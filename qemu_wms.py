#!/usr/bin/env python3
"""
Remote access to XPack QEMU Washing Machine Simulator

On startup connects to `localhost:8888` for diagnostic
messages. Timer task (every 100ms) sends query commands
to poll the status of GPIOD enabled bit; if enabled then
polls `moder` and `idr` registers to and displays their
contents.

Accepts asynchronous `odr` register changes and updates
graphic display accordingly. On reconnect to QEMU will use
the polled values to resync the display with the current
GPIOD status.

ALl buttons are supported with correct latched behaviour for
the PS keys and the door open button toggles on and off. The
motor sensor is simulated by clicking on the motor wheel.

The default sate for the QEMU emulator is all output pins are
zero which means at startup the graphic display does not match
the real hardware where all pins are pulled high. This is not
normally a problem but be aware that:
   * writing a zero to the 7-Segment display as the first
     output value will not be displayed as the emulator does
     not detect an output pin change
   * latch is off so PS keys do not stay high
   * Logic of door open pin is inverted as high is considered open

Martin Bond: June 2022
"""
import socket
import threading
import zipfile
from collections import namedtuple
import tkinter as tk
from datetime import datetime
from enum import Enum
from queue import Queue
from tkinter import ttk, messagebox
from typing import AnyStr, Optional

__VERSION__ = '0.9.0'

POLL = 100
DISPLAY_WARN = 5000


class ButtonStyle(Enum):
    """ Identifies different button behaviours"""
    plain = 1
    latch = 2
    door = 3


Button = namedtuple('Button', 'name pin, style down up x y radius')
Overlay = namedtuple('Overlay', 'x y images')


class WmsError(Exception):
    """ Used to wrap errors for popup messages"""
    pass


class Config:
    """ Static class for GUI layout configuration """
    rcc_ahbenr = b'M40023830? '
    rcc_apb1enr = b'M40023840? '
    graphics_path = 'qemu_wms_graphics.zip'
    board_image = 'feabhas-wms-768.png'
    image_x = 768
    image_y = 356

    buttons = [
        Button('reset', None, ButtonStyle.plain, '', 'reset ', 32, 200, 8),
        Button('door', 0, ButtonStyle.door, 'D0L0 ', 'D0d0 ', 730, 310, 15),
        Button('PS1', 1, ButtonStyle.latch, 'D0L1 ', 'D0d1 ', 730, 130, 12),
        Button('PS2', 2, ButtonStyle.latch, 'D0L2 ', 'D0d2 ', 695, 130, 12),
        Button('PS3', 3, ButtonStyle.latch, 'D0L3 ', 'D0d3 ', 665, 130, 12),
        Button('cancel', 4, ButtonStyle.latch, 'D0L4 ', 'D0d4 ', 615, 130, 12),
        Button('accept', 5, ButtonStyle.latch, 'D0L5 ', 'D0d5 ', 575, 130, 12),
        Button('motor', 6, ButtonStyle.plain, 'D0L6 ', 'D0d6 ', 650, 230, 50),
    ]

    overlays = {
        "led": Overlay(207, 298, ['led-0.png', 'led-1.png']),
        "PS1": Overlay(702, 26, ['ps1-0.png', 'ps1-1.png']),
        "PS2": Overlay(667, 26, ['ps2-0.png', 'ps2-1.png']),
        "PS3": Overlay(632, 26, ['ps3-0.png', 'ps3-1.png']),
        "sseg": Overlay(550, 289, [
            'sseg-0.png', 'sseg-1.png', 'sseg-2.png', 'sseg-3.png',
            'sseg-4.png', 'sseg-5.png', 'sseg-6.png', 'sseg-7.png',
            'sseg-8.png', 'sseg-8.png', 'sseg-10.png', 'sseg-11.png',
            'sseg-12.png', 'sseg-13.png', 'sseg-14.png', 'sseg-15.png'
        ]),
        "motor": Overlay(592, 171, ['motor-00.png', 'motor-30.png', 'motor-60.png']),
        "spinner": Overlay(627, 203, ['motor-stop.png', 'motor-cw.png', 'motor-acw.png']),
        "door": Overlay(711, 301, ['door-closed.png', 'door-open.png']),

    }

    led_xy = [(207, 298), (217, 298,), (227, 298,), (237, 298,)]


