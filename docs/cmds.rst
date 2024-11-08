.. _cmds:

Command Reference
=================

Command-Line Options
--------------------

.. option:: -h, --help

    show this help message and exit

.. option:: -V, --version

    show the program's version number and exit

.. option:: -d, --debug

    enable debug mode

.. option:: -C CONF_FILE, --config CONF_FILE

    path to the configuration file

.. option:: -P PLUGIN_DIRECTORY, --plugins PLUGIN_DIRECTORY

    path to a directory containing additional plugins

.. option:: --modules-list

    display modules (plugins & exports) list and exit

.. option:: --disable-plugin PLUGIN

    disable PLUGIN (comma-separated list)

.. option:: --enable-plugin PLUGIN

    enable PLUGIN (comma-separated list)

.. option:: --stdout PLUGINS_STATS

    display stats to stdout (comma-separated list of plugins/plugins.attribute)

.. option:: --export EXPORT

    enable EXPORT module (comma-separated list)

.. option:: --export-csv-file EXPORT_CSV_FILE

    file path for CSV exporter

.. option:: --export-json-file EXPORT_JSON_FILE

    file path for JSON exporter

.. option:: --disable-process

    disable process module (reduce Glances CPU consumption)

.. option:: --disable-webui

    disable the Web UI (only the RESTful API will respond)

.. option:: --light, --enable-light

    light mode for Curses UI (disable all but the top menu)

.. option:: -0, --disable-irix

    task's CPU usage will be divided by the total number of CPUs

.. option:: -1, --percpu

    start Glances in per CPU mode

.. option:: -2, --disable-left-sidebar

    disable network, disk I/O, FS and sensors modules

.. option:: -3, --disable-quicklook

    disable quick look module

.. option:: -4, --full-quicklook

    disable all but quick look and load

.. option:: -5, --disable-top

    disable top menu (QuickLook, CPU, MEM, SWAP, and LOAD)

.. option:: -6, --meangpu

    start Glances in mean GPU mode

.. option:: --enable-history

    enable the history mode

.. option:: --disable-bold

    disable bold mode in the terminal

.. option:: --disable-bg

    disable background colors in the terminal

.. option:: --enable-process-extended

    enable extended stats on top process

.. option:: -c CLIENT, --client CLIENT

    connect to a Glances server by IPv4/IPv6 address, hostname or hostname:port

.. option:: -s, --server

    run Glances in server mode

.. option:: --browser

    start TUI Central Glances Browser
    use --browser -w to start WebUI Central Glances Browser

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

    run Glances in web server mode (FastAPI lib needed)

.. option:: --cached-time CACHED_TIME

    set the server cache time [default: 1 sec]

.. option:: --open-web-browser

    try to open the Web UI in the default Web browser

.. option:: -q, --quiet

    do not display the curses interface

.. option:: -f PROCESS_FILTER, --process-filter PROCESS_FILTER

    set the process filter pattern (regular expression)

.. option:: --process-short-name

    force short name for processes name

.. option:: --hide-kernel-threads

    hide kernel threads in the process list (not available on Windows)

.. option:: -b, --byte

    display network rate in bytes per second

.. option:: --diskio-show-ramfs

    show RAM FS in the DiskIO plugin

.. option:: --diskio-iops

    show I/O per second in the DiskIO plugin

.. option:: --fahrenheit

    display temperature in Fahrenheit (default is Celsius)

.. option:: --fs-free-space

    display FS free space instead of used

.. option:: --theme-white

    optimize display colors for a white background

.. option:: --disable-check-update

    disable online Glances version check

Interactive Commands
--------------------

The following commands (key pressed) are supported while in Glances:

``ENTER``
    Set the process filter

    .. note:: On macOS please use ``CTRL-H`` to delete filter.

    The filter is a regular expression pattern:

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
    Enable/disable the Application Monitoring Process

``b``
    Switch between bit/s or Byte/s for network I/O

``B``
    View disk I/O counters per second

``c``
    Sort processes by CPU usage

``C``
    Enable/disable cloud stats

``d``
    Show/hide disk I/O stats

``D``
    Enable/disable Docker stats

``e``
    Enable/disable top extended stats

``E``
    Erase the current process filter

``f``
    Show/hide file system and folder monitoring stats

``F``
    Switch between file system used and free space

``g``
    Generate graphs for current history

``G``
    Enable/disable GPU stats

``h``
    Show/hide the help screen

``i``
    Sort processes by I/O rate

``I``
    Show/hide IP module

``+``
    Increase selected process nice level / Lower the priority (need right) - Only in standalone mode.

``-``
    Decrease selected process nice level / Higher the priority (need right) - Only in standalone mode.

``k``
    Kill selected process (need right) - Only in standalone mode.

``K``
    Show/hide TCP connections

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

``P``
    Enable/Disable ports stats

``q|ESC|CTRL-C``
    Quit the current Glances session

``Q``
    Show/hide IRQ module

``r``
    Reset history

``R``
    Show/hide RAID plugin

``s``
    Show/hide sensors stats

``S``
    Enable/disable spark lines

``t``
    Sort process by CPU times (TIME+)

``T``
    View network I/O as a combination

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

    The task's CPU usage will be divided by the total number of CPUs

``1``
    Switch between global CPU and per-CPU stats

``2``
    Enable/disable the left sidebar

``3``
    Enable/disable the quick look module

``4``
    Enable/disable all but quick look and load module

``5``
    Enable/disable the top menu (QuickLook, CPU, MEM, SWAP, and LOAD)

``6``
    Enable/disable mean GPU mode

``9``
    Switch UI theme between black and white

``/``
    Switch between process command line or command name

``F5`` or ``CTRL-R``
    Refresh user interface

``LEFT``
    Navigation left through the process sort

``RIGHT``
    Navigation right through the process sort

``UP``
    Up in the processes list

``DOWN``
    Down in the processes list

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
