import time
import socket
import math
import random
import atexit


def format_measurement_to_str_influxline(data):
    measurement_name = 'good_metric_name'

    fields = []
    for key, value in data.items():
        fields.append(f'{key}={value}')
    fields_str = ','.join(fields)

    tags = {'format': 'influxline'}
    tags_strs = []
    for tag_key, tag_value in tags.items():
        tags_strs.append(f'{tag_key}={tag_value}')
    tags_str = (',' + ','.join(tags_strs)) if tags else ''

    return f'{measurement_name}{tags_str} {fields_str}\n'


class StatsReporter:
    def __init__(
        self,
        socket_type,
        socket_address,
        encoding='utf-8',
        formatter=None
    ):
        self._socket_type = socket_type
        self._socket_address = socket_address
        self._encoding = encoding
        self._formatter = formatter if formatter else lambda d: str(d)
        self.create_socket()
    
    def create_socket(self):
        try:
            sock = socket.socket(*self._socket_type)
            # no sock.connect
            self._sock = sock
            print('Created socket')
        except socket.error as e:
            print(f'Got error while creating socket: {e}')

    def close_socket(self):
        try:
            self._sock.close()
            print('Closed socket')
        except (AttributeError, socket.error) as e:
            print(f'Got error while closing socket: {e}')

    def send_data(self, data):
        try:
            sent = self._sock.sendto(
                self._formatter(data).encode(self._encoding),
                self._socket_address
            )
            print(f'Sending sample data... {sent}')
        except (AttributeError, socket.error) as e:
            print(f'Got error while sending data on socket: {e}')

            # attempt to recreate socket on error
            self.close_socket()
            self.create_socket()


reporter = StatsReporter(
    (socket.AF_INET, socket.SOCK_DGRAM),
    ('localhost', 8094),
    formatter=format_measurement_to_str_influxline
)
atexit.register(reporter.close_socket)


while True:
    reporter.send_data({'value1': 10, 'value2': random.randint(1, 10)})
    time.sleep(1)
