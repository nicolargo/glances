[![Flattr this git repo](http://api.flattr.com/button/flattr-badge-large.png)](https://flattr.com/thing/484466/nicolargoglances-on-GitHub)
[![Build Status](https://travis-ci.org/nicolargo/glances.png?branch=master)](https://travis-ci.org/nicolargo/glances)

=============================
Glances -- Eye on your system
=============================

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/glances-white-256.png)

## Description

Glances is a CLI curses based monitoring tool for GNU/Linux and BSD OS.

Glances uses the PsUtil library to get information from your system.

It is developed in Python.

Console (80x24) screenshot:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/screenshot.png)

Wide terminal (> 90x24) screenshot:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/screenshot-wide.png)

## Installation

Pre-requisites (information for packagers):

* Python 2.6+ (not tested with Python 3+)
* build-essential (for installation via Pypi and setup.py)
* python-dev (for installation via Pypi)
* python-setuptools (for the installation via setup.py)
* python-psutil 0.4.1+ (replace the old libstatgrab's lib)
* python-jinja2 2.0+ (optional for HTML export)
* pysensors (Python library for sensors stats)

### From package manager (very easy way)

Packages exist for Debian (SID), Arch, Fedora, Redhat, FreeBSD...

Check if the version is the latest one.

### From PyPi (easy and cross platform way)

PyPi is an official Python package manager.

You first need to install PyPi on your system. For example on Debian/Ubuntu:

    $ sudo apt-get update
    $ sudo apt-get install python-pip build-essential python-dev

Then install the latest Glances version:

    $ sudo pip install Glances

Note: if you are behind an HTTP Proxy, you should use instead:

    $ sudo pip install --proxy=user:password@url:port Glances

### From [Homebrew](http://mxcl.github.com/homebrew/) for Mac OS X

    $ brew install brew-pip
    $ export PYTHONPATH=$(brew --prefix)/lib/python2.7/site-packages
    $ brew pip Glances

If you have the following error:

    Error: Failed executing: pip install glances==1.X --install-option=--prefix=/usr/local/XXX/glances/1.X (.rb:)

then try to run:

    $ pip install glances==1.X --install-option=--prefix=/usr/local/XXX/glances/1.X
    $ brew link Glances

### Concerning Windows operating system

Thanks to Nicolas Bourges, a Windows installer is available:

64 bits: https://s3.amazonaws.com/glances/glances-1.6.0-x64.exe
32 bits: https://s3.amazonaws.com/glances/glances-1.6.0-x86.exe

If you want to install it manually, please read the following procedure.

Windows operating system only support the Glances in server mode. So if you ran Glances on Windows, it will be automaticaly running in server mode.

To install Glances on you system:

    * Install [Python for Windows](http://www.python.org/getit/)
    * Install the [PsUtil lib](https://code.google.com/p/psutil/downloads/list)
    * Download the latest [Glances version](https://raw.github.com/nicolargo/glances/master/glances/glances.py)

I am looking for a contributor to package Glances for Windows (for exemple using [PyInstaller](http://www.pyinstaller.org/)).

### From source

Get the latest version (form GitHub):

    $ rm -rf /tmp/nicolargo-glances-*
    $ wget -O /tmp/glances-last.tgz https://github.com/nicolargo/glances/tarball/master

Glances use a standard GNU style installer (for a Debian like system):

    $ sudo apt-get update
    $ sudo apt-get install python-setuptools build-essential python-dev
    $ cd /tmp
    $ tar zxvf glances-last.tgz
    $ cd nicolargo-glances-*
    $ sudo python setup.py install

## Configuration

No configuration is needed to use Glances.

Furthermore, the release 1.6 introduces a configuration file to setup limits.

The default configuration file is under:

    /etc/glances/glances.conf (Linux)
or

    /usr/local/etc/glances.conf (*BSD and OS X)

To override the default configuration, you can copy the `glances.conf` file to
your `$XDG_CONFIG_HOME` directory (e.g. Linux):

    mkdir -p $XDG_CONFIG_HOME/glances
    cp /etc/glances/glances.conf $XDG_CONFIG_HOME/glances/

On OS X, you should copy the configuration file to `~/Library/Application Support/glances/`.

## Running

### In standalone mode

If you want to monitor your local machine, just run:

    $ glances

### In client/server mode

If you want to remotely monitor a machine (called server) from another one (called client).

Run this command on the server:

    server$ glances -s

and this one on the client:

    client$ glances -c @server

where @server is the IP address or hostname of the server

Glances uses a [XML/RPC](http://docs.python.org/2/library/simplexmlrpcserver.html) server and can be used by another client software.

In server mode, you can set the bind address (-B ADDRESS) and listenning TCP port (-p PORT).

In client mode, you can set the TCP port of the server (-p port).

Default binding address is 0.0.0.0 (Glances will listen on all the networks interfaces) and TCP port is 61209.

In client/server mode, limits are set by the server side.

The version 1.6 introduces a optionnal password to access to the server (-P password).

## User guide

Command line options are:

    -b		    Display network rate in Byte per second
	-B @IP|host	Bind server to the given IP or host NAME
	-c @IP|host	Connect to a Glances server
	-C file		Path to the configuration file
	-d		    Disable disk I/O module
	-e		    Enable the sensors module (Linux-only)
	-f file		Set the output folder (HTML) or file (CSV)
	-h		    Display the syntax and exit
	-m		    Disable mount module
	-n		    Disable network module
	-o output	Define additional output (available: HTML or CSV)
	-p PORT		Define the client or server TCP port (default: 61209)
	-P password	Client/server password
	-r		    Do not list processes (significant CPU use reduction)
	-s		    Run Glances in server mode
	-t sec		Set the refresh time in seconds (default: 3)
	-v		    Display the version and exit
	-y		    Enable the hddtemp module
	-z		    Do not use the bold color attribute

Importants stats are colored:

* GREEN:   stat counter is "OK"
* BLUE:    stat counter is "CAREFUL"
* MAGENTA: stat counter is "WARNING"
* RED:     stat counter is "CRITICAL"

When Glances is running, you can press:

* 'a' to set the automatic mode. The processes are sorted automatically

    IF CPU IoWait > 60% sort by process "IO read and write"

    If CPU > 70%, sort by process "CPU consumption"

    If MEM > 70%, sort by process "memory size"

* 'b' switch between bit/s or byte/s for network IO
* 'c' sort the processes list by CPU consumption
* 'd' disable or enable the disk IO stats
* 'e' enable the sensors module (PySensors library is needed; Linux-only)
* 'f' disable or enable the file system stats
* 'h' to display a help message with the keys you can press and the limits
* 'i' sort the processes list by IO rate (need root account on some OS)
* 'l' disable or enable the logs
* 'm' sort the processes list by process MEM
* 'n' disable or enable the network interfaces stats
* 'p' sort by process name
* 's' disable or enable the sensor stats (only available with -e tag)
* 't' View network IO as combination
* 'u' View cumulative network IO
* 'w' delete finished warning logs messages
* 'x' delete finished warning and critical logs messages
* '1' switch between global CPU and per core stats
* 'q' Exit

### Header

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/header.png)

The header shows the host name and the operating system name, version and architecture.

### CPU

Short view:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/cpu.png)

If horizontal space is available, extended CPU infomations are displayed.

Extended view (only available if your terminal is wide enough)

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/cpu-wide.png)

If user click on the '1' key, per CPU stats is displayed:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/percpu.png)

The CPU stats are shown as a percentage and for the configured refresh
time. The total CPU usage is displayed on the first line.

Color code used:

If user|kernel|nice CPU is < 50%, then status is set to "OK".

If user|kernel|nice CPU is > 50%, then status is set to "CAREFUL".

If user|kernel|nice CPU is > 70%, then status is set to "WARNING".

If user|kernel|nice CPU is > 90%, then status is set to "CRITICAL".

### Load

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/load.png)

On the Nosheep blog, Zach defines average load: "In short it is the
average sum of the number of processes waiting in the run-queue plus the
number currently executing over 1, 5, and 15 minute time periods."

Glances gets the number of CPU cores to adapt the alerts. With Glances,
alerts on average load are only set on 5 and 15 mins. The first line
also display the number of CPU core.

If average load is < O.7*Core, then status is set to "OK".

If average load is > O.7*Core, then status is set to "CAREFUL".

If average load is > 1*Core, then status is set to "WARNING".

If average load is > 5*Core, then status is set to "CRITICAL".

### Memory

Glances uses two columns: one for the RAM and another one for the SWAP.

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/mem.png)

If space is available, Glances displays extended informations:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/mem-wide.png)

With Glances, alerts are only set for on used swap and real memory.

If memory is < 50%, then status is set to "OK".

If memory is > 50%, then status is set to "CAREFUL".

If memory is > 70%, then status is set to "WARNING".

If memory is > 90%, then status is set to "CRITICAL".

### Network bit rate

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/network.png)

