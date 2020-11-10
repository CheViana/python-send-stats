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


def socket_flush():
    try:
        create_socket()
        sock = socket_store['socket']
        data_readings = socket_store['data']
        prepared_json = json.dumps(data_readings)
        print(f'Ready to send: {prepared_json}')
        sent = sock.send(prepared_json.encode('utf-8'))
        print(f'Sending sample data, bytes sent: {sent}')
        close_socket()
        socket_store['counter'] = 0
        socket_store['data'] = []
    except (KeyError, socket.error) as e:
        print(f'Got error while sending data on socket: {e}')


READINGS_BUFFER_SIZE = 30


def send_data_on_socket(data):
    counter = socket_store.get('counter', 0)
    data_list = socket_store.get('data', [])
    data['timestamp'] = time.time()
    data_list.append(data)
    socket_store['data'] = data_list
    socket_store['counter'] = counter + 1
    if socket_store['counter'] > READINGS_BUFFER_SIZE:
        socket_flush()


atexit.register(close_socket)


while True:
    for i in range(0, 5):
        send_data_on_socket({'value1': 10, 'value2': random.randint(1, 10)})
        time.sleep(1)
