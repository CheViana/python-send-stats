# Reporting measurements from Python code in real time

Simple example how to send measurements from Python code to the real-time monitoring solution (Telegraf/InfluxDB/Grafana).

Code-reported measurements can be:
- price of order user just submitted
- amount of free beds in hostipal
- how long did backend call take
- cache hit / cache blank
- percent of file that is already processed, and percent that's left
- amount of data that was processed last second
- ...
- any number that program code is aware of and that might be of use to keep track of

I don't think I need to make a lot of agruments in favor of real-time monitoring: it's a blessing in time of turmoil (outage). Data collected (good times data, outges data) can be analyzed later for various purposes: notice weird pattern in performance over time, notice signifact features of traffic that can be leveraged, notice what happens right before outage, ... . 

We will start with simple examples of Python programs that report measurements data. But first need to configure things that are going to listen, record, and display these measurements.


## Looking for quick ready robust solution?

Scroll to Example 4.


## Setup Grafana, InfluxDB, Telegraf

In short, install Grafana, InfluxDB, Telegraf:

- Visit https://portal.influxdata.com/downloads/ for information on how to install InfluxDB and Telegraf
- Visit https://grafana.com/grafana/download for information on how to install Grafana

Launch Grafana and InfluxDB with default configs:

> cd grafana-7.1.0
> bin/grafana-server

> influxd -config /usr/local/etc/influxdb.conf


## Telegraf socket_listener config for JSON data format

We're going to make Telegraf listen on Unix socket "unix:///tmp/telegraf.sock" for JSON-formatted measurements that Python code will send. Telegraf then will write measurements to database called "socket-stats" hosted in InfluxDB instance on http://127.0.0.1:8086 (default InfluxDB config).

[telegraf-1-stats-json-simple.conf]:

...

[[outputs.influxdb]]
  urls = ["http://127.0.0.1:8086"]
  database = "socket-stats"

[[inputs.socket_listener]]
  service_address = "unix:///tmp/telegraf.sock"
  data_format = "json"


Launch telegraf to listen on /tmp/telegraf.sock:

> telegraf -config telegraf-1-stats-json-simple.conf

More info on telegraf plugin that enables listening for data on socket: https://github.com/influxdata/telegraf/blob/release-1.14/plugins/inputs/socket_listener/README.md.


## Example 1. Simplest example of how to send stats from Python code, and of suitable telegraf config

[1-stats-json-simple.py] is simple Python program that sends measurements to Unix socket. Connection is established anew for each measurement sent. Measurements are in JSON format:

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


Start program that sends stats to socket:

> python3 1-stats-json-simple.py


More info on telegraf JSON format for incomming data - https://github.com/influxdata/telegraf/tree/master/plugins/parsers/json.


## Dashboard

Add source for InfluxDB database "socket-stats".
Create new dashboard, add panel which will display measurements sent to Telegraf client.

[tutorial-materials/1-json-dashboard-config.png]
[tutorial-materials/1-stats-json-simple-results.png]

Provided all 4 processes are running (Grafana, InfluxDB, Telegraf and Python program that sends stats), you should see measurements appear on dashboard in real time. Exciting, isn't it?


## Example 2. Better example than Example 1: reuse connection for stats reporting

It's an overhead to open and close connection each time measurement is sent, which could be 10 times per second. Openning and closing connections is CPU intensive operation.
Let's try to improve on previous example: open socket when program starts and close when it exits. 

Program that does better socket management than Example 1 is available in [2-stats-json.py]:

[code of 2-stats-json.py]

