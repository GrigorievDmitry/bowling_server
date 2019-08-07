#!/usr/bin/env python
import RPi.GPIO as GPIO
import time
import curses
from pins import pins

stdscr = curses.initscr()
curses.noecho()
curses.curs_set(0)
stdscr.nodelay(1)
curses.start_color()

curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)

GPIO.setmode(GPIO.BCM)
print pins
for key, value in pins.iteritems():
    if isinstance(value, int):
        GPIO.setup(value, GPIO.IN, GPIO.PUD_UP)

stdscr.addstr(0, 0, 'Press <Esc> to exit')
stdscr.addstr(2, 0, 'PIN GPIO     GPIO PIN')

while stdscr.getch() != 27:
    for pin, value in pins.iteritems():
        if isinstance(value, int):
            if GPIO.input(value):
                state = '*'
            else:
                state = '.'
            label = str(value)
            cp = 1
        else:
            state = '.'
            label = value
            cp = 0
        if pin % 2 > 0:
            x = 0
            s = "%3d %4s %s" % (pin, label, state)
        else:
            x = 0 + 11
            s = "%s %-4s %-3d" % (state, label, pin)
        y = 3 + (pin + 1) / 2
        stdscr.addstr(y, x, s, curses.color_pair(cp))
    time.sleep(0.01)
 
curses.endwin()
