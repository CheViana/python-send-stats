# Reporting measurements from Python code in real time

Simple example how to send measurements from Python code to the real-time monitoring solution (Telegraf/InfluxDB/Grafana).

Measurements can be:
- how long did backend call take
- size of image that is being processed right now
- processing time of uploaded file
- percent of file that is already processed, and percent that's left
- how much files were processed since process started
- ...
- any number that program code is aware of and that might be of use to keep track of

Observing measurements like that in real time can be very beneficial: notice problems early, pinpoint the cause why webserver is down, notice weird pattern in performance over time, ... .
Real time dashboards take less time to load, so saving time in moment of outage, compared to trying dig through logs.

Program can send dozens measurements a second, without significant performance degradation, although with chance that some measurements are lost. For best reliability other approaches are recommended, like temp file to store measurements before those are sent to Telegraf. However, that is more complicated to setup, and can add more to execution time, compared to readings sent over UDP/Unix socket. Most likely, with high enough value of `read_buffer_size`, and performance-tested setup, almost no measurements will be dropped, even if one Telegraf process serves hundreds of server processes. I'll show example of how to do tweak `read_buffer_size`, and performance-test measurements reporting setup, how to find after what threshold metrics will start to drop. And how to count dropped.

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

telegraf-1-stats-json-simple.conf:

...

[[outputs.influxdb]]
  urls = ["http://127.0.0.1:8086"]
  database = "socket-stats"

[[inputs.socket_listener]]
  service_address = "unix:///tmp/telegraf.sock"
  data_format = "json"


Launch telegraf to listen on /tmp/telegraf.sock:

> telegraf -config telegraf-1-stats-json-simple.conf


## Send stats to Telegraf from Python code in JSON format

1-stats-json-simple.py:

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

> python3 1-stats-json-simple.py


## Dashboard

Add source for InfluxDB database "socket-stats".
Create new dashboard, add panel which will display measurements sent to /tmp/telegraf.sock socket.

[tutorial-materials/1-2-json-dashboard-config.png]
[tutorial-materials/1-stats-json-simple-results.png]


## Socket management, and various Telegraf data formats

It's an overhead to open and close socket each time measurement is sent, which could be like 10 times per second.
Let's try to open socket when program starts and close when it exits. Or, reestablish connection after N readings are sent.
To execute socket close on program exit will make use of `atexit` module.

[2-stats-json.py]

'\n' at the end of str that is sent is crucial, this is how telegraf recognizes end of measurement. These telegraf inputs are desined for reading from file, I think.

Without '\n':

2020-11-10T14:42:17Z E! [inputs.socket_listener] Unable to parse incoming line: invalid character '{' after top-level value


More conplicated setup: [3-stats-json-buffer.py] - higher memory consumption of program, as it has to store reading before sending. Also code needs to set time.

[tutorial-materials/3-stats-json-buffer-output.png]
[tutorial-materials/3-stats-json-buffer-results.png]


Try wavefront format: [4-stats-wavefront.py]

Code needs to set timestamp. '\n' at the end of str that is sent is quite crucial.
Wavefront is coded for TCP socket, just for fun. Different names of measurements:

[tutorial-materials/4-stats-wavefront-config-and-results.png]


Try influx line format: [5-stats-influx-line.py]
Influx line is UDP socket, just for fun.


## TCP/UDP/Unix sockets

[tutorial-materials/unix-socket-lsof.png]
[tutorial-materials/tcp-socket-lsof.png]


## TODO: Try to run into socket listen queue overflow, socket listen queue increase