This program opens connection once, and sends measurements over it continuously. If data send fails, connection is reestablished. When program exits, socket is closed using [`atexit`|https://docs.python.org/3/library/atexit.html]. `StatsReporter` class encapsulates operations with socket: creating, sending data, closing; it also keeps reference to open socket as a field.

Formatting of measuremnt data from Python dict into string sent over wire is all done in `format_measurement_data_json` function. This function is passed as an argument to `StatsReporter` class, so it will be easy to change data format. Tag which corresponds to data format is added.

'\n' at the end of str that is sent is crucial here, this is how telegraf recognizes end of measurement. Without '\n' at the end of measurement string can encounter errors like:

  2020-11-10T14:42:17Z E! [inputs.socket_listener] Unable to parse incoming line: invalid character '{' after top-level value


Run Python program [2-stats-json.py] and launch telegraf with config [telegraf-2-stats-json.conf] (stop previous Python program and telegraf before this). You should see measurements in real time on dashboard, provided dashboard is updated a bit:

[tutorial-materials/2-dashboard-config-and-results.png]


[telegraf-2-stats-json.conf] specifies field `name_override = "good_metric_name"`, which is used as measurement name in database records:


[[inputs.socket_listener]]
  service_address = "unix:///tmp/telegraf.sock"
  data_format = "json"
  name_override = "good_metric_name"
  tag_keys = ["format"]


 Default measurement name would be input plugin name (`socket_listener` as for Example 1) which is not descriptive. It is also possible to specify in telegraf config key where in reading data is stored string which should become measurement name in database, using `json_name_key`. See more in [JSON Telegraf format docs|https://github.com/influxdata/telegraf/tree/master/plugins/parsers/json].

 Example 2 telegraf config also specifies `tag_keys = ["format"]` - meaning from measurement data dict `{'value': 1, 'format': 'json'}` `format` will be used as a tag.


## Other Telegraf text-based measurements data formats: Wavefront and Influx line. Telegraf socket_listener TCP and UDP socket examples.


### Example 3. Wavefront (VMWare) format over TCP socket

Python code to send measurement in wavefront format [3-stats-wavefront.py], telegraf config [telegraf-3-stats-wavefront.conf]. Stop other examples and run this one.

[3-stats-wavefront.py] code differs from Example 2 in couple of lines - formatting function and socket type/address:

...
import math

...

def format_measurement_data_wavefront(data):
    lines = []
    for key, value in data.items():
        line = (
            f'prefix_metric_name.{key} {value} '
            f'{math.floor(time.time())} '
            f'source=localhost format="wavefront"\n'
        )
        lines.append(line)
    return ''.join(lines)

...

reporter = StatsReporter(
    (socket.AF_INET, socket.SOCK_STREAM),
    ('127.0.0.1', 8094),
    formatter=format_measurement_data_wavefront
)
atexit.register(reporter.close_socket)

...


Wavefront format uses timestamp in seconds, so timestamp is set in Python code using `time.time()` without decimal fraction. Omitting timestamp didn't work out for me.
'\n' at the end of str that is sent is quite crucial. Wavefront format also requires `source` tag. `format="wavefront"` part of string is example of how measurement tags should be added.
More about Wavefront data format - https://docs.wavefront.com/wavefront_data_format.html.

Wavefront code is using TCP socket, just for fun. TCP connection is reused in similar fashion as in Example 2 for Unix socket.

Wavefront Example also has different names of measurements. It can only do "single field value" per measurement. So will have to update dashboard or make new panel to see results:

[tutorial-materials/3-stats-wavefront-config-and-results.png]


### Example 4. Influx Line format over UDP socket

Python code to send measurement in Influx Line format: [4-stats-influx-line.py], telegraf config [telegraf-4-stats-influx-line.conf]. Stop other examples and run this one.

Grafana config is same as for Example 2.
[tutorial-materials/4-stats-influxline-config-and-results.png]

[3-stats-wavefront.py] code differs from Example 2/3 in couple of lines - formatting function and UDP socket related things:

...
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

...

def create_socket(self):
    try:
        sock = socket.socket(*self._socket_type)
        # no sock.connect
        self._sock = sock

...

def send_data(self, data):
    try:
        sent = self._sock.sendto(
            self._formatter(data).encode(self._encoding),
            self._socket_address
        )

...

reporter = StatsReporter(
    (socket.AF_INET, socket.SOCK_DGRAM),
    ('localhost', 8094),
    formatter=format_measurement_to_str_influxline
)

...

Influx Line data format has form '{measurement_name}{tags_str} {fields_str}'.
More about Influx Line data format - https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_tutorial/.

Example 4 code uses UDP socket (stream type).
Notice the difference of networking code for UDP socket code: no need to connect to socket (no `socket.connect` call). Datagram is just send over to specified network address. No need to keep established connection, no need to recreate connection once in a while. Which is rather convenient for sending stats, less socket management code. Downside is UDP doesn't guarantee datagrams delivery, like TCP does for packets of one data transmission sent over established connection.


I am not covering UNIX datagram socket config in this tutorial, but if telegraf config will have:

  service_address = "unixgram:///tmp/telegraf.sock"

and code will have:

  reporter = StatsReporter(
      (socket.AF_UNIX, socket.SOCK_DGRAM),
      '/tmp/telegraf.sock',
      ...
  )

that should do it. I haven't tried though.



## TCP, UDP and Unix sockets

Python program needs some way to report measurements to the other program (Telegraf process). For this sockets can be of use.

A socket is one endpoint of a two way communication link between two programs running on the network (https://www.geeksforgeeks.org/socket-in-computer-network/).

If curious to learn more about network sockets, suggested reading is this - https://pymotw.com/2/socket/index.html (and "see also" list on that page). Code is for Python 2 so method names might be outdated, but concepts are valid (and older than Python itself).

I'm providing code snippets that send measurements to TCP, UDP and Unix sockets, so can just use those if you're not interested in technical details of network communications. If unsure which one is best for you, suggest to use code and config from Example 4.

You can check out how socket Telegraf process uses look using command `lsof -p [pid of Telegraf process]`. To get `pid` (process id) of Telegraf process, can use `ps aux | grep telegraf` command. It will show stuff like device name which is assosiated with Telegraf's socket, socket type, etc. 


## Troubleshooting

If something doesn't look right, and data doesn't apper on dashboards, can lauch telegraf with `--debug` option, to make it print out more information about errors in processing of received data.

When telegraf successfully receives and write to InfluxDB measurements, it should produce console output similar to:

[tutorial-materials/example-telegraf-output.png]

You can see it also says that buffer is not full. Means all incomming metrics are making it to database, no dropped readings on telegraf's side. In real setup, some metrics could be lost in network before they got to telegraf, but this is not likely when everything runs on same machine.

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


In case you're having difficulties configuring Grafana dashboards, complete JSON that could be used to export dashboard configuration is in [grafana-dashboard-complete.json] file. Can try to export it in new dashboard or compare it's panels JSON with your panels.


## What I might write about in next post:

- will try to overload TCP socket (Unix socket, UDP socket) with metrics, see what happens
- will describe how to increase `read_buffer_size` in telegraf config, why not to increase it to huge value right away, and system socket listen queue size
- about techniques to measure dropped readings rate
