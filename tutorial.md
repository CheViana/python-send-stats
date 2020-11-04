# Send measurements from Python code to Telegraf/InfluxDB/Grafana

## Setup Grafana, InfluxDB, Telegraf

See previous post. (recap?)

## Telegraf config

Make telegraf listen on Unix socket "unix:///tmp/telegraf.sock", or choose TCP socket, or UDP socket

https://github.com/influxdata/telegraf/blob/release-1.14/plugins/inputs/socket_listener/README.md
https://github.com/influxdata/telegraf/tree/master/plugins/parsers/json

telegraf.conf:

...

[[outputs.influxdb]]
  urls = ["http://127.0.0.1:8086"]
  database = "socket-stats"

[[inputs.socket_listener]]
  service_address = "unix:///tmp/telegraf.sock"
  data_format = "json"

Launch telegraf to listen on /tmp/telegraf.sock:

> telegraf -config telegraf.conf


## Send stats to Telegraf from Python code in JSON format

command-line-example.py:

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


Start program that sends dummy stats to socket:

> python3 command-line-example.py


## Dashboard

Add source for InfluxDB database "socket-stats".
Create new dashboard, add panel which will display measurements sent to /tmp/telegraf.sock socket.

[tutorial-materials/command-line-stats-dashboard-config.png]
[tutorial-materials/command-line-stats.png]


## Only close socket when program quits 
## Try to run into socket listen queue overflow