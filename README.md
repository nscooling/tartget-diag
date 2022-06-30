# QEMU Diagnostic Backend

Standard Linux `target` project with embedded xPack QEMU emulator
extended to provide a diagnostic connection on port 8888 (supports
Telnet protocol but ignores all Telnet capabilities).

## Python remote GUI

Currently support for GPIOD only (cannot use USART with no graphics
until existing bug found and fixed).

Open this project in VS Code attached to a Linux container such as
WSL2 or Docker.

In the container start up QEMU with diagnostics support using the script
```
$ ./diag-qemu.sh
```

On the host start the python script:

```
Windows     > py qemu_wms.py
Linux/macOS $ python3 qemu_wms.py
```

Script attaches to running QEMU on `localhost:8888` so you will need to
bind the container port 8888 to the host (WSL2 does this automatically).

All button inputs (including reset) are supported. Click on the motor wheel
to simulate input from the sensor behind the wheel.

The Python script requires the `qemu_wms_graphics.zip` file to be in the
same folder.

## Running with diagnostics enabled

Add the following option to the QEMU command line to create a serial
connection for the diagnostics (any port number will do):

```
-serial telnet:localhost:8888,server,nodelay
```

The QEMU simulation will start after a connections is established on the
serial port. 

You will need to have a program to execute on the board. A simple loop
with a sleep will suffice e.g **main.c**:

```
#include <stdio.h>
#include "timer.h"

int main()
{
  for(;;)
  {
    printf("Tick...\n");
    sleep(5000);
  }
  return 0;
}
```

## Python GUI Notes

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

## Diagnostic port protocol

By default the diagnostics do not echo input nor produce any output 
as it is designed to be used programmtically with Python scripts
being the obvious choice.

You can connect using `putty`, `telnet` or similar in which case 
enter the command `echo` to enable character echo and simple backspace
line editing.

Command are sequences of characters delimited by whitespace and
are letter case insensitive. All numbers are in hex (unless stated
otherwise) and memory/port values are displayed as 8 hex digits.

Multiple commands can be specified on a single line, each command is
executed immediately (the input is not line buffered).

Invalid commands are echoed back surrounded by question marks.

**Commands** are one of the words:
   * echo - switches on character echo
   * halt - stops the QEMU emulation
   * reset - simulate reset button press
   * listen - enables GPIOD ODR pin change messages
   * p<string> - print the string on QEMU stdout
   
**GPIO** query commands are of the form:
   * <gpio><port><action><parameters>

Where 
   * <gpio> is either B or D (GPIO) or U (USART3)
   * <port> is any value 0..9, eg. MODER=0, IDR=4, ODR=5, ...
   * <action> is described below
   * <parameters> are optional (see below)

Actions can be:
   * ? read port value
   * = <parameter> hex value to write to the register
   * s <paramer> pin number (hex) to set
   * r <paramter> pin number (hex) to reset (clear)
   * t <paramter> pin number (hex) to toggle (xor)
   * | <paramer> bit pattern to set
   * & <paramter> bit pattern to clear
   * ^ <paramter> bit pattern to xor

Actions for in input pins (<port> not used):
   * p <parameter> push/poke/press an input pin(hex) 
   * l <parameter> latch an input pin(hex)
   * d <parameter> drop input pin(hex)
   
Examples:
   * D0? - read mode register of GPIOD
	* D0=550000 D5=100 - switch on led A
	* D0p5 - press WMS Accept key

**Memory** query commands are of the form:
   * M<address><action><parameters>

Where 
   * <address> in hex
   * <action> as described above
   * <parameters> are optional (as above)
   
Examples:
   * m40023830|8 - enable GPIOD (set pin 3)
	* m40023840s18 - enable USART3's clock
	
## Listening Output

The diagnostic backend reports changes to the GPIOD:ODR
pins when listening mode is enabled (send the `listen` command).

Output will breakthrough any input if using a `telnet` session so
this is less useful when working interactively which is why
listen mode is disabled by default.

After the `listen` command is issued the following messages
will be ouput:
   * +D<n> - GPIOD pin N has switched from low to high
   * -D<n> - GPIOD pin N has switched from high to low

# Supporting Scripts

To try out any of the supporting scripts in teh `scripts` folder
run a main progrma that performs an infinite loop with a suitable `sleep` 
action to reduce busy polling:

```
#include "Timer.h"
int main()
{
  for(;;)
  {
    sleep(2000);
  }
  return 0;
}
```

Startup QEMU using the `diag-qemu.sh` script and then run a 
python script:
    
   * `led_count.py` that counts from 0 to 9 using the LED pins in the script
     and shuts down QEMU when it finishes
