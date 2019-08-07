#!/usr/bin/python
import logging
import traceback
import socket
import time
import struct
# from socket import error as SocketError
import RPi.GPIO as RPiGPIO
import psutil
import signal

n_rays = 20
left_list =  [6, 13, 19, 26]
right_list = [12, 16, 20, 21]

# line inversion
if False:
    left_list.reverse()
    right_list.reverse()
    left_list, right_list = right_list, left_list

SIGSTART = '\x01'
SIGSTOP = '\x02'

proc = psutil.Process()
proc.cpu_affinity([3])
proc.nice(-20)

conn = None
connected = False


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
        if t1 - self.t0 > 0.015:
            self.psres = True
        if (self.psres and (t1 - self.t0 < 0.002)):
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
        conn.send(
            struct.pack(
                'Iif',
                self.side,
                self.counter,
                time.time() - self.time)
            )
        self.counter += 1
        self.detection_counter += 1

    def reset(self, time):
        self.time = time
        self.counter = 0
        self.detection_counter = 0


left = Side(0, 'left')
right = Side(1, 'right')


# fill GPIO map evaluating prev1 and prev2
gpio_map = {}
for i in range(len(left_list)):
    gpio_map[left_list[i]] = GPIO(left, left_list[i-1], left_list[i-2])
for i in range(len(right_list)):
    gpio_map[right_list[i]] = GPIO(right, right_list[i-1], right_list[i-2])


def onHigh(gpio_num):
    gpio = gpio_map[gpio_num]
    if gpio.detected() and gpio.active and connected:
        gpio.active = False
        gpio.activated = True
        gpio.prev2.active = True
        if gpio.prev1.activated:
            gpio.prev1.activated = False
            gpio.side.detect(0)
        else:
            gpio.prev1.prev2.active = True
            gpio.side.detect(1)
        print(gpio_num)

def on_sigint(*args, **kwargs):
    raise KeyboardInterrupt('process killed')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, on_sigint)
    # setup logging
    logging.basicConfig(
        filename='/home/pi/vra/server/log.txt',
        filemode='w',
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
        try:
            # create socket
            logging.debug('creating socket')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 9090))
            sock.listen(1)
            # connect
            logging.debug('waiting for incoming connection')
            conn, addr = sock.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            logging.debug('accepted address {}:{}'.format(*addr))
            time.sleep(1)            
            # tracking system cycle
            while True:
                logging.debug('waiting for SIGSTART command')
                conn.settimeout(None)
                cmd = conn.recv(1)
                if cmd == SIGSTART:
                    logging.debug('got SIGSTART command')
                elif cmd == SIGSTOP:
                    logging.debug('got SIGSTOP instead of SIGSTART')
                    continue
                elif not cmd:
                    logging.debug('got null command, connection broken')
                    break
                else:
                    logging.debug('got unknown command, interpreting as SIGSTART')
                conn.settimeout(0.7)
                start = time.time()
                left.reset(start)
                right.reset(start)
                for gpio_num, gpio in gpio_map.iteritems():
                    gpio.reset()
                # first detectors depend on these GPIOs
                gpio_map[left_list[-1]].activated = True
                gpio_map[right_list[-1]].activated = True
                logging.debug('entering detection cycle')
                connected = True
                while left.counter < n_rays or right.counter < n_rays:
                    try:
                        cmd = conn.recv(1)
                        if cmd == SIGSTOP:
                            logging.debug('got SIGSTOP command')
                        elif not cmd:
                            logging.debug('got null command, connection broken')
                        else:
                            logging.debug('got unknown command, interpreting as SIGSTOP')
                        break
                    except socket.timeout:
                        pass
                connected = False
                logging.debug(
                    '{} detections, left detection cycle'.format(
                        left.detection_counter + right.detection_counter
                        ))
        except KeyboardInterrupt:
            logging.debug('caught keyboard interrupt')
            break
        except:
            logging.error(traceback.format_exc())
        finally:
            connected = False
            logging.debug('closing sockets')
            if conn:
                conn.close()
            sock.close()
    logging.debug('cleaning up GPIOs')
    RPiGPIO.cleanup()
