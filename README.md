Glances -- Eye on your system
=============================

## Description

Glances is a CLI curses based monitoring tool for GNU/Linux or BSD OS.

Glances uses the libstatgrab library to get information from your system.
It is developed in Python and uses the python-statgrab lib.

![screenshot](https://github.com/nicolargo/glances/raw/master/screenshot.png)

## Installation

### From package manager

Packages exist for Arch, Fedora, Redhat ...

### From source

Get the latest version:

	$ wget https://github.com/downloads/nicolargo/glances/glances-1.3.6.tar.gz

Glances use a standard GNU style installer:

	$ tar zxvf glances-1.3.6.tar.gz
	$ cd glances-1.3.6
	$ ./configure
	$ make
	$ sudo make install

Pre-requisites:

* Python 2.6+ (not tested with Python 3+)
* python-statgrab 0.5+ (did NOT work with python-statgrab 0.4)

Notes: For Debian.
The Debian Squeeze repos only include the python-statgrab 0.4.
You had to install the version 0.5 using the following commands:

	$ sudo apt-get install libstatgrab-dev pkg-config python-dev make
	$ wget http://ftp.uk.i-scream.org/sites/ftp.i-scream.org/pub/i-scream/pystatgrab/pystatgrab-0.5.tar.gz
	$ tar zxvf pystatgrab-0.5.tar.gz
	$ cd pystatgrab-0.5/
	$ ./setup.py build
	$ sudo ./setup.py install

Notes: For Ubuntu 10.04 and 10.10. 
The instruction to install the version 0.5 are here: 
https://github.com/nicolargo/glances/issues/5#issuecomment-3033194

## Running

Easy:

	$ glances.py

## User guide

By default, stats are refreshed every second, to change this setting, you can
use the -t option. For exemple to set the refrech rate to 5 seconds:

	$ glances.py -t 5

Importants stats are colored:

* GREEN:   stat counter is "OK"
* BLUE:    stat counter is "CAREFUL"
* MAGENTA: stat counter is "WARNING"
* RED:     stat counter is "CRITICAL"

When Glances is running, you can press:

* 'h' to display an help message whith the keys you can press
* 'a' to set the automatic mode. The processes are sorted automatically

    If CPU > 70%, sort by process "CPU consumption"

    If MEM > 70%, sort by process "memory size"

* 'c' to sort the processes list by CPU consumption
* 'd' Disable or enable the disk IO stats
* 'f' Disable or enable the file system stats
* 'm' to sort the processes list by process size
* 'n' Disable or enable the network interfaces stats
* 'q' Exit

### Header

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/header.png)

The header shows the Glances version, the host name and the operating 
system name, version and architecture.

### CPU

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/cpu.png)

The CPU states are shown as a percentage and for the configured refresh 
time.

If user|kernel|nice CPU is < 50%, then status is set to "OK".

If user|kernel|nice CPU is > 50%, then status is set to "CAREFUL".

If user|kernel|nice CPU is > 70%, then status is set to "WARNING".

If user|kernel|nice CPU is > 90%, then status is set to "CRITICAL".

### Load

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/load.png)

On the Nosheep blog, Zach defines the average load: "In short it is the 
average sum of the number of processes waiting in the run-queue plus the 
number currently executing over 1, 5, and 15 minute time periods."

Glances gets the number of CPU cores to adapt the alerts. With Glances, 
alerts on average load are only set on 5 and 15 mins. 

If average load is < O.7*Core, then status is set to "OK".

If average load is > O.7*Core, then status is set to "CAREFUL".

If average load is > 1*Core, then status is set to "WARNING".

If average load is > 5*Core, then status is set to "CRITICAL".

### Memory

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/mem.png)

Glances uses tree columns: memory (RAM), swap and "real".

Real used memory is: used - cache.

Real free memory is: free + cache.

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

If bitrate is < 50%, then status is set to "OK".

If bitrate is > 50%, then status is set to "CAREFUL".

If bitrate is > 70%, then status is set to "WARNING".

If bitrate is > 90%, then status is set to "CRITICAL".

For exemple, on a 100 Mbps Ethernet interface, the warning status is set 
if the bit rate is higher than 70 Mbps.

### Disk I/O

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/diskio.png)

Glances display the disk I/O throughput. The unit is adapted dynamicaly 
(bytes per second, Kbytes per second, Mbytes per second...).

There is no alert on this information.

### Filesystem

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/fs.png)

Glances display the total and used filesytem disk space. The unit is 
adapted dynamicaly (bytes per second, Kbytes per second, Mbytes per 
second...).

Alerts are set for used disk space:

If disk used is < 50%, then status is set to "OK".

If disk used is > 50%, then status is set to "CAREFUL".

If disk used is > 70%, then status is set to "WARNING".

If disk used is > 90%, then status is set to "CRITICAL".

### Processes

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/processlist.png)

Glances displays a summary and a list of processes.

By default (or if you hit the 'a' key) the process list is automaticaly 
sorted by CPU of memory consumption.

The number of processes in the list is adapted to the screen size.

### Footer

![screenshot](https://github.com/nicolargo/glances/raw/master/doc/footer.png)

Glances displays a caption and the current time/date.

## Localisation

To generate french locale execute as root or sudo :
i18n_francais_generate.sh

To generate spanish locale execute as root or sudo :
i18n_espanol_generate.sh

## Todo

You are welcome to contribute to this software.

* Packaging for Debian, Ubuntu, BSD...
* Check the needed Python library in the configure.ac
* Add file system stats when the python-statgrab is corrected
