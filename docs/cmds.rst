.. _cmds:

Command Reference
=================

Command-Line Options
--------------------

General
^^^^^^^

.. option:: -h, --help

    show this help message and exit

.. option:: -V, --version

    show the program's version number and exit

.. option:: -d, --debug

    enable debug-level logging

.. option:: --print-completion {bash,zsh,tcsh,fish,powershell}

    print the shell tab completion script for the Glances CLI (not available
    on Windows)

.. option:: -C <path>, --config <path>

    path to the ``glances.conf`` file to use (instead of searching
    ``~/.config/glances/glances.conf``, then ``/etc/glances/glances.conf``)

.. option:: --modules-list, --module-list

    print the plugins and exporters lists and exit

.. option:: --disable-plugin <a,b>, --disable-plugins <a,b>, --disable <a,b>

    disable plugins (comma-separated list or ``all``). If ``all`` is used,
    then you need to configure ``--enable-plugin``

.. option:: --enable-plugin <a,b>, --enable-plugins <a,b>, --enable <a,b>

    enable plugins (comma-separated list)

.. option:: -t <sec>, --time <sec>

    refresh rate in seconds (overrides ``[global] refresh``) [default: 2 sec]

.. option:: --disable-history

    disable the stats history (same as ``[global] history_size=0``)

.. option:: --stop-after <n>

    stop after n refreshes (TUI, stdout and ``--quiet`` modes; under
    ``--quiet``, n export cycles)

.. option:: --disable-config-exec

    disable shell operator interpretation (``&&``, ``|``, ``>``) in the AMP and
    on-alert action commands read from ``glances.conf`` (recommended for system
    services). The commands themselves still run: this is not a sandbox

Server (REST API and Web UI)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. option:: -s, --server, -w, --webserver

    run as a REST API server (FastAPI, ``/api/5``) and serve the Web UI on
    ``bind_address:port``. Headless: no curses TUI. Without this flag, Glances
    runs in TUI mode and does not bind any TCP socket. ``-w``/``--webserver``
    is the v4 spelling of the same mode (the v4 XML-RPC server is gone)

.. option:: -B <addr>, --bind <addr>

    bind address (overrides ``[outputs] bind_address``) [default: 127.0.0.1]

.. option:: -p <n>, --port <n>

    listening port (overrides ``[outputs] port``) [default: 61208]. With
    ``--client``: the server's port

.. option:: --disable-webui

    serve the REST API without the Web UI (requires ``--server``)

.. option:: --api-doc, --no-api-doc

    enable or disable the Swagger ``/docs`` and ReDoc ``/redoc`` pages
    (overrides ``[outputs] api_doc``)

.. option:: --enable-mcp

    mount the MCP (Model Context Protocol) endpoint (at ``/mcp``, see
    ``--mcp-path``). Requires ``--server`` and the ``mcp`` package, see
    :ref:`api_mcp`. Off by default

.. option:: --mcp-path <path>

    path the MCP endpoint is mounted at (overrides ``[outputs] mcp_path``)
    [default: /mcp]. Requires ``--server``

.. option:: --open-web-browser

    open the Web UI in the default Web browser at startup (requires
    ``--server``)

.. option:: --set-password

    generate a PBKDF2 password hash interactively and print it to stdout. Paste
    it into ``[outputs] password`` of ``glances.conf`` to protect the server.
    It does NOT modify ``glances.conf``

Client and browser
^^^^^^^^^^^^^^^^^^

.. option:: -c <server>, --client <server>

    show a remote Glances v5 server in the TUI: ``host``, ``host:port`` or an
    ``http(s)://`` URL (default port: ``--port``, else 61208)

.. option:: -u <name>, --username <name>

    with ``--client`` or ``--browser``: the server's username [default: glances]

.. option:: --password

    with ``--client``: prompt for the server's password (else ``[passwords]``
    in ``glances.conf``)

.. option:: --browser

    browse the servers of ``[serverlist]`` in the TUI and open one as with
    ``--client``. With ``--server``: serve that list on ``/api/5/serverslist``
    and on the ``/browser`` Web page

.. option:: --disable-autodiscover

    Zeroconf off: a server does not announce itself, a browser lists
    ``[serverlist]`` only

Exports
^^^^^^^

.. option:: --export <a,b>

    enable export modules (comma-separated list, e.g. ``csv,influxdb2``)

.. option:: --export-csv-file <path>

    file path for the CSV exporter [default: ./glances.csv]

.. option:: --export-csv-overwrite

    overwrite the CSV file instead of appending to it

.. option:: --export-json-file <path>

    file path for the JSON exporter [default: ./glances.json]

.. option:: --export-graph-path <folder>

    folder for the graph exporter's SVG files [default: ``[graph] path``,
    else ``~/.local/share/glances/graphs``]

.. option:: --export-process-filter EXPORT_PROCESS_FILTER

    set the export process filter (comma-separated list of regular expressions)

.. option:: -q, --quiet, --no-tui

    disable the curses TUI (for example to only run the exports)

