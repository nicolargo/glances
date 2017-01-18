.. _cmds:

Command Reference
=================

Command-Line Options
--------------------

.. option:: -h, --help

    show this help message and exit

.. option:: -V, --version

    show program's version number and exit

.. option:: -d, --debug

    enable debug mode. The debugging output is saved to /tmp/glances-USERNAME.log.

.. option:: -C CONF_FILE, --config CONF_FILE

    path to the configuration file

.. option:: --disable-alert

    disable alert/log module

.. option:: --disable-amps

    disable application monitoring process module

.. option:: --disable-cpu

    disable CPU module

.. option:: --disable-diskio

    disable disk I/O module

.. option:: --disable-docker

    disable Docker module

.. option:: --disable-folders

    disable folders module

.. option:: --disable-fs

    disable file system module

.. option:: --disable-hddtemp

    disable HD temperature module

.. option:: --disable-ip

    disable IP module

.. option:: --disable-irq

    disable IRQ module

.. option:: --disable-load

    disable load module

.. option:: --disable-mem

    disable memory module

.. option:: --disable-memswap

    disable memory swap module

.. option:: --disable-network

    disable network module

.. option:: --disable-now

    disable current time module

.. option:: --disable-ports

    disable Ports module

.. option:: --disable-process

    disable process module

.. option:: --disable-raid

    disable RAID module

.. option:: --disable-sensors

    disable sensors module

.. option:: --disable-wifi

    disable Wifi module

.. option:: -0, --disable-irix

    task's CPU usage will be divided by the total number of CPUs

.. option:: -1, --percpu

    start Glances in per CPU mode

.. option:: -2, --disable-left-sidebar

    disable network, disk I/O, FS and sensors modules (py3sensors lib
    needed)

.. option:: -3, --disable-quicklook

    disable quick look module

.. option:: -4, --full-quicklook

    disable all but quick look and load

.. option:: -5, --disable-top

    disable top menu (QuickLook, CPU, MEM, SWAP and LOAD)

.. option:: -6, --meangpu

    start Glances in mean GPU mode

.. option:: --enable-history

    enable the history mode (matplotlib lib needed)

.. option:: --disable-bold

    disable bold mode in the terminal

.. option:: --disable-bg

    disable background colors in the terminal

.. option:: --enable-process-extended

    enable extended stats on top process

.. option:: --export-graph

    export stats to graph

.. option:: --path-graph PATH_GRAPH

    set the export path for graph history

.. option:: --export-csv EXPORT_CSV

    export stats to a CSV file

.. option:: --export-cassandra

    export stats to a Cassandra/Scylla server (cassandra lib needed)

.. option:: --export-couchdb

    export stats to a CouchDB server (couchdb lib needed)

.. option:: --export-elasticsearch

    export stats to an Elasticsearch server (elasticsearch lib needed)

.. option:: --export-influxdb

    export stats to an InfluxDB server (influxdb lib needed)

.. option:: --export-opentsdb

    export stats to an OpenTSDB server (potsdb lib needed)

.. option:: --export-rabbitmq

    export stats to RabbitMQ broker (pika lib needed)

.. option:: --export-statsd

    export stats to a StatsD server (statsd lib needed)

.. option:: --export-riemann

    export stats to Riemann server (bernhard lib needed)

.. option:: --export-zeromq

    export stats to a ZeroMQ server (zmq lib needed)

.. option:: -c CLIENT, --client CLIENT

    connect to a Glances server by IPv4/IPv6 address or hostname

.. option:: -s, --server

    run Glances in server mode

.. option:: --browser

    start the client browser (list of servers)

.. option:: --disable-autodiscover

    disable autodiscover feature

.. option:: -p PORT, --port PORT

    define the client/server TCP port [default: 61209]

.. option:: -B BIND_ADDRESS, --bind BIND_ADDRESS

    bind server to the given IPv4/IPv6 address or hostname

.. option:: --username

    define a client/server username

.. option:: --password

    define a client/server password

.. option:: --snmp-community SNMP_COMMUNITY

    SNMP community

.. option:: --snmp-port SNMP_PORT

    SNMP port