class QEmuTag(Enum):
    """ Tags to identify response message types"""
    pin_low = 0
    pin_high = 1
    gpiod_enabled = 11
    command = 12
    moder = 13
    idr = 14
    warning = 15
    usart3_enabled = 21
    sr = 22


class QEmuListener:
    """ Socket listening class connect to localhost:8888"""
    def __init__(self, host='localhost', port=8889):
        try:
            self.socket = socket.create_connection((host, port), timeout=5)
        except (ConnectionRefusedError, BrokenPipeError) as err:
            raise WmsError(f'Cannot connect to QEMU WMS: {err}')

    def close(self):
        self.socket.close()

    def read(self, wait=True) -> str:
        retry = 3
        while True:
            try:
                data = self.socket.recv(128)
                while data and data[0] == 0xff:
                    data = data[3:]
                if data or not wait:
                    # if data[0] in b'+-': print('r', data)
                    break
            except socket.timeout:
                retry += 1
                if retry > 3:
                    raise UserWarning('Warning: QEMU connection receiver timeout')

        return data.strip().decode('ascii')

    def write(self, message: AnyStr):
        """ Note: assumes each message is whitespace terminated """
        if isinstance(message, str):
            message = message.encode('ascii')
        # print('w ', message)
        total = 0
        while total < len(message):
            sent = self.socket.send(message[total:])
            if sent == 0:
                raise UserWarning(f'Warning: QEMU connection send error {message}')
            total += sent


class Diagnostics:
    """
    Asynchronous send/recv wrapped around QEmuListener
    Uses Queue objects to
       * pass through commands from front end
       * read async reposes from back end and identify type
         to write a tuple (type, value) back to front end
    """
    def __init__(self):
        self.send = Queue()
        self.recv = Queue()
        self.qemu = QEmuListener()
        listener = threading.Thread(target=self.listen)
        listener.setDaemon(True)
        listener.start()
        runner = threading.Thread(target=self.run)
        runner.setDaemon(True)
        runner.start()
        self.command('noecho ')
        self.command('listen ')

    def close(self):
        self.qemu.close()

    def command(self, command):
        self.send.put((QEmuTag.command, command))

    def write(self, tag: QEmuTag, value):
        self.send.put((tag, value))

    def read(self):
        if self.recv.empty():
            return None, None
        return self.recv.get()

    def run(self):
        while True:
            try:
                tag, value = self.send.get()
                self.qemu.write(value)
            except UserWarning as ex:
                self.recv.put((QEmuTag.warning, str(ex)))
            except OSError:
                break  # raise UserWarning('Warning: QEMU connection closed')

    def listen(self):
        """ Note: assumes all responses are whitespace (newline etc) terminated"""
        while True:
            try:
                replies = self.qemu.read().split()
                for reply in replies:
                    if reply.startswith('?'):
                        self.recv.put((QEmuTag.warning, f'Invalid command response: {reply}'))
                    elif reply.startswith('-'):
                        self.recv.put((QEmuTag.pin_low, int(reply[2], 16)))
                    elif reply.startswith('+'):
                        self.recv.put((QEmuTag.pin_high, int(reply[2], 16)))
                    elif reply.startswith('='):
                        slash = reply.rfind('/')
                        value = int(reply[slash+1:], 16)
                        if reply.startswith('=m'):
                            addr = reply[:slash-1]
                            if addr.endswith('3830'):
                                self.recv.put((QEmuTag.gpiod_enabled, value))
                            # elif addr.endswith('3840'):
                            #     self.recv.put((QEmuTag.usart3_enabled, value))
                            else:
                                self.recv.put((QEmuTag.warning, f'Invalid memory address: {reply}'))
                        elif reply.startswith('=d0'):
                            self.recv.put((QEmuTag.moder, value))
                        elif reply.startswith('=d4'):
                            self.recv.put((QEmuTag.idr, value))
                        elif reply.startswith('=u0'):
                            self.recv.put((QEmuTag.sr, value))
                        else:
                            self.recv.put((QEmuTag.warning, f'Invalid response format: {reply}'))
            except UserWarning as ex:
                self.recv.put((QEmuTag.warning, str(ex)))
            except OSError:
                break  # raise UserWarning('Warning: QEMU connection closed')


