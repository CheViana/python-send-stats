import time
import socket
import json
import random


while True:
    try:
        sock = socket.socket(socket.AF_UNIX)
        sock.connect('/tmp/telegraf.sock')
        sock.send(json.dumps({'value1': 10, 'value2': random.randint(1, 10)}).encode())
        print('Sending sample data...')
        sock.close()
    except socket.error as e:
        print(f'Got error: {e}')

    time.sleep(2)
