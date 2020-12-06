Notes and materials for blog post about sending stats from Python code to Telegraf/InfluxDB/Grafana

## Running code examples

### Prerequirements: Python3

Install Python3: https://docs.python-guide.org/starting/install3/.

Make sure when you run
```
python --version
```

It prints out 'python3' (could be 'python3.9', or 'python3.7', etc).

### Prerequirements: Install and launch Telegraf, InfluxDB, Grafana

To install all tools for MacOS, run in terminal:

    brew install influxdb  # Database for metrics
    brew install telegraf  # agent-collector of metrics
    brew install graphana  # UI for metrics exploration and plotting

To download all tools binaries for Linux:

    wget https://dl.influxdata.com/influxdb/releases/influxdb-1.8.2_linux_amd64.tar.gz
    tar xvfz influxdb-1.8.2_linux_amd64.tar.gz
    wget https://dl.influxdata.com/telegraf/releases/telegraf-1.15.2_linux_amd64.tar.gz
    tar xf telegraf-1.15.2_linux_amd64.tar.gz
    wget https://dl.grafana.com/oss/release/grafana-7.1.4.linux-amd64.tar.gz
    tar -zxvf grafana-7.1.4.linux-amd64.tar.gz

Visit https://portal.influxdata.com/downloads/ for more information on how to install InfluxDB and Telegraf.
Visit https://grafana.com/grafana/download for more information on how to install Grafana.

Launch Telegraf, InfluxDB, Grafana (each in its own shell tab):
```
influxd -config /usr/local/etc/influxdb.conf
```

```
cd grafana-7.1.0/
bin/grafana-server
```

```
telegraf -config telegraf.conf
```
File telegraf.conf can be found in [here](https://github.com/CheViana/network-calls-stats/blob/master/telegraf.conf).

To see results on dashboard need to keep Telegraf, InfluxDB, Grafana running while Python scripts are running.

### Examples repository

Checkout [repository](https://github.com/CheViana/network-calls-stats/) with code examples and Telegraf configuration files.

### Python dependencies

It's best to create virtual environment to keep dependencies of project isolated from system Python packages, and dependencies of other projects. For that, I suggest to use [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html) and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/install.html). Need to install these tools if you don't have them installed already.

Create virtual environment using `virtualenvwrapper`:
```
mkvirtualenv network-calls-stats
```

Create virtual environment using only `virtualenv`:
```
virtualenv venv
source venv/bin/activate
```

Install libraries needed to run example code from repo:
```
pip install -r requirements.txt
```

### Run example Python scripts

Provided previuos steps were performed (python installed, virtualenv created, dependencies pip-installed), it's easy to run example program:
```
python example-1-aiohttp-send-stats-basic.py
```

There should appear output in terminal:
```
(network-calls-stats) ➜  network-calls-stats git:(master) ✗ python example-1-aiohttp-send-stats-basic.py
Reported stats: aiohttp_request_exec_time=58, tags={'domain': 'www.python.org'}
Reported stats: aiohttp_request_exec_time=76, tags={'domain': 'www.mozilla.org'}
Reported stats: call_python_and_mozilla_using_aiohttp_exec_time=90, tags={}
Py response piece: <!doctype html>
<!--[if lt IE 7]>   <html class="no-js ie6 l... ,
Moz response piece: <!doctype html>

<html class="windows x86 no-js" lang="e...
```

### Get measurements appearing on dashboard

To view reported request time stats on dashboard, need to setup datasource and panels in Grafana.

Navigate to grafana dashboard in browser (http://localhost:3000/). Add new data source:

![Grafana add datasource](tutorial-images/setup-dashboard-add-new-source.png)
![Grafana datasource Influx](tutorial-images/setup-dashboard-add-source-influx.png)
![Grafana configure datasource](tutorial-images/setup-dashboard-configure-source.png)

This data source should be used when configuring panels.

Let's create new dashboard for network stats, and add a panel to it.
Go to "Dashboards" in left side thin menu (icon looks like 4 bricks), pick "Manage", click on "New dashboard". Click "New panel" or "Add panel" in top right corner.
Pick "Edit" in dropdown next to new panel title.
Here's how to configure panel for Example 1:
![Configure Grafana panel](tutorial-images/example-1-request-time-dashboard-config-1.png)

Need to pick data source in the left corner of "Query" tab (center of screen) and provide measurement name in query editing section. To update panel name look in the right column on top.

To make Y axis values display with "ms", look in the right side column - "Panel" tab, "Axes" collapsible, "Left Y" - select "Time" and "milliseconds":
![Configure Grafana panel Y axis](tutorial-images/example-1-request-time-dashboard-config-2.png)

Don't forget to save. More [documentation](https://grafana.com/docs/grafana/latest/panels/add-a-panel/) on Grafana dashboards.


### Troubleshooting Telegraf, InfluxDB, Grafana

I've got some hints on what to check and how to check in [this post](https://dev.to/cheviana/reporting-measurements-from-python-code-in-real-time-4g5#troubleshooting).

[Full Grafana dashboard JSON](https://github.com/CheViana/network-calls-stats/blob/master/grafana-model.json) can be used to compare panel settings.