class WmsBoard:
    """ Maintains state of the graphic board display """
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.latch = False
        self.latched = [False] * len(Config.buttons)
        self.sseg = 0
        self.motor = False
        self.sprite = 0
        self.direction = 0

    @staticmethod
    def find_button(x: int, y: int):
        for button in Config.buttons:
            if button.x - button.radius <= x <= button.x + button.radius:
                if button.y - button.radius <= y <= button.y + button.radius:
                    return button
        return None

    @staticmethod
    def build_overlay(root):
        with zipfile.ZipFile(Config.graphics_path) as archive:
            for tag, overlay in Config.overlays.items():
                for i, name in enumerate(overlay.images):
                    with archive.open(name) as file:
                        overlay.images[i] = tk.PhotoImage(master=root, data=file.read())
            with archive.open(Config.board_image) as file:
                return tk.PhotoImage(master=root, data=file.read())
        # for tag, overlay in Config.overlays.items():
        #     for i, name in enumerate(overlay.images):
        #         overlay.images[i] = tk.PhotoImage(master=root, file=f'{folder}/{name}')

    def update_device(self, pin: int, level: int, qemu: Diagnostics):
        if 8 <= pin <= 11:
            overlay = Config.overlays['led']
            x, y = Config.led_xy[pin - 8]
            self.canvas.create_image(x, y, image=overlay.images[level], anchor=tk.NW)
            if level:
                self.sseg |= 1 << (pin - 8)
            else:
                self.sseg &= ~(1 << (pin - 8))
            overlay = Config.overlays.get('sseg')
            self.canvas.create_image(overlay.x, overlay.y, image=overlay.images[self.sseg], anchor=tk.NW)
        elif pin == 12:
            overlay = Config.overlays['motor']
            self.canvas.create_image(overlay.x, overlay.y, image=overlay.images[self.sprite], anchor=tk.NW)
            # if not level:
            #     overlay = Config.overlays['spinner']
            #     self.canvas.create_image(overlay.x, overlay.y, image=overlay.images[0], anchor=tk.NW)
            self.motor = bool(level)
        elif pin == 13:
            self.direction = level
        elif pin == 14:
            self.latch = bool(level)
            if not self.latch:
                for button in Config.buttons:
                    if not button.style == ButtonStyle.latch:
                        continue
                    self.latched[button.pin] = False
                    if qemu:
                        qemu.command(button.up)
                for ps in 'PS1', 'PS2', 'PS3':
                    overlay = Config.overlays[ps]
                    self.canvas.create_image(overlay.x, overlay.y, image=overlay.images[0], anchor=tk.NW)

    def animate(self):
        if self.motor:
            overlay = Config.overlays['motor']
            self.canvas.create_image(overlay.x, overlay.y, image=overlay.images[self.sprite], anchor=tk.NW)
            self.sprite = (self.sprite + 1) % len(overlay.images)
            overlay = Config.overlays['spinner']
            self.canvas.create_image(overlay.x, overlay.y, image=overlay.images[self.direction + 1], anchor=tk.NW)

    def update_button(self, button: Button, level: int):
        overlay = Config.overlays.get(button.name)
        if overlay:
            self.canvas.create_image(overlay.x, overlay.y, image=overlay.images[level], anchor=tk.NW)

    def button_down(self, button: Button, qemu: Optional[Diagnostics]):
        if button.style == ButtonStyle.latch:
            if self.latch and self.latched[button.pin]:
                return
            self.latched[button.pin] = self.latch
        elif button.style == ButtonStyle.door:
            if self.latched[button.pin]:
                self.latched[button.pin] = False
                return
            self.latched[button.pin] = True
        self.update_button(button, 1)
        if qemu and button.down:
            qemu.command(button.down)

    def button_up(self, button: Button, qemu: Optional[Diagnostics]):
        if button.style == ButtonStyle.latch:
            if self.latch and self.latched[button.pin]:
                return
        elif button.style == ButtonStyle.door:
            if self.latched[button.pin]:
                return
        self.update_button(button, 0)
        if qemu and button.up:
            qemu.command(button.up)


