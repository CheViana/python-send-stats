import time
import socket
import json
import random
import atexit


socket_store = {}


def create_socket():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 8094))
        socket_store['socket'] = sock
        sock.send('['.encode('utf-8'))
        print('Created socket')
    except socket.error as e:
        print(f'Got error while creating socket: {e}')


def close_socket():
    try:
        sock = socket_store['socket']
        sock.send((json.dumps({'value1': 0, 'value2': 5}) + ']').encode('utf-8'))
        sock.close()
        print('Closed socket')
    except (KeyError, socket.error) as e:
        print(f'Got error while closing socket: {e}')


def send_data_on_socket(data):
    try:
        sock = socket_store['socket']
        json_str = json.dumps(data)
        json_str = json_str + ','
        print(f'Ready to send: {json_str}')
        sent = sock.send(json_str.encode('utf-8'))
        print(f'Sending sample data... {sent}')
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