Standard output and one-shot modes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. option:: --stdout <plugin[.key].attr,...>

    print stats to stdout, one line per stat and refresh (e.g.
    ``cpu.user,mem.percent,network,all``). No TUI

.. option:: --stdout-json <plugin,...>

    print the selected plugins' stats to stdout as one JSON object per
    refresh. No TUI

.. option:: --stdout-csv <plugin[.attr],...>

    print the selected stats to stdout as CSV: a header line, then one line
    per refresh. No TUI

.. option:: --fetch, --stdout-fetch

    print a neofetch-like summary of the machine, then exit (see :ref:`fetch`)

.. option:: --fetch-template <path>, --stdout-fetch-template <path>

    Jinja template for ``--fetch`` (requires ``--fetch``)

.. option:: --api-restful-doc

    print the REST API documentation (RST, real responses from this machine),
    then exit

.. option:: --issue

    test every plugin and print a Markdown report to paste into a bug report,
    then exit

.. option:: --memory-leak

    test for memory leaks and exit: collect for ``--stop-after`` seconds
    (default 60) to warm up, then as long again, and print the memory growth
    between the two

TUI display
^^^^^^^^^^^

.. option:: --light, --enable-light

    light mode: start with only the top menu (hides the left sidebar,
    processes, alerts, AMPs, containers and VMs)

.. option:: -0, --disable-irix

    Irix mode: show the load average as a percentage of the CPU cores

.. option:: -1, --percpu, --per-cpu

    start the TUI with the per-CPU view in quicklook

.. option:: -2, --disable-left-sidebar

    start with the left sidebar hidden (network, disk I/O, FS, sensors...)

.. option:: -3, --disable-quicklook

    start with quicklook hidden

.. option:: -4, --full-quicklook

    start the TUI with the full-width quicklook (hides the CPU, MEM... top
    blocks)

.. option:: -5, --disable-top

    start with the top menu hidden (QuickLook, CPU, MEM, SWAP and LOAD)

.. option:: -6, --meangpu

    show a single mean GPU summary instead of per-GPU lines

.. option:: --disable-process

    start with the process blocks hidden. Use ``--disable-plugin
    processcount`` to stop collecting them

.. option:: --enable-irq

    enable the IRQ plugin (same as ``--enable-plugin irq``)

.. option:: --disable-bold

    disable bold text in the curses interface

.. option:: --disable-bg

    disable background colors in the curses interface (config fallback:
    ``[outputs] disable_bg``)

.. option:: --disable-separator

    disable the separator lines in the curses interface (config fallback:
    ``[outputs] separator``)

.. option:: --disable-unicode

    disable unicode characters in the curses interface

.. option:: --disable-cursor

    disable the process-selection cursor (UP/DOWN) in the curses interface

.. option:: --arrow-keys-sort

    use the arrow keys to step the process sort, and SHIFT+arrows to scroll
    the command column (the default is the other way round)

.. option:: --strftime <format>

    strftime format for the current date (overrides ``[global]
    strftime_format``)

.. option:: --hide-public-info

    mask the last two octets of the public IP address in the TUI
    (``a.b.c.d`` -> ``a.b.*.*``)

.. option:: --fahrenheit

    display temperatures in Fahrenheit (default is Celsius)

.. option:: -b, --byte

    display network rate in bytes per second (default: bits per second)

.. option:: --diskio-show-ramfs

    show RAM disks (``ram*``) in the disk I/O plugin (hidden by default)

.. option:: --diskio-iops

    display disk I/O operations per second instead of byte rates

.. option:: --diskio-latency

    display disk I/O latency (ms per read/write operation) instead of byte
    rates

.. option:: --fs-free-space

    display filesystem free space instead of used space (config fallback:
    ``[fs] free_space``)

Processes
^^^^^^^^^

.. option:: --sort-processes {cpu_percent,memory_percent,username,cpu_times,io_counters,name,cpu_num}

    sort processes by the given key

.. option:: --programs, --program

    accumulate processes by program

.. option:: --process-short-name

    show the short process name in the command column (default)

.. option:: --process-long-name

    show the full command line in the command column

.. option:: --hide-kernel-threads

    hide kernel threads in the process list (not available on Windows)

.. option:: -f PROCESS_FILTER, --process-filter PROCESS_FILTER

    set the process filter pattern (regular expression); TUI mode only

.. option:: --process-focus PROCESS_FOCUS

    set a process list to focus on (comma-separated list of Glances
    filters); TUI mode only (config fallback: ``[processlist] focus``)

Changes from Glances v4
^^^^^^^^^^^^^^^^^^^^^^^

Removed options: ``-P``/``--plugins`` (additional plugin directory),
``--cached-time``, ``--trace-malloc``, ``--enable-process-extended``,
``--disable-check-update``, ``--sparkline``, ``--theme-white`` (use
``[outputs] theme=light``) and the SNMP options (``--snmp-community``,
``--snmp-port``, ``--snmp-version``, ``--snmp-user``, ``--snmp-auth``,
``--snmp-force``).

Changed options:

- ``-s``/``--server`` is now the same mode as ``-w``/``--webserver`` (REST
  API and Web UI); the XML-RPC server and its port 61209 are gone, and
  ``-c``/``--client`` talks to a Glances v5 REST server.
