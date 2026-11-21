.. _api:

Python API documentation
========================

This page describes the Glances v5 Python API. Every example below is a real
read, taken when the page was generated.

.. note::

    During the Glances 5 alphas the module is ``glances.api``. It becomes
    ``glances.api`` with Glances 5.0.0, replacing the Glances 4 API.

TL;DR
-----

.. code-block:: python

    >>> from glances import api
    >>> gl = api.GlancesAPI()
    >>> gl.cpu
    {'cpucore': 16,
     'ctx_switches': 0.0,
     'guest': 0.0,
     'idle': 92.0,
     'interrupts': 0.0,
     'iowait': 0.9,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 3.6,
     'time_since_update': 0.38942165600019507,
     'total': 8.0,
     'user': 3.6}
    >>> gl.cpu["total"]
    8.0
    >>> gl.mem["used"]
    7275937792
    >>> gl.auto_unit(gl.mem["used"])
    '6.78G'
    >>> gl.network.keys()
    ['wlp0s20f3', 'tailscale0']
    >>> gl.network["wlp0s20f3"]
    {'bytes_recv': 895.1870344143833,
     'bytes_recv_cumul': 1941526508,
     'bytes_sent': 917.4277060768525,
     'bytes_sent_cumul': 76579990,
     'bytes_speed_rate_per_sec': 0.0,
     'dropped_in': 0.0,
     'dropped_out': 0.0,
     'errors_in': 0.0,
     'errors_out': 0.0,
     'hidden': False,
     'interface_name': 'wlp0s20f3',
     'is_up': True}

On demand, or in the background
-------------------------------

By default the API collects **on demand**: reading ``gl.<plugin>`` updates
that plugin when its last update is older than ``[global] refresh`` (2 seconds
by default), and nothing runs between two reads. That suits a script.

With ``background=True`` the Glances scheduler runs in a thread: the stats stay
fresh, and the history and the alerts fill up between reads. That suits a
notebook or a long-running tool.

.. code-block:: python

    >>> with api.GlancesAPI(background=True) as gl:
    ...     time.sleep(60)
    ...     gl.cpu.history(nb=30)
    ...     gl.alerts()

In both modes the API reads ``glances.conf`` as Glances does (``config_path``
adds a file on top), never the command line of the script that uses it.
``refresh=1`` overrides ``[global] refresh``, as ``-t`` does on the command
line: the cache duration on demand, the collection cadence in the background.
``plugins=["cpu", "mem"]`` builds only those plugins, plus what they depend
on. Alerts are recorded, but the actions ``glances.conf`` configures for them
never run, and no exporter is started.

Close the API when done, or use it as a context manager: some plugins hold
background resources until then.

Plugin views
------------

``gl.<plugin>`` returns a read-only snapshot of the plugin, taken when it was
read. It is a mapping: ``[]``, ``get``, ``keys``, ``items``, ``len``, ``in``.
A collection plugin (network interfaces, file systems, processes...) is keyed
by its primary key; a scalar plugin by its field names.

* ``raw``: the payload, as ``/api/5/<plugin>`` serves it
* ``fields``: each field's description and unit
* ``limits``: the thresholds in effect
* ``levels``: the alert level of each watched field
* ``history()``: the recorded history, as ``/api/5/<plugin>/history`` serves it

Changing a view changes nothing Glances, or a later read, sees. Read
``gl.<plugin>`` again for fresh values.

Plugins list
------------

.. code-block:: python

    >>> gl.plugins()
    ['amps', 'containers', 'core', 'cpu', 'diskio', 'folders', 'fs', 'gpu', 'ip',
     'load', 'mem', 'memswap', 'network', 'now', 'percpu', 'ports', 'processcount',
     'processlist', 'programlist', 'psutilversion', 'quicklook', 'sensors',
     'system', 'uptime', 'version', 'wifi']

Glances amps
------------

.. code-block:: python

    >>> gl.amps.keys()
    ['Dropbox', 'Python', 'Conntrack', 'Nginx', 'Systemd', 'SystemV']
    >>> gl.amps['Dropbox']
    {'count': 0,
     'countmax': None,
     'countmin': 1.0,
     'name': 'Dropbox',
     'refresh': 3.0,
     'regex': True,
     'result': None,
     'result_float': None,
     'timer': 0.43931031227111816}

Amps fields:

