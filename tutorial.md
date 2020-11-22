# Reporting measurements from Python code in real time

Simple example how to send measurements from Python code to the real-time monitoring solution (Telegraf/InfluxDB/Grafana).

Measurements can be:
- how long did backend call take
- size of image that is being processed right now
- processing time of uploaded file
- percent of file that is already processed, and percent that's left
- how much data was processed since process started
- ...
- any number that program code is aware of and that might be of use to keep track of

I don't think I need to make agruments in favor of real time dashboards: they are a blessing in time of turnmoil (outage). Data collected (good times data, outges data) can be analyzed later for various purposes: notice weird pattern in performance over time, notice signifact features of traffic that can be leveraged, ... . 

We will start with simple examples of Python programs that report measurements data. But first need to configure things that are going to listen, record, and display these measurements.


## Setup Grafana, InfluxDB

In short, install Grafana, InfluxDB and launch with default config:

> cd /grafana-7.1.0
> bin/grafana-server
> influxd -config /usr/local/etc/influxdb.conf

See previous post for details on what are these tools and how to install them. (TODO: add link)


## Telegraf config

We're going to make Telegraf listen on Unix socket "unix:///tmp/telegraf.sock" for JSON-formatted measurements.

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


More info on telegraf plugin that listen for incomming data on socket: https://github.com/influxdata/telegraf/blob/release-1.14/plugins/inputs/socket_listener/README.md .


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


More info on telegraf JSON format for incomming data - https://github.com/influxdata/telegraf/tree/master/plugins/parsers/json .


## Dashboard

Add source for InfluxDB database "socket-stats".
Create new dashboard, add panel which will display measurements sent to /tmp/telegraf.sock socket.

[tutorial-materials/1-2-json-dashboard-config.png]
[tutorial-materials/1-stats-json-simple-results.png]


## Socket management

It's an overhead to open and close socket each time measurement is sent, which could be like 10 times per second.
Let's try to open socket when program starts and close when it exits. And reestablish connection after N readings are sent.
To execute socket close on program exit will make use of `atexit` module.

Run Python code [2-stats-json.py] and launch telegraf with config [telegraf-2-stats-json.conf].

'\n' at the end of str that is sent is crucial, this is how telegraf recognizes end of measurement. Took me some time to figure out what's wrong without '/n'. These telegraf text-based inputs are desined for reading from file, I think.

Without '\n' at the end of measurement string can encounter errors like:

2020-11-10T14:42:17Z E! [inputs.socket_listener] Unable to parse incoming line: invalid character '{' after top-level value


More conplicated setup: [3-stats-json-buffer.py] (telegraf config for it [telegraf-3-stats-json-buffer.conf]) - higher memory consumption of program, as it has to store measurement before sending. Also code needs to set time when measurement was performed. So this is not recommended approach.

[tutorial-materials/3-stats-json-buffer-output.png]
[tutorial-materials/3-stats-json-buffer-results.png]


## Other Telegraf text-based measurements data formats: Wavefront and Influx line. Telegraf on TCP and UDP socket examples.


### Wavefront (VMWare) format over TCP socket

Python code to send measurement in wavefront format [4-stats-wavefront.py], telegraf config [telegraf-4-stats-wavefront.conf].

Wavefront format uses timestamp in seconds, so timestamp is set in Python code using `time.time()` without decimal fraction. Omitting timestamp in sent data didn't work out for me.
'\n' at the end of str that is sent is quite crucial. It also requires `source` tag.
More about this data format - https://docs.wavefront.com/wavefront_data_format.html.

Wavefront code is using TCP socket, just for fun. And it has different names of measurements:

[tutorial-materials/4-stats-wavefront-config-and-results.png]


### Influx Line format over UDP socket

Python code to send measurement in Influx Line format: [5-stats-influx-line.py], telegraf config [telegraf-5-stats-influx-line.conf].
More about Influx Line data format - https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_tutorial/.