- ``-B``/``--bind`` defaults to ``127.0.0.1`` (was ``0.0.0.0``).
- ``--password`` no longer defines a server password: use ``--set-password``
  and ``[outputs] password``. It now only prompts for the server's password
  with ``--client``. ``-u``/``--username`` takes the name as a value and
  only applies to ``--client`` and ``--browser``.
- ``--api-doc`` toggles the Swagger and ReDoc pages of the server (it used
  to print the Python API documentation).
- ``--fetch-template`` requires ``--fetch``.

Interactive Commands
--------------------

The following commands (key pressed) are supported while in Glances
(press ``h`` to display them all):

``F4``
    Set the process filter

    The filter is a regular expression pattern:

    - ``gnome``: matches all processes starting with the ``gnome``
      string

    - ``.*gnome.*``: matches all processes containing the ``gnome``
      string

``ENTER``
    Show/hide the extended stats of the selected process

``a``
    Sort process list automatically

    - If CPU ``>70%``, sort processes by CPU usage

    - If MEM ``>70%``, sort processes by MEM usage

    - If CPU iowait ``>60%``, sort processes by I/O read and write

``A``
    Show/hide the Application Monitoring Process (AMPs)

``b``
    Switch between bit/s or Byte/s for network I/O

``B``
    Switch between byte/s and I/O operations per second for disk I/O

``c``
    Sort processes by CPU usage

``C``
    Show/hide cloud stats

``d``
    Show/hide disk I/O stats

``D``
    Show/hide containers stats

``E``
    Erase the current process filter

``f``
    Show/hide file system and folder monitoring stats

``F``
    Switch between file system used and free space

``g``
    Generate graphs for current history (needs ``--export graph``)

``G``
    Show/hide GPU stats

``h``
    Show/hide the help screen (scroll it with ``UP``/``DOWN``, ``j``/``k``,
    ``PAGE-UP``/``PAGE-DOWN`` and ``HOME``)

``i``
    Sort processes by I/O rate

``I``
    Show/hide IP module

``j``
    Switch between the processes (threads) and programs view

``+``
    Increase selected process nice level / Lower the priority (need right) - Not in client mode.

``-``
    Decrease selected process nice level / Higher the priority (need right) - Not in client mode.

``k``
    Kill selected process (need right, asks first) - Not in client mode.

``K``
    Show/hide TCP connections

``l``
    Show/hide alerts

``L``
    Switch between byte/s and latency for disk I/O

``m``
    Sort processes by MEM usage

``M``
    Reset the filtered processes summary min/max

``n``
    Show/hide network stats

``N``
    Show/hide current time

``o``
    Sort processes by CPU core number

``p``
    Sort processes by name

``P``
    Show/hide ports stats

``q|ESC|CTRL-C``
    Quit the current Glances session

``Q``
    Show/hide IRQ module

``r``
    Show/hide SMART stats

``R``
    Show/hide RAID plugin

``s``
    Show/hide sensors plugin

``t``
    Sort process by CPU times (TIME+)

``T``
    View network and disk I/O as a combination

``u``
    Sort processes by USER

``U``
    View cumulative network and disk I/O

``V``
    Show/hide VMS plugin

``W``
    Show/hide Wifi module

``z``
    Show/hide processes stats

``0``
    Enable/disable Irix/Solaris mode

    The load and the task's CPU usage will be divided by the total number of CPUs

``1``
    Switch between global CPU and per-CPU stats

``2``
    Show/hide the left sidebar

``3``
    Show/hide the quick look module

``4``
    Enable/disable the full-width quick look

``5``
    Show/hide the top menu (QuickLook, CPU, MEM, SWAP, and LOAD)

``6``
    Enable/disable mean GPU mode

``7``
    Show/hide NPU stats

``8``
    Show/hide MPP stats

``/``
    Switch between process command line or command name

``F5`` or ``CTRL-R``
    Refresh user interface

``SHIFT-LEFT``
    Navigation left through the process sort

``SHIFT-RIGHT``
    Navigation right through the process sort

``LEFT``
    Scroll the selected process command line left

``RIGHT``
    Scroll the selected process command line right

``UP``
    Up in the processes list

``DOWN``
    Down in the processes list

With ``--arrow-keys-sort``, ``LEFT``/``RIGHT`` and ``SHIFT-LEFT``/``SHIFT-RIGHT``
are swapped. With ``--disable-cursor``, the keys acting on the selected process
(``ENTER``, ``k``, ``+``, ``-``, ``UP``, ``DOWN``, command line scrolling) are
disabled.

In the Glances client browser (accessible through the ``--browser``
command line argument):

``ENTER``
    Run the selected server

``UP``
    Up in the servers list

``DOWN``
    Down in the servers list

``1``
    Show the servers in the configured order

``2``
    Sort the servers by status (UNKNOWN > OFFLINE > PROTECTED > UNSUPPORTED > ONLINE)

``3``
    Sort the servers by status, reversed (ONLINE first)

``q|ESC``
    Quit Glances
