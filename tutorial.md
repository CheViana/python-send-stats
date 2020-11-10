# Reporting measurements from Python code in real time

Simple example how to send measurements from Python code to the real-time monitoring solution (Telegraf/InfluxDB/Grafana).

Measurements can be:
- how long did backend call take
- size of image that is being processed right now
- processing time of uploaded file
- percent of file that is already processed, and percent that's left
- how much files were processed since process start
- any number that program code is aware of and that might be of use to keep track of

Observing measurements like that in real time can be very beneficial: notice problems early, pinpoint the cause why webserver is down, notice weird pattern in performnace, etc.

Program can send dozens measurements a second, without significant performance degradation, although with chance that some measurements are lost. For better reliability other approaches are recommended - database, temp file.

## Setup Grafana, InfluxDB

In short, install Grafana, InfluxDB and launch with default config:

> cd /grafana-7.1.0
> bin/grafana-server

> influxd -config /usr/local/etc/influxdb.conf

See previous post for details in how to install. (TODO: add link)

## Telegraf config

We're going to make Telegraf listen on Unix socket "unix:///tmp/telegraf.sock" for JSON-formatted measurements.

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


## Better socket management

It's an overhead to open and close socket each time.
Let's try to open when program starts and close when it exits.
To execute function on program exit will make use of `atexit` module.

[manage-socket-not-working.py] - explain why. Telegraf command line errors.

2020-11-10T14:42:17Z E! [inputs.socket_listener] Unable to parse incoming line: invalid character '{' after top-level value

[tutorial-materials/socket-not-working-lsof.png]

[manage-socket-buffer.py] - works. Explain memory, etc.

[tutorial-materials/socket-manage-buffer-1.png]
[tutorial-materials/socket-manage-buffer-2.png]


[manage-socket-not-working-2.py] - also not working. Telegraf command line errors.


try wavelength format instead.


## TODO: Try to run into socket listen queue overflow, socket listen queue increase
