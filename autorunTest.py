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
import signal

SIGSTART = '\x01'
SIGSTOP = '\x02'

proc = psutil.Process()
proc.cpu_affinity([3])
proc.nice(-20)

conn = None
connected = False

def on_sigint(*args, **kwargs):
    raise KeyboardInterrupt, 'process killed'


if __name__ == '__main__':
    signal.signal(signal.SIGINT, on_sigint)
    # connection cycle
    testSide = 0
	testCounter = 0
	testTime = 0
    while True:
        try:
            # create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 9090))
            sock.listen(1)
            # connect
            conn, addr = sock.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            time.sleep(1)
            start = time.time()
            # tracking system cycle
            while True:
                conn.settimeout(None)
                conn.settimeout(0.7)
                connected = True
            	if (time.time() - start) > testTime + 1:
            		testTime += 1
            		conn.send(
        				struct.pack(
            			'Iif',
            			testSide,
            			testCounter,
            			testTime)
        			)
					if testSide == 0:
						testSide = 1
					else:
						testSide = 0
						testCounter += 1
            		print testTime
        except KeyboardInterrupt:
            break
        except:
            logging.error(traceback.format_exc())
        finally:
            connected = False
            if conn:
                conn.close()
            sock.close()