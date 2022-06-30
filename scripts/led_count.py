#!/usr/bin/env python3
import threading as thr
import socket
import sys
import time

HOST = 'https://8888-feabhas-targetdiag-dftnrbkkc45.ws-eu51.gitpod.io'  
PORT = 8889

class Diagnostics():
    def __init__(self, socket):
        self.socket = socket

    def listen(self):
        self.socket.send(b'listen\n')
        while True:
            char = self.socket.recv(1)
            if not char:
                break
            # telnet negotiation
            if (ord(char) == 255):
                self.socket.recv(2)
                continue
            sys.stdout.write(char.decode('utf8'))
            sys.stdout.flush()

    def write(self, message):
        """assumes message is whitespace terminated"""
        if isinstance(message, str):
            message = message.encode('utf8')
        total = 0
        while total < len(message):
            sent = self.socket.send(message[total:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            total += sent


def enable_leds(diag):
    diag.write(b'M40023830s3 D0&FF0000 D0|550000 ')


def test_leds(diag):
    enable_leds(diag)
    for i in range(10):
        pattern = i << 8
        diag.write(f'd5&f00  d5|{pattern:x} ')
        time.sleep(1)


def main():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            diag = Diagnostics(s)
            thread = thr.Thread(target=diag.listen)
            thread.start()
            test_leds(diag)
            diag.write('pTaDa! ')
            diag.write('halt ')
            thread.join()
            print()
            exit(0)
    except (ConnectionRefusedError, BrokenPipeError) as err:
        print(err, file=sys.stderr)
    exit(1)


if __name__ == '__main__':
    main()
