import time
import socket
import random
import atexit
import math


def format_measurement_to_str_influxline(
    measurement_name,
    measurement_value,
    **measurement_tags
):
    return f'{measurement_name} value={measurement_value}\n'


socket_store = {}
server_address = ('localhost', 8094)


def create_socket():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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


def send_data_on_socket(data, formatting_func):
    try:
        sock = socket_store['socket']
        for key, value in data.items():
            line = formatting_func(key, value)
            print(f'Ready to send: {line}')
            sent = sock.sendto(line.encode('utf-8'), server_address)
            print(f'Sent {sent} bytes')
    except (KeyError, socket.error) as e:
        print(f'Got error while sending data on socket: {e}')

        # attempt recreate socket on error
        close_socket()
        create_socket()


atexit.register(close_socket)

create_socket()
while True:  
    for i in range(0, 10):
        send_data_on_socket(
            {'value1': 10, 'value2': random.randint(1, 10)},
            format_measurement_to_str_influxline
        )
        time.sleep(1)