.. option:: --snmp-version SNMP_VERSION

    SNMP version (1, 2c or 3)

.. option:: --snmp-user SNMP_USER

    SNMP username (only for SNMPv3)

.. option:: --snmp-auth SNMP_AUTH

    SNMP authentication key (only for SNMPv3)

.. option:: --snmp-force

    force SNMP mode

.. option:: -t TIME, --time TIME

    set refresh time in seconds [default: 3 sec]

.. option:: -w, --webserver

    run Glances in web server mode (bottle lib needed)

.. option:: --cached-time CACHED_TIME

    set the server cache time [default: 1 sec]

.. option:: open-web-browser

    try to open the Web UI in the default Web browser

.. option:: -q, --quiet

    do not display the curses interface

.. option:: -f PROCESS_FILTER, --process-filter PROCESS_FILTER

    set the process filter pattern (regular expression)

.. option:: --process-short-name

    force short name for processes name

.. option:: --hide-kernel-threads

    hide kernel threads in process list

.. option:: --tree

    display processes as a tree

.. option:: -b, --byte

    display network rate in byte per second

.. option:: --diskio-show-ramfs

    show RAM FS in the DiskIO plugin

.. option:: --diskio-iops

    show I/O per second in the DiskIO plugin

.. option:: --fahrenheit

    display temperature in Fahrenheit (default is Celsius)

.. option:: --fs-free-space

    display FS free space instead of used

.. option:: --theme-white

    optimize display colors for white background

.. option:: --disable-check-update

    disable online Glances version ckeck

Interactive Commands
--------------------

The following commands (key pressed) are supported while in Glances:

``ENTER``
    Set the process filter

    **Note**: on macOS, please use ``CTRL-H`` to delete
    filter.

    Filter is a regular expression pattern:

    - ``gnome``: matches all processes starting with the ``gnome``
      string

    - ``.*gnome.*``: matches all processes containing the ``gnome``
      string

``a``
    Sort process list automatically

    - If CPU ``>70%``, sort processes by CPU usage

    - If MEM ``>70%``, sort processes by MEM usage

    - If CPU iowait ``>60%``, sort processes by I/O read and write

``A``
    Enable/disable Application Monitoring Process

``b``
    Switch between bit/s or Byte/s for network I/O

``B``
    View disk I/O counters per second

``c``
    Sort processes by CPU usage

``d``
    Show/hide disk I/O stats

``D``
    Enable/disable Docker stats

``e``
    Enable/disable top extended stats

``E``
    Erase current process filter

``f``
    Show/hide file system and folder monitoring stats

``F``
    Switch between file system used and free space

``g``
    Generate graphs for current history

``h``
    Show/hide the help screen

``i``
    Sort processes by I/O rate

``I``
    Show/hide IP module

``l``
    Show/hide log messages

``m``
    Sort processes by MEM usage

``M``
    Reset processes summary min/max

``n``
    Show/hide network stats

``N``
    Show/hide current time

``p``
    Sort processes by name

``q|ESC``
    Quit the current Glances session

``Q``
    Show/hide IRQ module

``r``
    Reset history

``R``
    Show/hide RAID plugin

``s``
    Show/hide sensors stats

``t``
    Sort process by CPU times (TIME+)

``T``
    View network I/O as combination

``u``
    Sort processes by USER

``U``
    View cumulative network I/O

``w``
    Delete finished warning log messages

``W``
    Show/hide Wifi module

``x``
    Delete finished warning and critical log messages

``z``
    Show/hide processes stats

``0``
    Enable/disable Irix/Solaris mode

    Task's CPU usage will be divided by the total number of CPUs

``1``
    Switch between global CPU and per-CPU stats

``2``
    Enable/disable left sidebar

``3``
    Enable/disable the quick look module

``4``
    Enable/disable all but quick look and load module

``5``
    Enable/disable top menu (QuickLook, CPU, MEM, SWAP and LOAD)

``/``
    Switch between process command line or command name

In the Glances client browser (accessible through the ``--browser``
command line argument):

``ENTER``
    Run the selected server

``UP``
    Up in the servers list

``DOWN``
    Down in the servers list

``q|ESC``
    Quit Glances