Glances display the network interface bit rate. The unit is adapted
dynamicaly (bits per second, Kbits per second, Mbits per second...).

Alerts are set only if the network interface maximum speed is available.

If bit rate is < 50%, then status is set to "OK".

If bit rate is > 50%, then status is set to "CAREFUL".

If bit rate is > 70%, then status is set to "WARNING".

If bit rate is > 90%, then status is set to "CRITICAL".

For example, on a 100 Mbps Ethernet interface, the warning status is set
if the bit rate is higher than 70 Mbps.

### Sensors (optional; only available on Linux)

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/sensors.png)

Optionally, Glances displays the sensors informations (lm-sensors).

A filter is processed in order to only display temperature.

You should enable this module using the following command line:

    glances -e

There is no alert on this information.

### Disk I/O

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/diskio.png)

Glances displays the disk I/O throughput. The unit is adapted dynamically
(bytes per second, Kbytes per second, Mbytes per second...).

There is no alert on this information.

### Filesystem

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/fs.png)

Glances displays the total and used filesytem disk space. The unit is
adapted dynamically (bytes per second, Kbytes per second, Mbytes per
second...).

Alerts are set for used disk space:

If disk used is < 50%, then status is set to "OK".

If disk used is > 50%, then status is set to "CAREFUL".

