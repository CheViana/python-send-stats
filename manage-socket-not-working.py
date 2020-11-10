import time
import socket
import json
import random
import atexit


socket_store = {}


def create_socket():
    try:
        sock = socket.socket(socket.AF_UNIX)
        sock.connect('/tmp/telegraf.sock')
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
        sent = sock.send(json.dumps(data).encode('utf-8'))
        print(f'Sending sample data... {sent}')
    except (KeyError, socket.error) as e:
        print(f'Got error while sending data on socket: {e}')

        # attempt recreate socket on error
        close_socket()
        create_socket()


atexit.register(close_socket)


while True:
    create_socket()
    for i in range(0, 5):
        send_data_on_socket({'value1': 10, 'value2': random.randint(1, 10)})
        time.sleep(1)
    close_socket()