Influx line code piece uses UDP socket.
Notice the difference of networking code for UDP socket code: no need to connect to socket (no `socket.connect` call). Datagram is just send over to specified network address. No need to keep established connection, no need to recreate connection once in a while. Which is rather convenient for sending stats, less socket management. Downside is UDP doesn't guarantee datagrams delivery, like TCP does for packets send over established connection.

[tutorial-materials/5-stats-influxline-config-and-results.png]

## TCP, UDP and Unix sockets

If curious to learn more about network sockets, suggested reading is this - https://pymotw.com/2/socket/index.html (and "see also" list on that page). Code is for Python 2 so method names might be outdated, but concepts are valid (and older than Python itself).


## Troubleshooting

If something doesn't look right, and data doesn't apper on dashboards, can lauch telegraf with `--debug` option, to make it print out more information about errors in processing of received data.

When telegraf successfully receives and write to InfluxDB measurements, it should produce console output similar to:

[tutorial-materials/example-telegraf-output.png]

You can see it also says that buffer is not full. Means all incomming metrics to making it to database, no dropped readings on telegraf's side. In real setup, some metrics could be lost in network before they got to telegraf, but this is not likely when everything runs on same machine.

Also good idea is to check in case of issues:
- InfluxDB is launched
- InfluxDB address in telegraf config matches the one in influxdb config
- Grafana dashboard configuration - address of influxdb and database name, measurements names
- Python code sends data to correct socket address, the one telegraf listens on (specified in telegraf config)

To debug what's being written to InfluxDB, can use [Influx CLI|https://docs.influxdata.com/influxdb/v1.8/query_language/explore-data/] or [influx flux query language|https://docs.influxdata.com/influxdb/v2.0/query-data/get-started/]. I've used Influx CLI and `SELECT` statements, as this is something I'm more familiar with.
Launch Influx CLI with command `influx`. To show list of available databases, use command `show databases`. Then switch to database telegraf sends data to using `use "socket-stats"` command. Show all measurement names using `show measurements`. To see what's going on in particular measurement, can use `select *::field from "value1"` - it will show all fields and all data for measurement called "value1". `select *::field from "value1" limit 3` will show 3 oldest data points, `select last(*::field) from "value1"` will show newest data point.

[tutorial-materials/influx-cli-example.png]
[tutorial-materials/influx-cli-latest-measurement.png]

These screenshots show my trouble: "value2" timestamp value is not correct, it's millisecond-precision Unix time whereas data format expected nanosecond-precision Unix time (like "test.value2"). So "value2" timestamp is enterpreted as way older timestamp than it should be (it has late 60s vibe), and won't show up on "last 5 min" dashboard.

[tutorial-materials/readings-from-the-past.png]

It is possible to report timestamp of measurement from Python code, or leave it up to InfluxDB to record timestamp of when reading arrives. Delay between two event is usually negligible: on same machine - real tiny, over network - depends on network, but like couple milliseconds, maybe hundred milliseconds. My suggestion is to leave it up to InfluxDB, to avoid issues when reported time from Python is not correct due to bugs (like I had). Unless exact time of reading with nanosecond precision is important to you. 
Anyway, if reporting program and InfluxDB run on different machines, make sure [Network Time Protocol (NTP)|http://www.ntp.org/] is utilized to keep their clocks in sync.


## Next planned post:

- will try to overload TCP socket (Unix socket, UDP socket) with metrics, see what happens
- will describe how to increase `read_buffer_size` in telegraf config, why not to increase it to huge value right away, and system socket listen queue size
- talk about techniques to measure dropped readings rate


### TODO

Code
- put code that formats measurement in separate function (same function signature)
- put networking code in separate class or mark it with comments
- add measurement tags - for format
- don't set time from Python code
- make measurement names all same ? wavelength. socket-listener. test. perfixes ? . JSON adds "socket-listener." prefix to measurement name - how to avoid?

Text:
- links to format descriptions from telegraf docs