* ``name``: AMP name. (unit is *string*)
* ``result``: AMP result (a string, possibly multi-line). (unit is *string*)
* ``result_float``: Numeric value of \`result\` when it parses as a number, else None. (unit is *number*)
* ``refresh``: AMP refresh interval. (unit is *second*)
* ``timer``: Time until next refresh. (unit is *second*)
* ``count``: Number of matching processes. (unit is *number*)
* ``countmin``: Minimum number of matching processes. (unit is *number*)
* ``countmax``: Maximum number of matching processes. (unit is *number*)
* ``regex``: True when a regex is configured for this AMP. (unit is *bool*)

Glances containers
------------------

.. code-block:: python

    >>> gl.containers.keys()
    []

Containers fields:

* ``name``: Container name. (unit is *string*)
* ``id``: Container ID. (unit is *string*)
* ``image``: Container image. (unit is *string*)
* ``status``: Container status. (unit is *string*)
* ``created``: Container creation date. (unit is *string*)
* ``command``: Container command. (unit is *string*)
* ``cpu_percent``: Container CPU consumption. (unit is *percent*)
* ``cpu_limit``: Container CPU limit. (unit is *number*)
* ``memory_usage``: Container memory usage (v4 export value: usage − cache when present). Feeds export/REST. (unit is *byte*)
* ``memory_usage_no_cache``: Container memory usage minus inactive\_file. TUI display value. (unit is *byte*)
* ``memory_inactive_file``: Container memory inactive file. (unit is *byte*)
* ``memory_limit``: Container memory limit. (unit is *byte*)
* ``memory_percent``: Container memory usage as a percentage of its limit. (unit is *percent*)
* ``io_rx``: Container IO bytes read rate. (unit is *bytepersecond*)
* ``io_wx``: Container IO bytes write rate. (unit is *bytepersecond*)
* ``network_rx``: Container network RX bitrate. (unit is *bitpersecond*)
* ``network_tx``: Container network TX bitrate. (unit is *bitpersecond*)
* ``ports``: Container ports. (unit is *string*)
* ``started_at``: Container start time (Unix timestamp, seconds). None when the container is not active. (unit is *number*)
* ``engine``: Container engine (Docker, Podman, LXD). (unit is *string*)
* ``engine_url``: Container engine base URL / endpoint (creds are hidden). (unit is *string*)
* ``pod_name``: Pod name (Podman only). (unit is *string*)
* ``pod_id``: Pod ID (Podman only). (unit is *string*)

Glances core
------------

.. code-block:: python

    >>> gl.core
    {'log': 16, 'phys': 10, 'time_since_update': 0.3948011560005398}

Core fields:

* ``phys``: Number of physical cores (hyper-thread CPUs excluded). (unit is *number*)
* ``log``: Number of logical CPU cores (physical cores × threads per core). (unit is *number*)

Glances cpu
-----------

.. code-block:: python

    >>> gl.cpu
    {'cpucore': 16,
     'ctx_switches': 0.0,
     'guest': 0.0,
     'idle': 92.0,
     'interrupts': 0.0,
     'iowait': 0.9,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 3.6,
     'time_since_update': 0.38942165600019507,
     'total': 8.0,
     'user': 3.6}

Cpu fields:

* ``total``: Sum of all CPU percentages (except idle). (unit is *percent*)
* ``system``: Percent time spent in kernel space. System CPU time is the time spent running code in the operating system kernel. (unit is *percent*)
* ``user``: Percent time spent in user space. User CPU time is the time spent on the processor running the program's code (or code in libraries). (unit is *percent*)
* ``iowait``: (Linux) Percent time spent by the CPU waiting for I/O operations to complete. (unit is *percent*)
* ``dpc``: (Windows) Percent time spent servicing deferred procedure calls (DPCs). (unit is *percent*)
* ``idle``: Percent of CPU not used by any program. Every program or task that runs occupies a certain amount of processing time on the CPU; when the CPU has completed all tasks it is idle. (unit is *percent*)
* ``irq``: (Linux and BSD) Percent time spent servicing hardware and software interrupts. (unit is *percent*)
* ``nice``: (UNIX) Percent time occupied by user-level processes with a positive nice value (processes that have been niced down). (unit is *percent*)
* ``steal``: (Linux) Percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor. (unit is *percent*)
* ``guest``: (Linux) Time spent running a virtual CPU for guest operating systems under the control of the Linux kernel. (unit is *percent*)
* ``ctx_switches``: Number of context switches (voluntary + involuntary) per second. A context switch is the procedure a CPU follows to change from one task to another while ensuring the tasks do not conflict. (unit is *number*)
* ``interrupts``: Number of interrupts per second. (unit is *number*)
* ``soft_interrupts``: Number of software interrupts per second. Always 0 on Windows and SunOS. (unit is *number*)
* ``syscalls``: Number of system calls per second. Always 0 on Linux. (unit is *number*)
* ``cpucore``: Total number of logical CPU cores. (unit is *number*)

Cpu limits:

.. code-block:: python

    >>> gl.cpu.limits
    {'ctx_switches': {'careful': 25000.0, 'critical': 50000.0, 'warning': 37500.0},
     'dpc': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'iowait': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'steal': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'system': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'total': {'careful': 65.0, 'critical': 85.0, 'warning': 75.0},
     'user': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances diskio
--------------

.. code-block:: python

    >>> gl.diskio.keys()
    ['nvme0n1', 'nvme0n1p1', 'nvme0n1p2', 'nvme0n1p3', 'dm-0', 'dm-1']
    >>> gl.diskio['nvme0n1']
    {'disk_name': 'nvme0n1',
     'hidden': False,
     'read_bytes': 41592.543561726714,
     'read_bytes_cumul': 31604888576,
     'read_count': 2.5386073951249215,
     'read_count_cumul': 2320977,
     'read_latency': 0,
     'read_time': 0.0,
     'write_bytes': 863045.2789058293,
     'write_bytes_cumul': 27843253248,
     'write_count': 190.39555463436912,
     'write_count_cumul': 3260379,
     'write_latency': 0,
     'write_time': 86.31265143424733}

Diskio fields:

* ``disk_name``: Disk name (e.g. sda, nvme0n1). (unit is *string*)
* ``read_count``: Read operations per second (rate of psutil read\_count counter). (unit is *number*)
* ``write_count``: Write operations per second (rate of psutil write\_count counter). (unit is *number*)
* ``read_time``: Time spent reading, in milliseconds per second (rate of psutil read\_time counter). (unit is *number*)
* ``write_time``: Time spent writing, in milliseconds per second (rate of psutil write\_time counter). (unit is *number*)
* ``read_latency``: Mean time spent reading per operation, in milliseconds. (unit is *number*)
* ``write_latency``: Mean time spent writing per operation, in milliseconds. (unit is *number*)
* ``read_bytes_cumul``: Bytes read since boot (cumulative counter). (unit is *bytes*)
* ``write_bytes_cumul``: Bytes written since boot (cumulative counter). (unit is *bytes*)
* ``read_count_cumul``: Read operations since boot (cumulative counter). (unit is *number*)
* ``write_count_cumul``: Write operations since boot (cumulative counter). (unit is *number*)
* ``read_bytes``: Bytes read per second (rate of psutil read\_bytes counter). (unit is *bytespers*)
* ``write_bytes``: Bytes written per second (rate of psutil write\_bytes counter). (unit is *bytespers*)

Glances folders
---------------

.. code-block:: python

    >>> gl.folders.keys()
    []

Folders fields:

* ``path``: Absolute path. (unit is *string*)
* ``size``: Folder size in bytes. (unit is *bytes*)
* ``refresh``: Refresh interval in seconds. (unit is *seconds*)
* ``errno``: Return code when retrieving folder size (0 is no error). (unit is *number*)
* ``careful``: Careful threshold in MB. (unit is *megabyte*)
* ``warning``: Warning threshold in MB. (unit is *megabyte*)
* ``critical``: Critical threshold in MB. (unit is *megabyte*)

Glances fs
----------

.. code-block:: python

    >>> gl.fs.keys()
    ['/']
    >>> gl.fs['/']
    {'device_name': '/dev/mapper/ubuntu--vg-ubuntu--lv',
     'free': 437069901824,
     'fs_type': 'ext4',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 54.1,
     'size': 1003736440832,
     'used': 515604033536}

Fs fields:

* ``mnt_point``: Mount point. (unit is *string*)
* ``device_name``: Device name backing the filesystem (e.g. /dev/sda1). (unit is *string*)
* ``fs_type``: File system type (e.g. ext4, xfs, btrfs). (unit is *string*)
* ``options``: Mount options string (comma-separated). (unit is *string*)
* ``size``: Total size of the filesystem in bytes. (unit is *bytes*)
* ``used``: Used size in bytes. (unit is *bytes*)
* ``free``: Free size in bytes. (unit is *bytes*)
* ``percent``: Filesystem usage as a percentage of total size. (unit is *percent*)

Fs limits:

.. code-block:: python

    >>> gl.fs.limits
    {'percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances gpu
-----------

.. code-block:: python

    >>> gl.gpu.keys()
    ['intel0', 'intel1']
    >>> gl.gpu['intel0']
    {'fan_speed': None,
     'gpu_id': 'intel0',
     'mem': None,
     'name': 'UHD Graphics',
     'proc': 0,
     'temperature': None}

Gpu fields:

* ``gpu_id``: GPU identifier (e.g. nvidia0). (unit is *string*)
* ``name``: GPU product name. (unit is *string*)
* ``proc``: GPU processor consumption. (unit is *percent*)
* ``mem``: GPU memory consumption. (unit is *percent*)
* ``temperature``: GPU temperature. (unit is *celsius*)
* ``fan_speed``: GPU fan speed. (unit is *percent*)

Gpu limits:

.. code-block:: python

    >>> gl.gpu.limits
    {'mem': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'proc': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'temperature': {'careful': 60.0, 'critical': 80.0, 'warning': 70.0}}

Glances ip
----------

.. code-block:: python

    >>> gl.ip
    {'address': '192.168.1.26',
     'mask': '255.255.255.0',
     'mask_cidr': 24,
     'time_since_update': 0.3707135529984953}

Ip fields:

* ``address``: Private IP address. (unit is *string*)
* ``mask``: Private IP mask. (unit is *string*)
* ``mask_cidr``: Private IP mask in CIDR format. (unit is *number*)
* ``gateway``: Private IP gateway. (unit is *string*)
* ``public_address``: Public IP address. (unit is *string*)
* ``public_info_human``: Public IP information (human readable). (unit is *string*)

Glances load
------------

.. code-block:: python

    >>> gl.load
    {'cpucore': 16,
     'min1': 1.822265625,
     'min15': 1.0771484375,
     'min5': 1.20263671875,
     'time_since_update': 0.37102851000054216}

Load fields:

* ``min1``: Average number of processes waiting in the run-queue plus those currently executing, over 1 minute. (unit is *float*)
* ``min5``: Average number of processes waiting in the run-queue plus those currently executing, over 5 minutes. (unit is *float*)
* ``min15``: Average number of processes waiting in the run-queue plus those currently executing, over 15 minutes. (unit is *float*)
* ``cpucore``: Total number of logical CPU cores. (unit is *number*)

Load limits:

.. code-block:: python

    >>> gl.load.limits
    {'min15': {'careful': 0.7, 'critical': 5.0, 'warning': 1.0},
     'min5': {'careful': 0.7, 'critical': 5.0, 'warning': 1.0}}

Glances mem
-----------

.. code-block:: python

    >>> gl.mem
    {'active': 4682395648,
     'available': 8604135424,
     'buffers': 198803456,
     'cached': 8411090688,
     'free': 1860702208,
     'inactive': 7035326464,
     'percent': 45.8,
     'shared': 1683193856,
     'slab': 806309888,
     'time_since_update': 0.3623706359994685,
     'total': 15880073216,
     'used': 7275937792}

Mem fields:

* ``total``: Total physical memory available. (unit is *bytes*)
* ``available``: Actual amount of available memory that can be given instantly to processes that request more memory; calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux). Suitable for monitoring actual memory usage in a cross-platform fashion. (unit is *bytes*)
* ``percent``: Percentage usage calculated as (total - available) / total \* 100. (unit is *percent*)
* ``used``: Memory used, calculated differently depending on the platform and designed for informational purposes only. (unit is *bytes*)
* ``free``: Memory not being used at all (zeroed) that is readily available; note that this does not reflect the actual memory available — use \`available\` instead. (unit is *bytes*)
* ``active``: (UNIX) Memory currently in use or very recently used, resident in RAM. (unit is *bytes*)
* ``inactive``: (UNIX) Memory that is marked as not used. (unit is *bytes*)
* ``buffers``: (Linux, BSD) Cache for items like filesystem metadata. (unit is *bytes*)
* ``cached``: (Linux, BSD) Cache for various things (including ZFS cache). (unit is *bytes*)
* ``shared``: (BSD) Memory that may be simultaneously accessed by multiple processes. (unit is *bytes*)
* ``wired``: (BSD, macOS) Memory marked to always stay in RAM — never paged to disk. (unit is *bytes*)
* ``slab``: (Linux) In-kernel data structures cache. (unit is *bytes*)

Mem limits:

.. code-block:: python

    >>> gl.mem.limits
    {'percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances memswap
---------------

.. code-block:: python

    >>> gl.memswap
    {'free': 2164785152,
     'percent': 49.6,
     'sin': 0.0,
     'sout': 0.0,
     'time_since_update': 0.3712467010009277,
     'total': 4294963200,
     'used': 2130178048}

Memswap fields:

* ``total``: Total swap memory. (unit is *bytes*)
* ``used``: Used swap memory. (unit is *bytes*)
* ``free``: Free swap memory. (unit is *bytes*)
* ``percent``: Used swap memory as a percentage of total. (unit is *percent*)
* ``sin``: Bytes the system has swapped in from disk (per second — v4 reports the cumulative counter; v5 converts it to a rate). (unit is *bytespers*)
* ``sout``: Bytes the system has swapped out to disk (per second — v4 reports the cumulative counter; v5 converts it to a rate). (unit is *bytespers*)

Memswap limits:

.. code-block:: python

    >>> gl.memswap.limits
    {'percent': {'careful': 60.0, 'critical': 95.0, 'warning': 80.0}}

Glances network
---------------

.. code-block:: python

    >>> gl.network.keys()
    ['wlp0s20f3', 'tailscale0']
    >>> gl.network['wlp0s20f3']
    {'bytes_recv': 895.1870344143833,
     'bytes_recv_cumul': 1941526508,
     'bytes_sent': 917.4277060768525,
     'bytes_sent_cumul': 76579990,
     'bytes_speed_rate_per_sec': 0.0,
     'dropped_in': 0.0,
     'dropped_out': 0.0,
     'errors_in': 0.0,
     'errors_out': 0.0,
     'hidden': False,
     'interface_name': 'wlp0s20f3',
     'is_up': True}

Network fields:

* ``interface_name``: Network interface name. (unit is *string*)
* ``bytes_recv``: Bytes received per second. (unit is *bytespers*)
* ``bytes_sent``: Bytes sent per second. (unit is *bytespers*)
* ``bytes_recv_cumul``: Bytes received since the interface came up (cumulative counter). (unit is *bytes*)
* ``bytes_sent_cumul``: Bytes sent since the interface came up (cumulative counter). (unit is *bytes*)
* ``errors_in``: Receive errors per second. (unit is *number*)
* ``errors_out``: Send errors per second. (unit is *number*)
* ``dropped_in``: Receive packets dropped per second. (unit is *number*)
* ``dropped_out``: Send packets dropped per second. (unit is *number*)
* ``bytes_speed_rate_per_sec``: Per-direction bandwidth capacity in bytes/s. Computed from net\_if\_stats().speed (Mbit/s), each direction getting the full link speed: speed\_mbits \* 1e6 / 8. Returns 0 when the OS does not report a link speed (loopback, virtual interfaces) — in which case threshold normalisation is skipped for bytes\_recv / bytes\_sent. (unit is *bytespers*)
* ``is_up``: Whether the interface is up. (unit is *bool*)

Network limits:

.. code-block:: python

    >>> gl.network.limits
    {'bytes_recv': {'careful': 0.7, 'critical': 0.9, 'warning': 0.8},
     'bytes_sent': {'careful': 0.7, 'critical': 0.9, 'warning': 0.8},
     'errors_in': {'careful': 1.0, 'critical': 20.0, 'warning': 5.0},
     'errors_out': {'careful': 1.0, 'critical': 20.0, 'warning': 5.0}}

Glances now
-----------

.. code-block:: python

    >>> gl.now
    {'custom': '2026-11-21 11:03:43 CET',
     'iso': '2026-11-21T11:03:43+01:00',
     'time_since_update': 0.3705626940009097}

Now fields:

* ``custom``: Current date in custom format. (unit is *string*)
* ``iso``: Current date in ISO 8601 format. (unit is *string*)

Glances percpu
--------------

.. code-block:: python

    >>> gl.percpu.keys()
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    >>> gl.percpu[0]
    {'cpu_number': 0,
     'guest': 0.0,
     'guest_nice': 0.0,
     'idle': 100.0,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 0.0,
     'total': 0.0,
     'user': 0.0}

Percpu fields:

* ``cpu_number``: CPU core number (zero-based logical core index). (unit is *number*)
* ``total``: Sum of CPU percentages (except idle) for this core. (unit is *percent*)
* ``system``: Percent time spent in kernel space on this core. System CPU time is the time spent running code in the operating system kernel. (unit is *percent*)
* ``user``: Percent time spent in user space on this core. User CPU time is the time spent on the processor running the program's code. (unit is *percent*)
* ``idle``: Percent time this core was idle. (unit is *percent*)
* ``iowait``: (Linux) Percent time this core spent waiting for I/O operations to complete. (unit is *percent*)
* ``irq``: (Linux and BSD) Percent time this core spent servicing hardware/software interrupts. (unit is *percent*)
* ``softirq``: (Linux) Percent time this core spent handling software interrupts. (unit is *percent*)
* ``nice``: (UNIX) Percent time this core spent on niced user-level processes. (unit is *percent*)
* ``steal``: (Linux) Percentage of time this virtual CPU waited for a real CPU while the hypervisor was servicing another virtual processor. (unit is *percent*)
* ``guest``: (Linux) Percent of time this core spent running a virtual CPU for guest OSes. (unit is *percent*)
* ``guest_nice``: (Linux) Percent of time this core spent running a niced guest virtual CPU. (unit is *percent*)
* ``dpc``: (Windows) Percent of time this core spent handling deferred procedure calls. (unit is *percent*)
* ``interrupt``: (Windows) Percent of time this core spent handling software interrupts. (unit is *percent*)
* ``max_cpu_display``: Maximum number of CPU cores displayed before the mean row ([percpu] max\_cpu\_display). (unit is *number*)
* ``thresholds``: Effective [percpu] thresholds per column, used to colour the CPU\* mean row. (unit is *string*)
* ``stat_fields``: OS-specific stat columns, in the order the TUI renders them (define\_headers\_from\_os). (unit is *string*)

Percpu limits:

.. code-block:: python

    >>> gl.percpu.limits
    {'system': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'user': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances ports
-------------

.. code-block:: python

    >>> gl.ports.keys()
    ['port_0']
    >>> gl.ports['port_0']
    {'description': 'DefaultGateway',
     'host': '192.168.1.1',
     'indice': 'port_0',
     'port': 0,
     'refresh': 30,
     'rtt_warning': None,
     'status': 0.005188,
     'timeout': 3}

Ports fields:

* ``indice``: Unique indice for the host/port. (unit is *string*)
* ``description``: Human readable description for the host/port/URL. (unit is *string*)
* ``host``: Measurement is done on this host (or IP address). (unit is *string*)
* ``port``: Measurement is done on this port (0 for ICMP). (unit is *number*)
* ``url``: Measurement is done on this URL (HEAD request). (unit is *string*)
* ``status``: Measurement result: None while scanning, 0/False on timeout, the RTT in seconds for a port, or the HTTP status code for a URL. (unit is *second*)
* ``elapsed``: HTTP response time (URL items only). (unit is *second*)
* ``rtt_warning``: Warning threshold (in seconds) for the measurement. (unit is *second*)
* ``timeout``: Timeout (in seconds) for the measurement. (unit is *second*)
* ``refresh``: Refresh time (in seconds) for this host/port. (unit is *second*)

Glances processcount
--------------------

.. code-block:: python

    >>> gl.processcount
    {'auto_sort': True,
     'pid_max': 4194304,
     'running': 0,
     'sleeping': 316,
     'sort_key': 'cpu_percent',
     'thread': 1786,
     'time_since_update': 0.3689254939999955,
     'total': 475}

Processcount fields:

* ``total``: Total number of processes. (unit is *number*)
* ``running``: Number of running processes. (unit is *number*)
* ``sleeping``: Number of sleeping processes. (unit is *number*)
* ``thread``: Total number of threads across all processes. (unit is *number*)
* ``pid_max``: Maximum PID value supported by the kernel (Linux) or None. (unit is *number*)
* ``sort_key``: Key the processes, containers and VMs are sorted by. (unit is *string*)
* ``auto_sort``: True when the sort key is chosen automatically (from the alerts). (unit is *bool*)

Glances processlist
-------------------

.. code-block:: python

    >>> gl.processlist.keys()
    [153553, 130, 90955, 145466, 92572, 91819, 92403, 152837, 92184, 131758, 132865,
     3445, 7925, 92187, 91213, 8489, 132844, 144762, 152934, 152886, 153308, 10355,
     131793, 4063, 153550, 3125, 91222, 8456, 91199, 132957, 103497, 3448, 3461,
     4069, 7351, 152377, 8247, 8482, 13733, 7333, 631, 9567, 8256, 1, 8348, 7278,
     9117, 92177, 143065, 143339, 3110, 143050, 7339, 3238, 9108, 8448, 3146,
     132600, 143283, 50475, 676, 4076, 9424, 3482, 9180, 8561, 3092, 3404, 7337,
     97777, 91196, 102518, 57083, 8198, 9162, 131414, 8195, 3242, 8149, 3138, 7332,
     8265, 8201, 8217, 8163, 8559, 7837, 3366, 7457, 700, 3101, 4184, 3091, 3451,
     8414, 7812, 8507, 671, 10838, 9153, 8150, 7847, 7045, 8184, 3367, 153546, 670,
     4031, 7844, 8113, 3142, 8547, 8122, 9090, 8291, 8188, 152375, 102481, 8356,
     3130, 4079, 153549, 3132, 102354, 3230, 8120, 4683, 3806, 8624, 8603, 7338,
     3118, 8206, 8377, 152376, 8236, 8618, 3090, 3433, 8386, 8141, 8224, 8346, 8187,
     8231, 8243, 8196, 8189, 105475, 4408, 8211, 8612, 7461, 91090, 8213, 7500,
     7520, 9858, 8344, 3805, 3155, 4075, 3959, 3151, 3096, 7815, 2908, 4411, 7342,
     7814, 4080, 4074, 7468, 4084, 2924, 3860, 7307, 3218, 9735, 3442, 3435, 2, 3,
     4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28,
     29, 30, 31, 33, 34, 35, 36, 37, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49, 51, 52,
     53, 54, 55, 57, 58, 59, 60, 61, 63, 64, 65, 66, 67, 69, 70, 71, 72, 73, 75, 76,
     77, 78, 79, 81, 82, 83, 84, 85, 87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 99,
     100, 101, 102, 103, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 117,
     119, 121, 122, 123, 124, 125, 126, 127, 133, 135, 136, 137, 138, 139, 140, 143,
     144, 146, 147, 149, 150, 151, 152, 155, 157, 159, 160, 161, 179, 260, 262, 263,
     264, 265, 266, 312, 313, 314, 475, 476, 477, 478, 486, 488, 514, 515, 518, 519,
     522, 529, 530, 532, 550, 553, 554, 586, 696, 703, 704, 705, 724, 753, 833, 960,
     992, 996, 998, 1055, 1056, 1057, 1058, 1148, 1149, 1150, 1152, 1153, 1154,
     1156, 1157, 1158, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1167, 1168, 1203,
     1602, 1611, 1636, 1747, 1885, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208,
     2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 4142, 4237,
     4238, 4239, 4240, 4241, 4242, 4243, 4244, 4245, 4246, 4247, 4248, 4249, 4250,
     4251, 4252, 5196, 12784, 50252, 62682, 78015, 78223, 79639, 95118, 95653,
     95660, 96147, 96552, 99656, 99674, 102096, 102099, 102103, 102109, 102112,
     102116, 104492, 104679, 107586, 107630, 108343, 108837, 109009, 109043, 118399,
     124620, 125409, 126474, 126475, 126544, 126672, 126675, 128056, 128057, 128119,
     128856, 129220, 129221, 129295, 129297, 133866, 135792, 135793, 135794, 142583,
     142633, 142948, 142951, 143062, 143571, 143819, 143823, 144440, 144674, 146576,
     146587, 148538, 149148, 151968, 152082, 153290]
    >>> gl.processlist[153553]
    {'cmdline': ['/home/nicolargo/dev/glances/.venv/bin/python',
                 '-m',
                 'glances.api_doc',
                 '-C',
                 'conf/glances.conf'],
     'cpu_num': 4,
     'cpu_percent': 70.5,
     'cpu_times': {'children_system': 0.01,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.25,
                   'user': 0.33},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [16384, 303104, 16384, 303104, 1],
     'key': 'pid',
     'memory_info': {'data': 126226432,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 91443200,
                     'shared': 28073984,
                     'text': 31211520,
                     'vms': 670072832},
     'memory_percent': 0.5758361359937952,
     'name': 'python',
     'nice': 0,
     'num_threads': 7,
     'pid': 153553,
     'status': 'S',
     'time_since_update': 0.3700144290924072,
     'username': 'nicolargo'}

Processlist fields:

* ``pid``: Process identifier (PID). (unit is *number*)
* ``name``: Process name. (unit is *string*)
* ``username``: Process owner (user name). (unit is *string*)
* ``status``: Process status (single letter — S sleeping, R running, etc.). (unit is *string*)
* ``nice``: Process nice value. (unit is *number*)
* ``num_threads``: Number of threads spawned by the process. (unit is *number*)
* ``cpu_percent``: Process CPU consumption (can exceed 100% on multi-threaded workloads spread across cores). (unit is *percent*)
* ``memory_percent``: Process resident memory consumption as a percentage of total RAM. (unit is *percent*)
* ``cmdline``: Command line of the process (list of argv tokens). (unit is *list*)
* ``cpu_num``: CPU core number where the process is currently running. (unit is *number*)
* ``memory_info``: Process memory information (psutil pmem namedtuple). (unit is *byte*)
* ``cpu_times``: Process CPU times (psutil pcputimes namedtuple). (unit is *second*)
* ``io_counters``: Process I/O counters (list [read\_bytes, write\_bytes, ..., io\_tag]). (unit is *byte*)
* ``gids``: Process group IDs (psutil pgids namedtuple). (unit is *number*)
* ``time_since_update``: Wall-clock interval since the previous engine refresh (seconds). (unit is *second*)
* ``key``: Name of the primary key field (always \`\`pid\`\`). (unit is *string*)
* ``cpucore``: Number of logical CPU cores (divisor of the Irix-mode CPU%). (unit is *number*)

Processlist limits:

.. code-block:: python

    >>> gl.processlist.limits
    {'_categorical': {'nice': {'warning': ['-1',
                                           '-10',
                                           '-11',
                                           '-12',
                                           '-13',
                                           '-14',
                                           '-15',
                                           '-16',
                                           '-17',
                                           '-18',
                                           '-19',
                                           '-2',
                                           '-20',
                                           '-3',
                                           '-4',
                                           '-5',
                                           '-6',
                                           '-7',
                                           '-8',
                                           '-9',
                                           '1',
                                           '10',
                                           '11',
                                           '12',
                                           '13',
                                           '14',
                                           '15',
                                           '16',
                                           '17',
                                           '18',
                                           '19',
                                           '2',
                                           '3',
                                           '4',
                                           '5',
                                           '6',
                                           '7',
                                           '8',
                                           '9']},
                      'status': {'critical': ['D', 'Z'],
                                 'ok': ['I', 'P', 'R', 'W']}},
     'cpu_percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'memory_percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances programlist
-------------------

.. code-block:: python

    >>> gl.programlist.keys()
    ['python', 'irq/9-acpi', 'firefox', 'kworker/6:0-mm_percpu_wq',
     'Isolated Web Co', 'WebExtensions', 'zed-editor', 'claude', 'multipassd',
     'gnome-shell', 'Privileged Cont', 'dropbox', 'claude-agent-acp',
     'Isolated Servic', 'Web Content', 'terminator', 'dockerd', 'uv', 'snapd',
     'RDD Process', 'localsearch-3', 'Socket Process', 'python3', 'gjs',
     'tailscaled', 'containerd', 'ollama', 'pipewire-pulse', 'glycin-svg',
     'update-notifier', 'evolution-calendar-factory', 'snap', 'pipewire',
     'systemd-journald', 'fwupd', 'evolution-alarm-notify', 'systemd',
     'ibus-extension-gtk3', 'xdg-desktop-portal-gnome', 'Utility Process',
     'sd_espeak-ng', 'polkitd', 'speech-dispatcher', 'wireplumber',
     'NetworkManager', 'xdg-desktop-portal', 'snap-store', 'udisksd', 'bash',
     'sd_dummy', 'dart:firmware-n', 'systemd-udevd', 'libvirtd',
     'xdg-desktop-portal-gtk', 'colord', 'ibus-x11', 'gvfs-udisks2-volume-monitor',
     'dbus-daemon', 'upowerd', 'gnome-keyring-daemon', 'forkserver', 'cups-browsed',
     'gvfsd-http', 'gsd-media-keys', 'mutter-x11-frames', 'gsd-housekeeping',
     'wpa_supplicant', 'evolution-source-registry', 'systemd-logind',
     'gsd-disk-utility-notify', 'gsd-power', 'gsd-sharing',
     'evolution-addressbook-factory', 'gvfsd', 'ModemManager',
     'xdg-document-portal', 'systemd-resolved', 'iio-sensor-proxy', 'gdm3',
     'bluetoothd', 'unattended-upgr', 'gvfsd-metadata', 'gcr-ssh-agent', 'Xwayland',
     'systemd-timesyncd', 'ssh-agent', 'gsd-xsettings', 'dconf-service',
     'gnome-session-service', 'gdm-session-worker', 'ibus-daemon', 'boltd', 'make',
     'systemd-oomd', 'thermald', 'gvfsd-fuse', 'at-spi-bus-launcher',
     'systemd-machined', 'ibus-engine-simple', 'at-spi2-registryd', 'gvfsd-trash',
     'goa-daemon', 'gsd-color', 'bwrap', 'cupsd', 'ibus-portal', 'accounts-daemon',
     'snmpd', 'sh', 'switcheroo-control', 'zed', 'rsyslogd', 'rtkit-daemon',
     'cups-proxyd', 'gvfs-mtp-volume-monitor', 'gvfs-gphoto2-volume-monitor',
     'mpris-proxy', 'smartd', 'gsd-print-notifications', 'gsd-usb-protection',
     'gvfs-afc-volume-monitor', 'avahi-daemon', 'goa-identity-service',
     'gnome-shell-calendar-server', 'gsd-smartcard', 'gsd-printer',
     'gsd-a11y-settings', 'gsd-sound', 'gsd-wwan', 'gsd-keyboard', 'gsd-datetime',
     'sleep', 'dnsmasq', 'gsd-rfkill', 'gvfs-goa-volume-monitor',
     'xdg-permission-store', 'crashhelper', 'gsd-screensaver-proxy',
     'gdm-wayland-session', 'gnome-session-init-worker',
     'snapd-desktop-integration', 'ibus-memconf', 'virtlogd', 'cron', 'virtlockd',
     'fsidd', 'rpcbind', 'gnome-session-ctl', 'rpc.mountd', 'rpc.idmapd',
     'fusermount3', 'rpc.statd', 'nfsdcld', 'run-cups-browse', '(sd-pam)',
     'user-session-helper', 'run-cupsd', 'kthreadd', 'pool_workqueue_release',
     'kworker/R-rcu_gp', 'kworker/R-sync_wq', 'kworker/R-kvfree_rcu_reclaim',
     'kworker/R-slub_flushwq', 'kworker/R-netns', 'kworker/0:0H-kblockd',
     'kworker/R-mm_percpu_wq', 'ksoftirqd/0', 'rcu_preempt',
     'rcu_exp_par_gp_kthread_worker/0', 'rcu_exp_gp_kthread_worker', 'migration/0',
     'kprobe-optimizer', 'idle_inject/0', 'cpuhp/0', 'cpuhp/2', 'idle_inject/2',
     'migration/2', 'ksoftirqd/2', 'kworker/2:0H-kblockd', 'cpuhp/4',
     'idle_inject/4', 'migration/4', 'ksoftirqd/4', 'kworker/4:0H-kblockd',
     'cpuhp/6', 'idle_inject/6', 'migration/6', 'ksoftirqd/6',
     'kworker/6:0H-kblockd', 'cpuhp/8', 'idle_inject/8', 'migration/8',
     'ksoftirqd/8', 'kworker/8:0H-kblockd', 'cpuhp/10', 'idle_inject/10',
     'migration/10', 'ksoftirqd/10', 'kworker/10:0H-kblockd', 'cpuhp/12',
     'idle_inject/12', 'migration/12', 'ksoftirqd/12', 'kworker/12:0H-kblockd',
     'cpuhp/13', 'idle_inject/13', 'migration/13', 'ksoftirqd/13',
     'kworker/13:0H-kblockd', 'cpuhp/14', 'idle_inject/14', 'migration/14',
     'ksoftirqd/14', 'kworker/14:0H-kblockd', 'cpuhp/15', 'idle_inject/15',
     'migration/15', 'ksoftirqd/15', 'kworker/15:0H-kblockd', 'cpuhp/1',
     'idle_inject/1', 'migration/1', 'ksoftirqd/1', 'kworker/1:0H-kblockd',
     'cpuhp/3', 'idle_inject/3', 'migration/3', 'ksoftirqd/3',
     'kworker/3:0H-kblockd', 'cpuhp/5', 'idle_inject/5', 'migration/5',
     'ksoftirqd/5', 'kworker/5:0H-kblockd', 'cpuhp/7', 'idle_inject/7',
     'migration/7', 'ksoftirqd/7', 'kworker/7:0H-kblockd', 'cpuhp/9',
     'idle_inject/9', 'migration/9', 'ksoftirqd/9', 'kworker/9:0H-kblockd',
     'cpuhp/11', 'idle_inject/11', 'migration/11', 'ksoftirqd/11',
     'kworker/11:0H-kblockd', 'kdevtmpfs', 'kworker/R-inet_frag_wq',
     'rcu_tasks_kthread', 'rcu_tasks_rude_kthread', 'kauditd', 'khungtaskd',
     'oom_reaper', 'kworker/R-writeback', 'kcompactd0', 'ksmd', 'khugepaged',
     'kworker/R-kblockd', 'kworker/R-blkcg_punt_bio', 'kworker/R-kintegrityd',
     'kworker/R-tpm_dev_wq', 'kworker/R-ata_sff', 'kworker/R-md_bitmap',
     'kworker/R-md_llbitmap_io', 'kworker/R-md_llbitmap_unplug',
     'kworker/R-edac-poller', 'kworker/R-devfreq_wq', 'watchdogd',
     'kworker/R-quota_events_unbound', 'kswapd0', 'ecryptfs-kthread',
     'kworker/R-kthrotld', 'irq/123-pciehp', 'irq/124-pciehp',
     'kworker/R-acpi_thermal_pm', 'hwrng', 'kworker/R-hfi-updates', 'kworker/R-mld',
     'kworker/R-ipv6_addrconf', 'kworker/R-kstrp', 'kworker/R-charger_manager',
     'irq/178-VEN_04F3:00', 'spi0', 'kworker/R-nvme-wq', 'kworker/R-nvme-reset-wq',
     'kworker/R-nvme-delete-wq', 'kworker/R-nvme-auth-wq',
     'kworker/R-USBC000:00-con1', 'kworker/R-USBC000:00-con2',
     'kworker/R-USBC000:00-con3', 'kworker/R-kdmflush/252:0',
     'kworker/R-kcryptd_io-252:0-1', 'kworker/R-kcryptd-252:0-1',
     'dmcrypt_write/252:0', 'kworker/2:1H-kblockd', 'kworker/R-kdmflush/252:1',
     'kworker/0:1H-i915_cleanup', 'kworker/12:1H-i915_cleanup',
     'kworker/11:1H-i915_cleanup', 'kworker/6:1H-kblockd', 'kworker/15:1H-kblockd',
     'kworker/1:1H-kblockd', 'kworker/7:1H-i915_cleanup',
     'kworker/10:1H-i915_cleanup', 'kworker/5:1H-kblockd', 'jbd2/dm-1-8',
     'kworker/R-ext4-rsv-conversion', 'kworker/4:1H-kblockd',
     'kworker/14:1H-kblockd', 'kworker/8:1H-i915_cleanup', 'kworker/9:1H-kblockd',
     'psimon', 'kworker/13:1H-i915_cleanup', 'kworker/3:1H-i915_cleanup',
     'irq/16-processor_thermal_device_pci', 'kworker/R-ttm', 'kworker/R-cfg80211',
     'jbd2/nvme0n1p2-8', 'card1-crtc0', 'card1-crtc1', 'card1-crtc2', 'card1-crtc3',
     'irq/200-iwlwifi:default_queue', 'irq/201-iwlwifi:queue_1',
     'irq/202-iwlwifi:queue_2', 'irq/203-iwlwifi:queue_3',
     'irq/204-iwlwifi:queue_4', 'irq/205-iwlwifi:queue_5',
     'irq/206-iwlwifi:queue_6', 'irq/207-iwlwifi:queue_7',
     'irq/208-iwlwifi:queue_8', 'irq/209-iwlwifi:queue_9',
     'irq/210-iwlwifi:queue_10', 'irq/211-iwlwifi:queue_11',
     'irq/212-iwlwifi:queue_12', 'irq/213-iwlwifi:queue_13',
     'irq/214-iwlwifi:queue_14', 'irq/215-iwlwifi:exception', 'kworker/R-rpciod',
     'kworker/R-xprtiod', 'irq/217-mei_gsc', 'irq/218-mei_gsc',
     'irq/197-cs35l41 IRQ1 Controller', 'irq/233-AudioDSP', 'spl_system_task',
     'spl_delay_taskq', 'spl_dynamic_tas', 'spl_kmem_cache', 'zvol_tq-0',
     'zvol_tq-1', 'zvol_tq-2', 'arc_prune', 'arc_evict', 'arc_flush', 'arc_reap',
     'dbu_evict', 'dbuf_evict', 'z_vdev_file', 'l2arc_feed', 'lockd', 'nfsd',
     'krfcommd', 'kworker/15:0-events', 'kworker/u64:2-events_unbound',
     'kworker/9:0-cgroup_free', 'kworker/14:0-mm_percpu_wq',
     'kworker/11:1-cgroup_free', 'kworker/u64:10-ishtp_unbound_0',
     'kworker/10:1-kdmflush/252:0', 'kworker/u65:1-i915_flip',
     'kworker/u64:12-kcryptd-252:0-1', 'kworker/1:2-events',
     'kworker/6:1-cgroup_release', 'kworker/5:2-events',
     'kworker/u64:5-kcryptd-252:0-1', 'kworker/u64:16-kcryptd-252:0-1',
     'kworker/u64:21-kcryptd-252:0-1', 'kworker/u64:27-kcryptd-252:0-1',
     'irq/198-mei_me', 'kworker/u64:28-kcryptd-252:0-1',
     'kworker/13:0-mm_percpu_wq', 'kworker/12:2-mm_percpu_wq', 'kworker/9:1-events',
     'kworker/7:1-i915-unordered', 'kworker/4:2-events',
     'kworker/11:2-mm_percpu_wq', 'kworker/1:1-events', 'kworker/2:2-mm_percpu_wq',
     'kworker/0:0-events', 'kworker/8:2-events', 'kworker/7:0-i915-unordered',
     'kworker/u64:1-kcryptd-252:0-1', 'kworker/u64:3-kcryptd-252:0-1',
     'kworker/14:2', 'kworker/15:2', 'kworker/3:2-mm_percpu_wq',
     'kworker/u64:6-kcryptd-252:0-1', 'kworker/u64:7-kcryptd-252:0-1',
     'kworker/12:1', 'kworker/6:2-events', 'kworker/u64:8-events_unbound',
     'kworker/u64:9-kcryptd-252:0-1', 'kworker/13:2-events', 'kworker/8:3-events',
     'kworker/3:1-events', 'kworker/u64:13-kcryptd-252:0-1',
     'kworker/u64:14-kcryptd-252:0-1', 'kworker/u64:15-kcryptd-252:0-1',
     'kworker/4:1', 'kworker/8:0-events', 'kworker/u65:2-hci0',
     'kworker/u65:4-hci0', 'sd_espeak-ng-mb', 'kworker/2:1-events',
     'kworker/5:1-events', 'kworker/0:2-kdmflush/252:0',
     'kworker/u64:0-kcryptd-252:0-1', 'kworker/10:2-events',
     'kworker/7:2-i915-unordered', 'kworker/11:0', 'kworker/3:0-mm_percpu_wq',
     'kworker/u64:4', 'kworker/u65:0-rb_allocator', 'kworker/0:1', 'kworker/1:0']
    >>> gl.programlist['python']
    {'cmdline': ['python'],
     'cpu_percent': 70.5,
     'cpu_times': {'children_system': 0.01,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.25,
                   'user': 0.33},
     'io_counters': [16384, 303104, 16384, 303104, 1],
     'memory_info': {'data': 126226432,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 91443200,
                     'shared': 28073984,
                     'text': 31211520,
                     'vms': 670072832},
     'memory_percent': 0.5758361359937952,
     'name': 'python',
     'nice': 0,
     'nprocs': 1,
     'num_threads': 7,
     'status': 'S',
     'time_since_update': 0.3700144290924072,
     'username': 'nicolargo'}

Programlist fields:

* ``name``: Program name (shared process name aggregating its threads). (unit is *string*)
* ``username``: Program owner (user name, '\_' when children differ). (unit is *string*)
* ``nprocs``: Number of child processes aggregated into this program. (unit is *number*)
* ``status``: Program status ('\_' when children differ). (unit is *string*)
* ``nice``: Program nice value ('\_' when children differ). (unit is *number*)
* ``num_threads``: Total number of threads across the program's children. (unit is *number*)
* ``cpu_percent``: Program CPU consumption (sum across children — can exceed 100%). (unit is *percent*)
* ``memory_percent``: Program resident memory consumption (sum across children). (unit is *percent*)
* ``cmdline``: Command line (the program name, as a single-token list). (unit is *list*)
* ``memory_info``: Aggregated memory information (dict with rss/vms keys). (unit is *byte*)
* ``cpu_times``: Aggregated CPU times (dict with user/system keys). (unit is *second*)
* ``io_counters``: Aggregated I/O counters (concatenated per-child blocks). (unit is *byte*)
* ``time_since_update``: Wall-clock interval since the previous engine refresh (seconds). (unit is *second*)
* ``cpucore``: Number of logical CPU cores (divisor of the Irix-mode CPU%). (unit is *number*)

Programlist limits:

.. code-block:: python

    >>> gl.programlist.limits
    {'cpu_percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'memory_percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances psutilversion
---------------------

.. code-block:: python

    >>> gl.psutilversion
    {'time_since_update': 0.37801444199976686, 'version': '7.2.2'}

Psutilversion fields:

* ``version``: psutil version. (unit is *string*)

Glances quicklook
-----------------

.. code-block:: python

    >>> gl.quicklook
    {'bar_char': '▪',
     'cpu': 8.0,
     'cpu_hz': 4475000000,
     'cpu_hz_current': 984958250,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'gpu_proc': 0.0,
     'load': 6.7,
     'max_cpu_display': 4,
     'mem': 45.8,
     'percpu': [{'cpu_number': 0, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 1, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 2, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 3, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 4, 'level': 'ok', 'total': 44.4},
                {'cpu_number': 5, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 6, 'level': 'ok', 'total': 20.0},
                {'cpu_number': 7, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 8, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 9, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 10, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 11, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 12, 'level': 'ok', 'total': 25.0},
                {'cpu_number': 13, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 14, 'level': 'ok', 'total': 20.0},
                {'cpu_number': 15, 'level': 'ok', 'total': 18.2}],
     'percpu_other': {'level': 'ok', 'total': 1.5166666666666666},
     'stats_list': ['cpu', 'mem', 'load'],
     'swap': 49.6,
     'time_since_update': 0.3767531659996166}

Quicklook fields:

* ``cpu``: CPU percent usage. (unit is *percent*)
* ``mem``: MEM percent usage. (unit is *percent*)
* ``swap``: SWAP percent usage. (unit is *percent*)
* ``load``: LOAD percent usage (15 min, normalized by core count). (unit is *percent*)
* ``gpu_mem``: Average GPU memory consumption. (unit is *percent*)
* ``gpu_proc``: Average GPU processor consumption. (unit is *percent*)
* ``percpu``: Per-core CPU usage (list of {cpu\_number, total, level}). (unit is *percent*)
* ``percpu_other``: Mean + level of the CPU cores hidden by max\_cpu\_display ({total, level}), or None when every core is shown. (unit is *percent*)
* ``max_cpu_display``: Number of per-core bars shown before collapsing the rest into percpu\_other ([percpu] max\_cpu\_display). (unit is *number*)
* ``cpu_log_core``: Number of logical CPU cores. (unit is *number*)
* ``cpu_phys_core``: Number of physical CPU cores. (unit is *number*)
* ``cpu_name``: CPU name. (unit is *string*)
* ``cpu_hz_current``: CPU current frequency (Hz). (unit is *hertz*)
* ``cpu_hz``: CPU max frequency (Hz). (unit is *hertz*)
* ``stats_list``: Stats displayed as bars, in display order ([quicklook] list). (unit is *string*)
* ``bar_char``: Character used to fill the bars ([quicklook] bar\_char). (unit is *string*)

Quicklook limits:

.. code-block:: python

    >>> gl.quicklook.limits
    {'cpu': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'gpu_mem': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'gpu_proc': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'load': {'careful': 70.0, 'critical': 500.0, 'warning': 100.0},
     'mem': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'swap': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances sensors
---------------

.. code-block:: python

    >>> gl.sensors.keys()
    ['Ambient (mean)', 'BAT BAT0', 'CPU', 'CPU Fan', 'Composite', 'Core (mean)',
     'HDD', 'Package id 0', 'SODIMM', 'Sensor (mean)', 'Video Fan',
     'dell_smm (mean)', 'i915 0', 'iwlwifi_1 0', 'temp']
    >>> gl.sensors['Ambient (mean)']
    {'critical': None,
     'label': 'Ambient (mean)',
     'type': 'temperature_core',
     'unit': 'C',
     'value': 39,
     'warning': 0}

Sensors fields:

* ``label``: Sensor label. (unit is *string*)
* ``type``: Sensor type (temperature\_core, fan\_speed, battery). (unit is *string*)
* ``unit``: Sensor unit. (unit is *string*)
* ``value``: Sensor value. (unit is *number*)
* ``warning``: Hardware warning threshold. (unit is *number*)
* ``critical``: Hardware critical threshold. (unit is *number*)
* ``status``: Battery charge status. (unit is *string*)

Glances system
--------------

.. code-block:: python

    >>> gl.system
    {'hostname': 'nicolargo-xps15',
     'hr_name': 'Ubuntu 26.04 64bit / Linux 7.0.0-43-generic',
     'linux_distro': 'Ubuntu 26.04',
     'os_name': 'Linux',
     'os_version': '7.0.0-43-generic',
     'platform': '64bit',
     'time_since_update': 0.2164504060001491}

System fields:

* ``os_name``: Operating system name. (unit is *string*)
* ``hostname``: Hostname. (unit is *string*)
* ``platform``: Platform (32 or 64 bits). (unit is *string*)
* ``linux_distro``: Linux distribution. (unit is *string*)
* ``os_version``: Operating system version. (unit is *string*)
* ``hr_name``: Human readable operating system name. (unit is *string*)

Glances uptime
--------------

.. code-block:: python

    >>> gl.uptime
    {'seconds': 492769, 'time_since_update': 0.2166157089995977}

Uptime fields:

* ``seconds``: Seconds elapsed since the system booted. (unit is *seconds*)

Glances version
---------------

.. code-block:: python

    >>> gl.version
    {'time_since_update': 0.21683109500008868, 'version': '5.0.0b2'}

Version fields:

* ``version``: Glances version. (unit is *string*)

Glances wifi
------------

.. code-block:: python

    >>> gl.wifi.keys()
    ['wlp0s20f3']
    >>> gl.wifi['wlp0s20f3']
    {'quality_level': -53.0, 'quality_link': 57.0, 'ssid': 'wlp0s20f3'}

Wifi fields:

* ``ssid``: Wi-Fi network name (interface name). (unit is *string*)
* ``quality_link``: Signal quality level. (unit is *dBm*)
* ``quality_level``: Signal strength level. (unit is *dBm*)

Helpers
-------

Human-readable units, as the terminal interface shows them:

.. code-block:: python

    >>> gl.auto_unit(gl.mem["used"])
    '6.78G'

A percentage as a text bar:

.. code-block:: python

    >>> gl.bar(gl.mem["percent"])
    '■■■■■■■■□□□□□□□□□□'

The top processes (the API's own process is left out):

.. code-block:: python

    >>> gl.top_process()
    [{'cpu_percent': 13.4,
      'memory_percent': 4.1609029316959045,
      'name': 'firefox',
      'pid': 90955},
     {'cpu_percent': 0.0,
      'memory_percent': 5.086548235723197,
      'name': 'Isolated Web Co',
      'pid': 92572},
     {'cpu_percent': 0.0,
      'memory_percent': 4.658249958537219,
      'name': 'WebExtensions',
      'pid': 91819}]

Reference
---------

.. code-block:: python

    GlancesAPI(config_path: 'str | None' = None, background: 'bool' = False, plugins: 'list[str] | None' = None, refresh: 'float | None' = None, disable_config_exec: 'bool' = False) -> 'None'

.. code-block:: text

    Glances' stats, from Python.
    
    Args:
        config_path: an extra ``glances.conf``, layered over the usual search
            path (system file, XDG file, ``GLANCES_<SECTION>__<KEY>``), as
            ``-C`` does. ``sys.argv`` is never read.
        background: run the v5 scheduler in a thread, so stats stay fresh and
            the history and alerts fill up between reads. Off by default: then
            a plugin is updated when it is read.
        plugins: build only these plugins (and what they depend on), e.g.
            ``["cpu", "mem"]``. Default: every plugin ``glances.conf`` enables.
        refresh: seconds, overriding ``[global] refresh`` as ``-t`` does: how
            long a read stays cached on demand, and the scheduler's cadence in
            the background (per-plugin ``[<plugin>] refresh`` keys still win).
        disable_config_exec: as ``--disable-config-exec``: the commands that
            ``glances.conf`` gives the AMPs run without shell operators.
    
    Use it as a context manager, or call ``close()``: some plugins hold
    background resources until then.

.. code-block:: python

    GlancesAPI.alerts() -> 'list[dict[str, Any]]'

.. code-block:: text

    The alert events recorded so far, as ``/api/5/alert`` serves them.

.. code-block:: python

    GlancesAPI.auto_unit(number: 'Any', low_precision: 'bool' = False, min_symbol: 'str' = 'K', none_symbol: 'str' = '-') -> 'str'

.. code-block:: text

    A number as a human-readable string with a unit suffix (``6.07G``). Same as v4.

.. code-block:: python

    GlancesAPI.bar(value: 'float', size: 'int' = 18, bar_char: 'str' = '■', empty_char: 'str' = '□', pre_char: 'str' = '', post_char: 'str' = '') -> 'str'

.. code-block:: text

    A percentage as a text bar (``■■□□□□``). Same as v4.

.. code-block:: python

    GlancesAPI.close() -> 'None'

.. code-block:: text

    Stop the scheduler if it runs, release the plugins' resources, stop the loop.

.. code-block:: python

    GlancesAPI.plugins() -> 'list[str]'

.. code-block:: text

    The plugins this API built (enabled in glances.conf, and in `plugins=` if given).

.. code-block:: python

    GlancesAPI.top_process(limit: 'int' = 3, sorted_by: 'str' = 'cpu_percent', sorted_by_secondary: 'str' = 'memory_percent') -> 'list[dict[str, Any]]'

.. code-block:: text

    The top processes, sorted by `sorted_by` then `sorted_by_secondary`.
    
    Leaves out kernel threads (no command line), as v4 does, and this
    process itself, which is the one reading its own load. v4 matched
    "glances" as a whole argument instead, which missed `/usr/bin/glances`.

.. code-block:: python

    PluginView(plugin: 'GlancesPluginBase') -> 'None'

.. code-block:: text

    A read-only snapshot of one plugin, as it was when it was read (design §5.4).
    
    A mapping: ``view[key]``, ``get``, ``keys``, ``items``, ``len``, ``in``.
    For a collection plugin the keys are the primary-key values
    (``gl.network["eth0"]``, ``gl.processlist[1234]``, ``gl.fs["/home"]``);
    for a scalar plugin they are the field names.
    
    Everything it holds is a copy: changing it changes nothing Glances, or a
    later read, sees. Read ``gl.<plugin>`` again for fresh values.
    
    Attributes:
        name: the plugin name.
        raw: the payload, as ``/api/5/<plugin>`` serves it without its
            ``_``-prefixed metadata (v4 ``get_raw()``).
        fields: the schema, ``fields_description`` (``/api/5/<plugin>/info``).
        limits: the effective thresholds (v4 ``.limits``).
        levels: the alert level of each watched field, ``_levels``.

.. code-block:: python

    PluginView.history(nb: 'int' = 0, field: 'str | None' = None, item: 'str | None' = None) -> 'dict[str, Any]'

.. code-block:: text

    The plugin's history, as ``/api/5/<plugin>/history`` serves it.
    
    Read when called, not when the view was taken. Raises ``KeyError`` for
    a field the plugin does not historise or an item it has no series for.
