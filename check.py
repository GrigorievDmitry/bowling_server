#!/usr/bin/python
import logging
import traceback
import socket
import time
import struct
# from socket import error as SocketError
import errno
import RPi.GPIO as RPiGPIO
import psutil


proc = psutil.Process()
proc.cpu_affinity([3])
proc.nice(-20)

CMD_RESTART = '\x01'

conn = None
connected = False


N = 0

class GPIO:
    def __init__(self, side, prev1_gpio_num, prev2_gpio_num):
        self.active = True
        self.side = side
        self.prev2_gpio_num = prev2_gpio_num
        self.prev2 = None
        self.prev1_gpio_num = prev1_gpio_num
        self.prev1 = None
        self.t0 = time.time() * 2
        self.activated = False
        self.psres = False

    def reset(self):
        self.active = True
        self.t0 = time.time() * 2
        self.activated = False
        self.psres = False

    def detected(self):
        result = False
        t1 = time.time()
        #print t1 -self.t0
        if t1 - self.t0 > 0.015:
            self.psres = True
        if (self.psres and (t1-self.t0 < 0.002)):
            self.psres = False
            result = True
        self.t0 = t1
        return result

    def __repr__(self):
        return 'GPIO({}, {}, {})'.format(
            self.side.name,
            self.prev1_gpio_num,
            self.prev2_gpio_num)

class Side:
    def __init__(self, side, name):
        self.side = side
        self.counter = 0
        self.name = name
        self.detection_counter = 0

    def detect(self, inc):
        self.counter += inc
        print self.name, self.counter
        self.counter += 1
        self.detection_counter += 1

    def reset(self, time):
        self.time = time
        self.counter = 0
        self.detection_counter = 0


left = Side(0, 'left')
right = Side(1, 'right')


left_list =  [6, 13, 19, 26]
right_list = [12, 16, 20, 21]


# fill GPIO map evaluating prev1 and prev2
gpio_map = {}
for i in xrange(len(left_list)):
    gpio_map[left_list[i]] = GPIO(left, left_list[i-1], left_list[i-2])
for i in xrange(len(right_list)):
    gpio_map[right_list[i]] = GPIO(right, right_list[i-1], right_list[i-2])


def onHigh(gpio_num):
    global N
    gpio = gpio_map[gpio_num]
    if gpio.detected():# and gpio.active and connected:
        N += 1
        print N, gpio_num
        '''
        gpio.active = False
        gpio.activated = True
        gpio.prev2.active = True
        if gpio.prev1.activated:
            gpio.prev1.activated = False
            gpio.side.detect(0)
        else:
            gpio.prev1.prev2.active = True
            gpio.side.detect(1)
        '''
        


if __name__ == '__main__':
    # setup logging
    logging.basicConfig(
        format = '[%(asctime)s] %(levelname)s: %(message)s',
        level = logging.DEBUG)
    # initialize GPIOs
    logging.debug('setting GPIO mode')
    RPiGPIO.setmode(RPiGPIO.BCM)
    logging.debug('initializing GPIOs')
    for gpio_num, gpio in gpio_map.iteritems():
        gpio.prev1 = gpio_map[gpio.prev1_gpio_num]
        gpio.prev2 = gpio_map[gpio.prev2_gpio_num]
        RPiGPIO.setup(gpio_num, RPiGPIO.IN, RPiGPIO.PUD_DOWN)
        RPiGPIO.add_event_detect(
            gpio_num,
            RPiGPIO.FALLING,
            callback=onHigh)
    # connection cycle
    while True:
        time.sleep(1)
        '''
        try:
            time.sleep(1)            
            # tracking system cycle
            while True:
                start = time.time()
                left.reset(start)
                right.reset(start)
                for gpio_num, gpio in gpio_map.iteritems():
                    gpio.reset()
                # first detectors depend on these GPIOs
                gpio_map[6].activated = True
                gpio_map[4].activated = True
                logging.debug('entering detection cycle')
                connected = True
                while left.counter < 16 or right.counter < 16:
                    time.sleep(0.5)
                connected = False
                logging.debug(
                    '{} detections, left detection cycle'.format(
                        left.detection_counter + right.detection_counter
                        ))
                break
        except KeyboardInterrupt:
            print ''
            logging.debug('caught keyboard interrupt')
            break
        except:
            logging.error(traceback.format_exc())
        finally:
            connected = False
        '''
    logging.debug('cleaning up GPIOs')
    RPiGPIO.cleanup()