def catch(wait_cursor: bool = False):
    """ Wrapper to display popup dialog for event handler exceptions """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                if wait_cursor:
                    self.root.config(cursor='watch')
                    self.root.update()
                return func(self, *args, **kwargs)
            except UserWarning as ex:
                self.warning(str(ex))
            except Exception as ex:
                if not self.closing:
                    # import traceback
                    # traceback.print_exc(file=STDERR)
                    # messagebox.showerror(err, str(ex) + '\n\n' + str(traceback.format_tb(ex.__traceback__, limit=1)),
                    #                      parent=self.root)
                    messagebox.showerror('Unexpected Error', str(ex))
            finally:
                if wait_cursor and not self.closing:
                    self.root.config(cursor='')
        return wrapper
    return decorator


def scroll_main(root):
    """ Wrap a scrol bar around the entire root window"""
    main_frame = tk.Frame(root, bd=1, relief=tk.SUNKEN)
    main_frame.pack(fill=tk.BOTH, expand=1)
    xsbar_frame = tk.Frame(main_frame)
    xsbar_frame.pack(fill=tk.X, side=tk.BOTTOM)
    canvas = tk.Canvas(main_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    xscroll = ttk.Scrollbar(xsbar_frame, orient=tk.HORIZONTAL, command=canvas.xview)
    xscroll.pack(side=tk.BOTTOM, fill=tk.X)
    yscroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(xscrollcommand=xscroll.set)
    canvas.configure(yscrollcommand=yscroll.set)
    canvas.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox(tk.ALL)))
    frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=frame, anchor=tk.NW)
    return frame


class CheckBox(tk.Checkbutton):
    """ Customised CheckButton to simplify coding"""
    def __init__(self, parent, text: str, value=0, anchor=tk.W, **kwargs):
        tk.Checkbutton()
        self.var = tk.IntVar(value=value)
        super().__init__(parent, text=text, variable=self.var, anchor=anchor, **kwargs)

    def set(self, value: int):
        self.var.set(value)

    def get(self) -> bool:
        return bool(self.var.get())


