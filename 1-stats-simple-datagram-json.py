import time
import socket
import json
import random


while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(
            json.dumps({'value1': 10, 'value2': random.randint(1, 10)}).encode(),
            ('localhost', 8094)
        )
        print('Sending sample data...')
        sock.close()
    except socket.error as e:
        print(f'Got error: {e}')

    time.sleep(2)