If disk used is > 70%, then status is set to "WARNING".

If disk used is > 90%, then status is set to "CRITICAL".

### Processes

Short view:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/processlist.png)

Long view (only available if your terminal is wide enough)

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/processlist-wide.png)

Glances displays a summary and a list of processes.

By default (or if you hit the 'a' key) the process list is automatically
sorted by CPU of memory consumption.

The number of processes in the list is adapted to the screen size.

* VIRT: Virtual memory size (in byte)
* REST: Amount of resident memory (in byte)
* CPU%: % of CPU used by the process
* MEM%: % of MEM used by the process
* PID: Process ID
* USER: Process user ID
* NI: Nice level of the process
* S: Process status

   R - Running
   D - Sleeping (may not be interrupted)
   S - Sleeping (may be interrupted)
   T - Traced or stopped
   Z - Zombie or "hung" process

* TIME+:  Cumulative CPU time used
* IO_R and IO_W: Per process IO read and write rate (in byte per second)
* NAME: Process name or command line

### Logs

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/logs.png)

A logs list is displayed in the bottom of the screen if (and only if):

* at least one WARNING or CRITICAL alert was occured.
* space is available in the bottom of the console/terminal

There is one line per alert with the following information:

* start date
* end date
* alert name
* (min/avg/max) values

### Footer

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/footer.png)

Glances displays the current time/date and access to the embedded help screen.

If you have ran Glances in client mode (-c), you can also see if the client is connected to the server.

If client is connected:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/client-connected.png)

else:

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/client-disconnected.png)

On the left, you can easely seen if you are connected to a Glances server.

## Localisation

Glances localization files exist for:

* English (default langage)
* French
* Italian
* Spanish
* Portugal

Feel free to contribute !
