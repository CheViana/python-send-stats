---
title: Reporting Measurements from Python Code in Real Time: a Beginner-Friendly Tutorial
published: true
description: Simple examples how to send measurements from Python code to the real-time monitoring solution
tags: #python #monitoring #tutorial #telegraf
cover_image: https://dev-to-uploads.s3.amazonaws.com/i/dba9ekv9amhyc3mivfsb.png
---


# Reporting measurements from Python code in real time

A simple example of how to send measurements from Python code to the real-time monitoring solution (Telegraf/InfluxDB/Grafana).

Code-reported measurements can be:
- price of an order user just submitted
- amount of free beds in the hospital
- how long did a backend call take
- percent of file that is already processed, and percent that's left
- ...
- any number of which the program is aware and which might be useful to track 


I don't think I need to make a lot of arguments in favor of real-time monitoring: it's a blessing in time of turmoil (outage). Data collected (good times data, outages data) can be analyzed later for various purposes: notice weird pattern in performance over time, notice significant features of traffic that can be leveraged, notice what happens right before outage, ... . 

We will start with simple examples of Python programs that report measurements data. But first we need to configure things that are going to listen, record, and display these measurements.


## Tutorial materials

All files mentioned are available in the repo [CheViana/python-send-stats](https://github.com/CheViana/python-send-stats).


## Looking for a quick, ready, robust solution?

Setup Grafana, InfluxDB, Telegraf and use Example 1 code snippet / Telegraf config.


## Setup Grafana, InfluxDB, Telegraf

In short, install Grafana, InfluxDB, Telegraf:

- Visit https://portal.influxdata.com/downloads/ for information on how to install InfluxDB and Telegraf
- Visit https://grafana.com/grafana/download for information on how to install Grafana

Launch Grafana and InfluxDB with default configs:
```
> cd grafana-7.1.0
> bin/grafana-server
```

In other terminal tab:
```
> influxd -config /usr/local/etc/influxdb.conf
```


## Example 1. The simplest example of how to send stats from Python code in 6 lines, and of suitable Telegraf config

First, we're going to make Telegraf listen on the Internet datagram socket for JSON-formatted measurements that Python code will send. Telegraf will write received measurements to database.

https://github.com/CheViana/python-send-stats/blob/master/telegraf-1-stats-simple-datagram-json.conf:

```
...

[[outputs.influxdb]]
  urls = ["http://127.0.0.1:8086"]
  database = "socket-stats"

[[inputs.socket_listener]]
  service_address = "udp://:8094"
  data_format = "json"
  json_name_key = "metric_name"
```

Launch Telegraf with this config:
```
> telegraf -config telegraf-1-stats-simple-datagram-json.conf
```

More info on telegraf plugin that enables listening for data on socket: [socket_listener docs](https://github.com/influxdata/telegraf/blob/release-1.14/plugins/inputs/socket_listener/README.md).


[1-stats-simple-datagram-json.py](https://github.com/CheViana/python-send-stats/blob/master/1-stats-simple-datagram-json.py) is simple Python program that sends measurements to UDP socket. Measurements are sent in [Telegraf JSON format](https://github.com/influxdata/telegraf/tree/master/plugins/parsers/json) every 2 seconds.

[1-stats-simple-datagram-json.py](https://github.com/CheViana/python-send-stats/blob/master/1-stats-simple-datagram-json.py):

```
import time
import socket
import json
import random


while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(
            json.dumps({'metric_name': 'good_metric_name', 'value1': 10, 'value2': random.randint(1, 10)}).encode(),
            ('localhost', 8094)
        )
        print('Sending sample data...')
        sock.close()
    except socket.error as e:
        print(f'Got error: {e}')

    time.sleep(2)
```

Start the program that sends stats to socket:

```
> python3 1-stats-simple-datagram-json.py
```

This is a complete working example. A tiny piece of code that does what you want it to do - report measurements:

```
good_metric_name,value1=10,value2=7
good_metric_name,value1=10,value2=2
good_metric_name,value1=10,value2=5
...
```

In this example, measurement name is not tied to Telegraf config - Telegraf uses measurement name found under key 'metric_name' in JSON that is sent to it. More about this below.


## Metric name gotchas

Metric name (also tag name, tag value, any string value reported) should not contain ':', '|', ',', '='. Better to use '-', '_' or '.' as delimiter in metric name. Special characters in reported string values could cause errors during measurement parsing in Telegraf or in InfluxDB, and these errors are easy to miss.


## Grafana Dashboard

Add source for InfluxDB database "socket-stats".
Create new dashboard, add panel which will display measurements sent to Telegraf client.

![Example 1 Grafana dashboard config](https://dev-to-uploads.s3.amazonaws.com/i/567reez3f2bh9o118s2m.png)

Provided all 4 processes are running (Grafana, InfluxDB, Telegraf and Python program that sends stats), you should see measurements appear on dashboard in real time. Exciting, isn't it?


## Example 2. JSON measurements over TCP socket (UNIX domain)

For UDP sockets there's no need to keep connection open, because of how protocol works. However, it might be not possible to use UDP sockets in some network setups, or it's possible but rate of dropped packets is too big: most measurement readings are lost.
Alternative is to use TCP sockets (also called Stream socket). For TCP sockets it's an overhead to open and close connection each time measurement is sent, which could be around 10 times per second. Opening and closing connections is a CPU-expensive operation.
TCP socket can be UNIX domain or INTERNET domain. UNIX domain are better suited for processes that run on same network host, but can't be used when communicating processes are running on different network hosts. Better suited because low-level code that handles UNIX domain socket communication skips some checks that would be needed for INTERNET socket.
For our Python snippets code difference for UNIX domain / INTERNET domain is just socket address and socket type value. See Example 3 for INTERNET domain example.

There are resources on socket types mentioned [below](https://pymotw.com/2/socket/index.html).

Program that uses a TCP socket (UNIX domain) in such a way that the socket connection is established when the program starts, and the connection is closed when the program exits is available in [2-stats-json.py](https://github.com/CheViana/python-send-stats/blob/master/2-stats-json.py):

```
import time
import socket
import json
import random
import atexit


def format_measurement_data_json(data):
    data['format'] = 'json'
    return json.dumps(data) + '\n'


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
            sock.connect(self._socket_address)
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
            sent = self._sock.send(
                self._formatter(data).encode(self._encoding)
            )
            print(f'Sending sample data... {sent}')
        except (AttributeError, socket.error) as e:
            print(f'Got error while sending data on socket: {e}')

            # attempt to recreate socket on error
            self.close_socket()
            self.create_socket()


reporter = StatsReporter(
    (socket.AF_UNIX, ),
    '/tmp/telegraf.sock',
    formatter=format_measurement_data_json
)
atexit.register(reporter.close_socket)


while True:
    reporter.send_data({'value1': 10, 'value2': random.randint(1, 10)})
    time.sleep(1)
```

This program opens the connection once and sends measurement over it every second. If the send fails, connection is reestablished. When program exits, the socket is closed using [atexit](https://docs.python.org/3/library/atexit.html). Even better way would be to reestablish connection once in a while, say every one minute.

`StatsReporter` class encapsulates operations with socket: 
creating, sending data, closing; it also keeps reference to open socket as a field which all those methods can use.

Formatting of measurement data from Python dict into string sent over wire is performed in `format_measurement_data_json` function. This function is passed as an argument to `StatsReporter` class, so it will be easy to change data format in future examples. 
A tag which corresponds to data format is added in order to distinguish between measurements reported in a different example, and just as an example of a tag.

`\n` at the end of string that is sent is crucial, this is how Telegraf recognizes the end of a measurement. Without `\n` at the end of measurement string one can encounter errors like:

````
  2020-11-10T14:42:17Z E! [inputs.socket_listener] Unable to parse incoming line: invalid character '{' after top-level value
```

Stop Example 1 Python program and Telegraf, and run Example 2 Python program [2-stats-json.py](https://github.com/CheViana/python-send-stats/blob/master/2-stats-json.py) and launch Telegraf for it with config [telegraf-2-stats-json.conf](https://github.com/CheViana/python-send-stats/blob/master/telegraf-2-stats-json.conf):
```
> python3 2-stats-json.py

In other terminal tab
> telegraf -config telegraf-2-stats-json.conf
```

 You should see measurements in real time on dashboard:

![Example 2 Grafana dashboard config and results](https://dev-to-uploads.s3.amazonaws.com/i/ubu8v7s51j5jvrlgxda1.png)


[telegraf-2-stats-json.conf](https://github.com/CheViana/python-send-stats/blob/master/telegraf-2-stats-json.conf#L658) specifies field `name_override = "good_metric_name"`, which is used as measurement name in database records:

```
[[inputs.socket_listener]]
  service_address = "unix:///tmp/telegraf.sock"
  data_format = "json"
  name_override = "good_metric_name"
  tag_keys = ["format"]
```

 Default measurement name would be a non-descriptive input plugin name (e.g. `socket_listener`). It is also possible to specify the key `json_name_key` in Telegraf config to store a measurement in the database with a custom name:

```
[[inputs.socket_listener]]
  service_address = "unix:///tmp/telegraf.sock"
  data_format = "json"
  json_name_key = "metric_name"
```

Then when Telegraf receives the following measurement data:

```
{"metric_name": "speed", "value": 10}
```

The measurement named `speed` with `value=10` will be saved to DB.
This way is more flexible and avoids the need to update config when measurement name varies.

 See more in [JSON Telegraf format docs](https://github.com/influxdata/telegraf/tree/master/plugins/parsers/json).

 Example 2 telegraf config also specifies `tag_keys = ["format"]` - meaning from measurement data dictionary `{'value': 1, 'format': 'json'}` `format` will be used as a tag for measurement (consult [InfluxDB docs](https://docs.influxdata.com/influxdb/v2.0/reference/key-concepts/) if that doesn't mean much to you).


## Example 3. Wavefront (VMWare) Telegraf data format over TCP socket (INTERNET domain)

Python code to send measurement in wavefront format [3-stats-wavefront.py](https://github.com/CheViana/python-send-stats/blob/master/3-stats-wavefront.py), telegraf config [telegraf-3-stats-wavefront.conf](https://github.com/CheViana/python-send-stats/blob/master/telegraf-3-stats-wavefront.conf). Stop other examples and run this one:

```
> python3 3-stats-wavefront.py

In other terminal tab
> telegraf -config telegraf-3-stats-wavefront.conf
```

[3-stats-wavefront.py](https://github.com/CheViana/python-send-stats/blob/master/3-stats-wavefront.py) code differs from Example 2 in couple of lines - formatting function and socket type/address:

```
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

...

```

Wavefront format uses timestamp in seconds, so timestamp is set in Python code using `time.time()` without decimal fraction. Omitting timestamp didn't work out for me.
`\n` at the end of str that is sent is quite crucial (same as for Example 2, or any code snippet using TCP socket). Wavefront format also requires `source` tag. `format="wavefront"` part of string is example of how measurement tags should be added.
More about Wavefront data format - in [wavefront docs](https://docs.wavefront.com/wavefront_data_format.html).

Wavefront code piece is using TCP socket, INTERNET domain. This code snippet is suitable when program that sends metrics and Telegraf process run on different hosts. Generally, this code snippet should work in any network configuration, so it can be called more universal than previous examples. TCP connection is reused in similar fashion as in Example 2 for Unix stream socket.

Wavefront Example also has different names of measurements. It can only do single field value per measurement, whereas JSON and Influx Line formats can do measurements with multiple fields - [more about multiple fields measurements](https://stackoverflow.com/questions/45368535/influxdb-single-or-multiple-measurement). So will have to update dashboard or make new panel to see results:

![Example 3 Grafana dashboard config and results](https://dev-to-uploads.s3.amazonaws.com/i/vxje435q0gnun5p1d1wx.png)


## Example 4. Influx Line format over UDP socket

Python code to send measurement in Influx Line format: [4-stats-influx-line.py](https://github.com/CheViana/python-send-stats/blob/master/4-stats-influx-line.py), telegraf config [telegraf-4-stats-influx-line.conf](https://github.com/CheViana/python-send-stats/blob/master/telegraf-4-stats-influx-line.conf). Stop other examples and run this one:

```
> python3 4-stats-influx-line.py

In other terminal tab
> telegraf -config telegraf-4-stats-influx-line.conf
```

Grafana config is same as for Example 2 so you should be able to see real-time results on dashboard:

![Example 4 Grafana dashboard config and results](https://dev-to-uploads.s3.amazonaws.com/i/vdjjiow5r69i16nqcdbe.png)

[4-stats-influx-line.py](https://github.com/CheViana/python-send-stats/blob/master/4-stats-influx-line.py) code differs from Example 2 and 3 in couple of lines - formatting function and UDP socket related things:

```
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
        sent = self._sock.sendto(  # sendto not send
            self._formatter(data).encode(self._encoding),
            self._socket_address  # socket address
        )

...

reporter = StatsReporter(
    (socket.AF_INET, socket.SOCK_DGRAM),
    ('localhost', 8094),
    formatter=format_measurement_to_str_influxline
)

...
```

Influx Line data format is string of form `'{measurement_name}{tags_str} {fields_str}'`.
More about Influx Line data format in [it's docs](https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_tutorial/).

Influx Line example code piece uses UDP socket (Internet type datagram socket).
Notice the difference of networking code for UDP socket code compared to Examples 2 and 3: no need to connect to socket (no `socket.connect` call). Datagram is just send over to specified network address. No need to keep established connection, no need to recreate connection once in a while. Which is rather convenient for sending stats, less socket management code. Downside is UDP doesn't guarantee datagrams delivery, like TCP does for packets of one data transmission sent over established connection. UDP communication might not be good option for every network setup - need to measure how much packets are lost before using it.

I am not covering UNIX type datagram socket config in this tutorial, but if Telegraf config will have:
```
  service_address = "unixgram:///tmp/telegraf.sock"
```
and code of Example 4 will have:
```
  reporter = StatsReporter(
      (socket.AF_UNIX, socket.SOCK_DGRAM),
      '/tmp/telegraf.sock',
      ...
  )
```
that should do it. I haven't tried though.



## More about sockets

If curious to learn more about sockets, suggested reading is this - https://pymotw.com/2/socket/index.html (and "see also" list on that page). Code is for Python 2 so method names might be outdated, but concepts are valid (and older than Python itself).

I'm providing code snippets that send measurements to UNIX stream socket (Example 2), Internet stream socket (Example 3) and Internet datagram socket (Examples 1 and 4). Can just use those if you're not interested in technical details of network communications. If unsure which one is best for you, I suggest to use code and config from Example 1 or Example 4.

You can check out how socket Telegraf process uses look using command `lsof -p [pid of Telegraf process]`. To get `pid` (process id) of Telegraf process, can use `ps aux | grep telegraf` command. `lsof` will show stuff like device name which is associated with Telegraf's socket, socket type, other curiosities. 


## Troubleshooting

If data doesn't appear on dashboards, can launch Telegraf with `--debug` option, to make it print out more information about errors in processing of received data.

When Telegraf successfully receives and write to InfluxDB measurements, it should produce console output similar to:

![telegraf output](https://dev-to-uploads.s3.amazonaws.com/i/gojd6qzhjon4dy5bce0h.png)


You can see it also says that buffer is not full. Means all incoming metrics are making it to database, no dropped readings on Telegraf's side. In real setup, some metrics could be lost in network before they got to Telegraf, but this is not likely when everything runs on same machine.

Also good idea is to check in case of issues:
- InfluxDB is launched
- InfluxDB address in Telegraf config matches the one in InfluxDB config
- Grafana dashboard configuration - address of InfluxDB and database name, measurement names
- Python code sends data to correct socket address, the one Telegraf listens on (specified in Telegraf config)

### InfluxDB data investigation

To debug what's being written to InfluxDB, can use [Influx CLI](https://docs.influxdata.com/influxdb/v1.8/query_language/explore-data/) or [influx flux query language](https://docs.influxdata.com/influxdb/v2.0/query-data/get-started/). I've used Influx CLI and `SELECT` statements, as this is something I'm more familiar with.
Launch Influx CLI with command `influx`. To show list of available databases, use command `show databases`. Switch to database Telegraf sends data to using `use "socket-stats"` command. Show all measurement names using `show measurements`. To see what's going on in particular measurement, can use `select *::field from "value1"` - it will show all fields and all data for measurement called "value1". `select *::field from "value1" limit 3` will show 3 oldest data points, `select last(*::field) from "value1"` will show newest data point.

![Influx CLI example](https://dev-to-uploads.s3.amazonaws.com/i/zc29oeqbm04bf7ctnl8q.png)
![Influx CLI latest measurement](https://dev-to-uploads.s3.amazonaws.com/i/kefuyxl4t0hjtumx5mak.png)

These screenshots show my trouble: `value2` timestamp value is not correct, it's millisecond-precision Unix time whereas data format requires nanosecond-precision Unix time (like "test.value2" timestamp). So `value2` timestamp is interpreted as way older timestamp than it should be (it has late 60s vibe), and won't show up on "last 5 min" Grafana dashboard.

![Readings from the past](https://dev-to-uploads.s3.amazonaws.com/i/xhpiqxduv3u4uh2g4j0i.png)


### Measurement timestamp

It is possible to report timestamp of measurement from Python code, or leave it up to InfluxDB to record timestamp of when reading arrives. Delay between two event is usually negligible: on same machine - real tiny, over network - depends on network, but like couple milliseconds, maybe hundred milliseconds. My suggestion is to leave it up to InfluxDB, to avoid issues when reported time from Python is not correct due to bugs, or different machines have different clock time. If exact time of reading with nanosecond precision is important to you, add timestamp field in Python code. 
Anyway, if reporting program and InfluxDB run on different machines, make sure [Network Time Protocol (NTP)|http://www.ntp.org/] is utilized to keep clocks in sync.

### Dashboard issues

In case you're having difficulties configuring Grafana dashboards, complete JSON that could be used to export dashboard configuration is in [grafana-dashboard-complete.json](https://github.com/CheViana/python-send-stats/blob/master/grafana-dashboard-complete.json) file. Can try to export it in new dashboard or compare it's panels JSON with your panels.


## What I might write about in next post:

- overloading TCP socket (Unix socket, UDP socket) with metrics, and checking out what happens; looking into `read_buffer_size` in Telegraf config and system socket listen queue size; techniques to measure dropped readings rate
- reporting stats of backend calls (`aiohttp` and `requests`)
- optimal uWSGI configurations, for best performance when all is good, and backend failure-resistant configurations
- uWSGI serving Django with aiohttp communications
- babel 7 configurations for less JS in bundle
- running python tests in parallel, and tests coverage  
