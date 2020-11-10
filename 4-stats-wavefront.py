import time
import socket
import random
import atexit
import math


socket_store = {}


def create_socket():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 8094))
        socket_store['socket'] = sock
        print('Created socket')
    except socket.error as e:
        print(f'Got error while creating socket: {e}')


def close_socket():
    try:
        sock = socket_store['socket']
        sock.close()
        print('Closed socket')
    except (KeyError, socket.error) as e:
        print(f'Got error while closing socket: {e}')


def send_data_on_socket(data):
    try:
        sock = socket_store['socket']
        for key, value in data.items():
            line = f'test.{key} {value} {math.floor(time.time())} source=localhost\n'
            print(f'Ready to send: {line}')
            sent = sock.send(line.encode('utf-8'))
            print(f'Sent {sent} bytes')
    except (KeyError, socket.error) as e:
        print(f'Got error while sending data on socket: {e}')

        # attempt recreate socket on error
        close_socket()
        create_socket()


atexit.register(close_socket)


while True:
    create_socket()
    for i in range(0, 10):
        send_data_on_socket({'value1': 10, 'value2': random.randint(1, 10)})
        time.sleep(1)
    close_socket()