class WmsGui:
    """ Builds and manages the GUI """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.closing = False
        self.button = None
        self.qemu = None
        self.ticks = 0
        self.reattach = True

        self.style = ttk.Style()
        self.style.configure('.', sticky=(tk.N, tk.W), font=('Sans Serif', 10), padding=5)

        root.geometry('835x510')
        root.title("Feabhas WMS")
        base = scroll_main(root)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        frame = ttk.LabelFrame(base, text="STM32F407-WMS")
        frame.pack(fill=tk.BOTH, pady=5, padx=5)
        canvas = tk.Canvas(frame, width=Config.image_x, height=Config.image_y)
        canvas.pack(fill=tk.BOTH, expand=1, pady=5, padx=5)
        canvas.config(scrollregion=canvas.bbox(tk.ALL))
        canvas.bind('<Button-1>', self.on_b1_down)
        canvas.bind('<ButtonRelease-1>', self.on_b1_up)
        canvas.bind('<Motion>', self.on_move)
        self.board = WmsBoard(canvas)

        try:
            self.image = self.board.build_overlay(root)
            canvas.create_image(0, 0, image=self.image, anchor=tk.NW)

        except Exception as ex:
            messagebox.showerror('Startup error', f'Error or missing graphics file:\n{ex}')
            raise KeyboardInterrupt(ex)

        status = tk.Frame(base)
        status.pack(anchor=tk.W, padx=5)
        self.gpiod = CheckBox(status, text='GPIOD', state=tk.DISABLED)
        self.gpiod.pack(side=tk.LEFT, padx=0)
        self.mode = ttk.Label(status, text=f'mode: 00000000', state=tk.DISABLED)
        self.mode.pack(side=tk.LEFT, padx=10)
        self.idr = ttk.Label(status, text=f'idr: 0000', state=tk.DISABLED)
        self.idr.pack(side=tk.LEFT, padx=10)
        self.pins = [
            CheckBox(status, text=text, state=tk.DISABLED)
            for text in ('Led A', 'Led B', 'Led C', 'Led D', 'Motor', 'Dir', 'Latch')
        ]
        for pin in self.pins:
            pin.pack(side=tk.LEFT, padx=0)

        # status = tk.Frame(base)
        # status.pack(anchor=tk.W, padx=5)
        # self.usart3 = CheckBox(status, text='USART3', state=tk.DISABLED)
        # self.usart3.pack(side=tk.LEFT, padx=0)
        # ttk.Label(status, text='sr', state=tk.DISABLED).pack(side=tk.LEFT, padx=0)
        # self.sr = tk.StringVar(value='00000000')
        # ttk.Label(status, textvariable=self.sr, state=tk.DISABLED).pack(side=tk.LEFT, padx=0)

        self.warn_field = ttk.Label(base, text='', state=tk.DISABLED)
        self.warn_field.pack(side=tk.LEFT, padx=12)
        halt = ttk.Button(base, text='Halt', width=5, command=self.on_halt)
        halt.pack(side=tk.RIGHT, padx=15)

        self.root.after(POLL, self.on_timer)

    @catch()
    def on_halt(self):
        if self.qemu:
            self.qemu.command(b'halt ')
        self.closing = True
        self.root.destroy()

    def warning(self, value: str):
        if value:
            self.warn_field['text'] = f'{datetime.now():%H:%M:%S} {value}'
            self.ticks = POLL
        else:
            self.warn_field['text'] = ''
            self.ticks = 0

    def on_move(self, event):
        button = self.board.find_button(event.x, event.y)
        if button != self.button:
            self.root.config(cursor='hand2' if button else '')
            self.button = button

    @catch()
    def on_b1_down(self, _):
        # print(event.x, event.y)
        if self.button:
            self.board.button_down(self.button, self.qemu)

    @catch()
    def on_b1_up(self, _):
        if self.button:
            if self.button.up.startswith('reset'):
                self.gpiod.set(0)
            self.board.button_up(self.button, self.qemu)

    def do_update_status(self):
        if not self.gpiod.get():
            self.qemu.write(QEmuTag.gpiod_enabled, Config.rcc_ahbenr)
        # if not self.usart3.get():
        #     self.qemu.write(QEmuTag.usart3_enabled, Config.rcc_apb1enr))
        for _ in range(10):         # prevent GUI locking out
            tag, value = self.qemu.read()
            if tag is None:
                break
            elif tag == QEmuTag.warning:
                self.warning(value)
                continue
            if tag == QEmuTag.gpiod_enabled:
                gpiod_on = (value >> 3) & 1
                self.gpiod.set(1 if gpiod_on else 0)
                if gpiod_on:
                    self.warning('Connected to QEMU')
                    self.reattach = True
            elif tag == QEmuTag.moder:
                self.mode['text'] = f'mode: {value:08x}'
            elif tag == QEmuTag.idr:
                self.idr['text'] = f'isr: {value:04x}'
                if self.reattach:
                    self.reattach = False
                    for pin in range(8, 15):
                        if (value >> pin) & 1:
                            self.board.update_device(pin, 1, self.qemu)
                    for button in Config.buttons:
                        if button.pin is None:
                            continue
                        if (value >> button.pin) & 1:
                            self.board.button_down(button, None)
                            self.board.button_up(button, None)
                for pin, check in enumerate(self.pins, 8):
                    check.set((value >> pin) & 1)
            elif tag == QEmuTag.pin_low:
                self.board.update_device(value, 0, self.qemu)
            elif tag == QEmuTag.pin_high:
                self.board.update_device(value, 1, self.qemu)
        if self.gpiod.get():
            self.qemu.write(QEmuTag.moder, b'D0? ')
            self.qemu.write(QEmuTag.idr, b'D4? ')
        # if self.usart3.get():
        #     self.qemu.write(QEmuTag.idr, b'U0? ')

    @catch()
    def on_timer(self):
        try:
            if self.ticks:
                self.ticks += POLL
                if self.ticks >= DISPLAY_WARN:
                    self.warning('')
            if self.qemu is None:
                try:
                    self.warning('Connecting to QEMU...')
                    self.qemu = Diagnostics()
                except WmsError as err:
                    if not messagebox.askokcancel('QEMU Error', f'''QEMU is not running.
    
    Error: {err}
    
    Please start QEMU in your Linux Container.
    Press OK to continue or Cancel to stop?'''):
                        self.on_close()
            else:
                self.do_update_status()
                self.board.animate()
        finally:
            self.root.after(POLL, self.on_timer)

    def on_close(self):
        self.closing = True
        if self.qemu:
            self.qemu.close()
        self.root.destroy()


def main():
    """ Main method builds GUI and starts TkInter main loop"""
    try:
        root = tk.Tk()
        _ = WmsGui(root)
        root.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
