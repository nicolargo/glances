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
     'idle': 93.3,
     'interrupts': 0.0,
     'iowait': 1.0,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 2.9,
     'time_since_update': 0.9349361390000013,
     'total': 6.7,
     'user': 2.9}
    >>> gl.cpu["total"]
    6.7
    >>> gl.mem["used"]
    2682834944
    >>> gl.auto_unit(gl.mem["used"])
    '2.50G'
    >>> gl.network.keys()
    ['wlp0s20f3', 'tailscale0']
    >>> gl.network["wlp0s20f3"]
    {'bytes_recv': 596.7749334297607,
     'bytes_recv_cumul': 3384127,
     'bytes_sent': 160.77498206555197,
     'bytes_sent_cumul': 610060,
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
     'timer': 1.0584840774536133}

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
    {'log': 16, 'phys': 10, 'time_since_update': 0.9431262429999947}

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
     'idle': 93.3,
     'interrupts': 0.0,
     'iowait': 1.0,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 2.9,
     'time_since_update': 0.9349361390000013,
     'total': 6.7,
     'user': 2.9}

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
     'read_bytes': 169354.40972907984,
     'read_bytes_cumul': 3003047936,
     'read_count': 3.180483956751049,
     'read_count_cumul': 117656,
     'read_latency': 3,
     'read_time': 10.601613189170163,
     'write_bytes': 22480712.286344778,
     'write_bytes_cumul': 378012672,
     'write_count': 1759.867789402247,
     'write_count_cumul': 27257,
     'write_latency': 2,
     'write_time': 4748.462547429316}

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
     'free': 438736703488,
     'fs_type': 'ext4',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 53.9,
     'size': 1003736440832,
     'used': 513937231872}

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
    {'address': '192.168.1.31',
     'mask': '255.255.255.0',
     'mask_cidr': 24,
     'time_since_update': 0.7560654309999961}

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
     'min1': 1.13671875,
     'min15': 0.38525390625,
     'min5': 0.88037109375,
     'time_since_update': 0.7557994119999876}

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
    {'active': 3205263360,
     'available': 13197238272,
     'buffers': 420151296,
     'cached': 3430461184,
     'free': 9933754368,
     'inactive': 1527541760,
     'percent': 16.9,
     'shared': 236433408,
     'slab': 682905600,
     'time_since_update': 0.740620741000015,
     'total': 15880073216,
     'used': 2682834944}

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
    {'free': 4294963200,
     'percent': 0.0,
     'sin': 0.0,
     'sout': 0.0,
     'time_since_update': 0.7538837080000178,
     'total': 4294963200,
     'used': 0}

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
    {'bytes_recv': 596.7749334297607,
     'bytes_recv_cumul': 3384127,
     'bytes_sent': 160.77498206555197,
     'bytes_sent_cumul': 610060,
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
    {'custom': '2026-11-15 18:14:20 CET',
     'iso': '2026-11-15T18:14:20+01:00',
     'time_since_update': 0.7511392170000022}

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
     'idle': 97.4,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 2.6,
     'total': 2.6,
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
     'status': 0.018929,
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
     'sleeping': 288,
     'sort_key': 'cpu_percent',
     'thread': 1172,
     'time_since_update': 0.7191197269999918,
     'total': 467}

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
    [11235, 130, 526, 517, 524, 527, 10588, 15, 8489, 7925, 8448, 3433, 3445, 4063,
     9162, 10355, 8507, 8256, 9180, 9367, 8149, 3125, 8482, 9567, 3461, 9117, 10064,
     3448, 8291, 4076, 9858, 4069, 8456, 8348, 8247, 3451, 631, 11231, 8163, 8377,
     8559, 9424, 4062, 7339, 8141, 7352, 3238, 9108, 3146, 1, 3431, 3482, 7278,
     3155, 676, 3151, 8206, 8198, 9153, 700, 4079, 8217, 3366, 3110, 7333, 8189,
     8346, 3242, 8561, 3404, 8201, 3805, 7351, 7847, 8184, 7337, 7045, 8195, 8243,
     8231, 8265, 8187, 8188, 4184, 9615, 9616, 3806, 9090, 8386, 8236, 4031, 3138,
     8224, 3092, 8618, 7520, 7837, 3130, 8211, 3101, 8196, 3367, 8414, 3142, 7812,
     8356, 8113, 8547, 671, 8603, 7457, 8344, 7844, 3132, 8213, 3861, 8624, 8122,
     670, 3091, 6374, 8612, 6373, 7461, 10539, 7500, 10838, 7332, 3172, 8150, 7815,
     9735, 3118, 3230, 7814, 7342, 8120, 3959, 3090, 7338, 7307, 2908, 3096, 4683,
     4075, 2924, 11227, 4074, 7468, 4408, 4084, 3435, 3442, 11230, 4080, 3218, 4411,
     3860, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22,
     23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
     43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
     63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
     83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
     102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
     118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 131, 132, 133, 134,
     135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150,
     151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166,
     168, 179, 180, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 312,
     313, 314, 475, 476, 477, 478, 486, 488, 514, 515, 516, 518, 519, 520, 521, 522,
     523, 525, 528, 529, 530, 532, 550, 553, 554, 586, 622, 662, 673, 696, 703, 704,
     705, 724, 753, 773, 783, 804, 833, 960, 992, 996, 998, 1030, 1055, 1056, 1057,
     1058, 1148, 1149, 1150, 1152, 1153, 1154, 1156, 1157, 1158, 1159, 1160, 1161,
     1162, 1163, 1164, 1165, 1167, 1168, 1169, 1201, 1203, 1546, 1596, 1597, 1602,
     1611, 1622, 1623, 1636, 1747, 1885, 2201, 2202, 2203, 2204, 2205, 2206, 2207,
     2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 2921,
     3205, 3484, 4126, 4142, 4237, 4238, 4239, 4240, 4241, 4242, 4243, 4244, 4245,
     4246, 4247, 4248, 4249, 4250, 4251, 4252, 5196, 5367, 6975, 6976, 9300, 9617,
     10616, 10623, 10628, 11256, 11257]
    >>> gl.processlist[11235]
    {'cmdline': ['/home/nicolargo/dev/glances/.venv/bin/python',
                 '-m',
                 'glances.api_doc',
                 '-C',
                 'conf/glances.conf'],
     'cpu_num': 4,
     'cpu_percent': 69.5,
     'cpu_times': {'children_system': 0.02,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.52,
                   'user': 0.63},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [39088128, 98304, 39088128, 98304, 1],
     'key': 'pid',
     'memory_info': {'data': 125509632,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 89300992,
                     'shared': 25632768,
                     'text': 31211520,
                     'vms': 668983296},
     'memory_percent': 0.5623462233790245,
     'name': 'python',
     'nice': 0,
     'num_threads': 7,
     'pid': 11235,
     'status': 'S',
     'time_since_update': 0.7508246898651123,
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
    ['python', 'irq/9-acpi', 'kworker/u64:12-events_unbound',
     'kworker/u64:6-kcryptd-252:0-1', 'kworker/u64:10-kcryptd-252:0-1',
     'kworker/u64:13-kcryptd-252:0-1', 'kworker/u64:15-kcryptd-252:0-1',
     'rcu_preempt', 'dropbox', 'gnome-shell', 'snap-store', 'python3', 'multipassd',
     'dockerd', 'mutter-x11-frames', 'terminator', 'Xwayland',
     'evolution-alarm-notify', 'ibus-x11', 'gjs', 'evolution-source-registry',
     'snapd', 'evolution-calendar-factory', 'fwupd', 'containerd',
     'xdg-desktop-portal-gnome', 'packagekitd', 'tailscaled', 'goa-daemon',
     'libvirtd', 'snapd-desktop-integration', 'ollama', 'localsearch-3',
     'ibus-extension-gtk3', 'update-notifier', 'unattended-upgr',
     'systemd-journald', 'uv', 'evolution-addressbook-factory',
     'xdg-desktop-portal-gtk', 'cups-browsed', 'wireplumber',
     'gnome-shell-calendar-server', 'NetworkManager', 'xdg-desktop-portal',
     'udisksd', 'systemd', 'cupsd', 'colord', 'virtlogd', 'systemd-udevd',
     'virtlockd', 'gsd-print-notifications', 'gsd-media-keys', 'gsd-xsettings',
     'systemd-resolved', 'snmpd', 'gsd-sharing', 'ModemManager', 'polkitd',
     'pipewire', 'gsd-datetime', 'gsd-printer', 'wpa_supplicant',
     'gvfs-udisks2-volume-monitor', 'upowerd', 'gsd-power', 'pipewire-pulse',
     'gnome-session-service', 'ibus-daemon', 'gnome-keyring-daemon',
     'gdm-session-worker', 'gsd-housekeeping', 'gsd-wwan', 'gsd-sound',
     'gsd-disk-utility-notify', 'gsd-a11y-settings', 'gsd-color', 'gdm3',
     '(udev-worker)', 'cups-proxyd', 'gvfsd-trash', 'goa-identity-service',
     'gsd-usb-protection', 'thermald', 'systemd-logind', 'gsd-smartcard',
     'dbus-daemon', 'gvfs-afc-volume-monitor', 'gnome-session-init-worker', 'gvfsd',
     'accounts-daemon', 'gsd-rfkill', 'iio-sensor-proxy', 'gsd-keyboard', 'boltd',
     'gvfsd-metadata', 'systemd-machined', 'gcr-ssh-agent', 'ibus-portal',
     'at-spi-bus-launcher', 'ibus-engine-simple', 'systemd-timesyncd',
     'gvfs-gphoto2-volume-monitor', 'xdg-document-portal', 'ibus-memconf',
     'gvfsd-fuse', 'switcheroo-control', 'gsd-screensaver-proxy', 'sleep',
     'gvfs-mtp-volume-monitor', 'at-spi2-registryd', 'systemd-oomd', 'bluetoothd',
     'dbus', 'gvfs-goa-volume-monitor', 'xdg-permission-store', 'bash',
     'gdm-wayland-session', 'ssh-agent', 'zed', 'dconf-service',
     'user-session-helper', 'smartd', 'rsyslogd', 'gnome-session-ctl', 'dnsmasq',
     'avahi-daemon', 'mpris-proxy', '(sd-pam)', 'rpcbind', 'fsidd', 'rtkit-daemon',
     'cron', 'nfsdcld', 'make', 'rpc.idmapd', 'fusermount3', 'rpc.statd',
     'run-cups-browse', 'run-cupsd', 'sh', 'rpc.mountd', 'kthreadd',
     'pool_workqueue_release', 'kworker/R-rcu_gp', 'kworker/R-sync_wq',
     'kworker/R-kvfree_rcu_reclaim', 'kworker/R-slub_flushwq', 'kworker/R-netns',
     'kworker/0:0-events', 'kworker/0:0H-kblockd', 'kworker/0:1-kacpi_notify',
     'kworker/u64:0-kcryptd-252:0-1', 'kworker/R-mm_percpu_wq', 'ksoftirqd/0',
     'rcu_exp_par_gp_kthread_worker/0', 'rcu_exp_gp_kthread_worker', 'migration/0',
     'kprobe-optimizer', 'idle_inject/0', 'cpuhp/0', 'cpuhp/2', 'idle_inject/2',
     'migration/2', 'ksoftirqd/2', 'kworker/2:0-inode_switch_wbs',
     'kworker/2:0H-kblockd', 'cpuhp/4', 'idle_inject/4', 'migration/4',
     'ksoftirqd/4', 'kworker/4:0-events', 'kworker/4:0H-kblockd', 'cpuhp/6',
     'idle_inject/6', 'migration/6', 'ksoftirqd/6', 'kworker/6:0-cgroup_free',
     'kworker/6:0H-kblockd', 'cpuhp/8', 'idle_inject/8', 'migration/8',
     'ksoftirqd/8', 'kworker/8:0-rcu_gp', 'kworker/8:0H-kblockd', 'cpuhp/10',
     'idle_inject/10', 'migration/10', 'ksoftirqd/10', 'kworker/10:0-events',
     'kworker/10:0H-kblockd', 'cpuhp/12', 'idle_inject/12', 'migration/12',
     'ksoftirqd/12', 'kworker/12:0-events', 'kworker/12:0H-kblockd', 'cpuhp/13',
     'idle_inject/13', 'migration/13', 'ksoftirqd/13', 'kworker/13:0-events',
     'kworker/13:0H-kblockd', 'cpuhp/14', 'idle_inject/14', 'migration/14',
     'ksoftirqd/14', 'kworker/14:0-cgroup_release', 'kworker/14:0H-kblockd',
     'cpuhp/15', 'idle_inject/15', 'migration/15', 'ksoftirqd/15',
     'kworker/15:0-usb_hub_wq', 'kworker/15:0H-kblockd', 'cpuhp/1', 'idle_inject/1',
     'migration/1', 'ksoftirqd/1', 'kworker/1:0-slub_flushwq',
     'kworker/1:0H-kblockd', 'cpuhp/3', 'idle_inject/3', 'migration/3',
     'ksoftirqd/3', 'kworker/3:0-cgroup_free', 'kworker/3:0H-kblockd', 'cpuhp/5',
     'idle_inject/5', 'migration/5', 'ksoftirqd/5', 'kworker/5:0-inode_switch_wbs',
     'kworker/5:0H-kblockd', 'cpuhp/7', 'idle_inject/7', 'migration/7',
     'ksoftirqd/7', 'kworker/7:0-i915-unordered', 'kworker/7:0H-kblockd', 'cpuhp/9',
     'idle_inject/9', 'migration/9', 'ksoftirqd/9', 'kworker/9:0-cgroup_release',
     'kworker/9:0H-kblockd', 'cpuhp/11', 'idle_inject/11', 'migration/11',
     'ksoftirqd/11', 'kworker/11:0-events', 'kworker/11:0H-kblockd', 'kdevtmpfs',
     'kworker/R-inet_frag_wq', 'rcu_tasks_kthread', 'rcu_tasks_rude_kthread',
     'kauditd', 'khungtaskd', 'kworker/u64:1-kcryptd-252:0-1', 'oom_reaper',
     'kworker/u64:2-kcryptd-252:0-1', 'kworker/R-writeback', 'kcompactd0', 'ksmd',
     'khugepaged', 'kworker/R-kblockd', 'kworker/R-blkcg_punt_bio',
     'kworker/R-kintegrityd', 'kworker/11:1-cgroup_free',
     'kworker/12:1-cgroup_release', 'kworker/13:1-rcu_gp',
     'kworker/1:1-cgroup_release', 'kworker/R-tpm_dev_wq', 'kworker/2:1-events',
     'kworker/R-ata_sff', 'kworker/R-md_bitmap', 'kworker/R-md_llbitmap_io',
     'kworker/R-md_llbitmap_unplug', 'kworker/R-edac-poller',
     'kworker/R-devfreq_wq', 'kworker/4:1-events', 'kworker/2:2-mm_percpu_wq',
     'watchdogd', 'kworker/R-quota_events_unbound', 'kworker/5:1-events', 'kswapd0',
     'ecryptfs-kthread', 'kworker/3:1-events', 'kworker/R-kthrotld',
     'irq/123-pciehp', 'irq/124-pciehp', 'kworker/R-acpi_thermal_pm',
     'kworker/u64:3-kcryptd-252:0-1', 'kworker/14:1-events', 'hwrng',
     'kworker/u64:4-flush-252:1', 'kworker/R-hfi-updates', 'kworker/6:1-events',
     'kworker/R-mld', 'kworker/R-ipv6_addrconf', 'kworker/R-kstrp',
     'kworker/15:1-mm_percpu_wq', 'kworker/7:1-events', 'kworker/8:1-events',
     'kworker/10:1-mm_percpu_wq', 'kworker/9:1-events', 'kworker/u65:0-ttm',
     'kworker/R-charger_manager', 'kworker/6:2-cgroup_bpf_destroy',
     'kworker/10:2-cgroup_release', 'kworker/13:2-mm_percpu_wq',
     'irq/178-VEN_04F3:00', 'kworker/11:2-mm_percpu_wq', 'spi0',
     'kworker/R-nvme-wq', 'kworker/R-nvme-reset-wq', 'kworker/R-nvme-delete-wq',
     'kworker/R-nvme-auth-wq', 'kworker/8:2-events', 'kworker/4:2-events',
     'kworker/5:2', 'kworker/R-USBC000:00-con1', 'kworker/R-USBC000:00-con2',
     'kworker/R-USBC000:00-con3', 'kworker/R-kdmflush/252:0',
     'kworker/R-kcryptd_io-252:0-1', 'kworker/R-kcryptd-252:0-1',
     'dmcrypt_write/252:0', 'kworker/2:1H-i915_cleanup', 'kworker/R-kdmflush/252:1',
     'kworker/0:1H-kblockd', 'kworker/12:1H-i915_cleanup',
     'kworker/u64:5-kcryptd-252:0-1', 'kworker/11:1H-kblockd',
     'kworker/6:1H-kblockd', 'kworker/u64:7-kcryptd-252:0-1',
     'kworker/u64:8-kcryptd-252:0-1', 'kworker/15:1H-kblockd',
     'kworker/u64:9-kcryptd-252:0-1', 'kworker/u64:11-kcryptd-252:0-1',
     'kworker/u64:14-kcryptd-252:0-1', 'kworker/1:1H-kblockd',
     'kworker/7:1H-i915_cleanup', 'kworker/10:1H-kblockd', 'kworker/5:1H-kblockd',
     'jbd2/dm-1-8', 'kworker/R-ext4-rsv-conversion', 'kworker/4:1H-i915_cleanup',
     'psimon', 'kworker/7:2-cgwb_release', 'kworker/3:2-mm_percpu_wq',
     'kworker/14:1H-i915_cleanup', 'kworker/8:1H-i915_cleanup',
     'kworker/9:1H-kblockd', 'kworker/13:1H-kblockd', 'kworker/3:1H-kblockd',
     'kworker/12:2-mm_percpu_wq', 'kworker/9:2-mm_percpu_wq', 'kworker/1:2-events',
     'irq/16-processor_thermal_device_pci', 'kworker/R-ttm', 'kworker/R-cfg80211',
     'jbd2/nvme0n1p2-8', 'irq/198-mei_me', 'card1-crtc0', 'card1-crtc1',
     'card1-crtc2', 'card1-crtc3', 'irq/200-iwlwifi:default_queue',
     'irq/201-iwlwifi:queue_1', 'irq/202-iwlwifi:queue_2',
     'irq/203-iwlwifi:queue_3', 'irq/204-iwlwifi:queue_4',
     'irq/205-iwlwifi:queue_5', 'irq/206-iwlwifi:queue_6',
     'irq/207-iwlwifi:queue_7', 'irq/208-iwlwifi:queue_8',
     'irq/209-iwlwifi:queue_9', 'irq/210-iwlwifi:queue_10',
     'irq/211-iwlwifi:queue_11', 'irq/212-iwlwifi:queue_12',
     'irq/213-iwlwifi:queue_13', 'irq/214-iwlwifi:queue_14',
     'irq/215-iwlwifi:exception', 'kworker/R-rpciod', 'kworker/R-xprtiod',
     'kworker/14:2-events', 'kworker/1:3-events', 'kworker/15:2-events',
     'kworker/u65:1-i915_flip', 'kworker/u65:2-rb_allocator', 'irq/217-mei_gsc',
     'irq/218-mei_gsc', 'kworker/11:3', 'kworker/11:4',
     'irq/197-cs35l41 IRQ1 Controller', 'irq/233-AudioDSP', 'spl_system_task',
     'spl_delay_taskq', 'spl_dynamic_tas', 'spl_kmem_cache', 'zvol_tq-0',
     'zvol_tq-1', 'zvol_tq-2', 'arc_prune', 'arc_evict', 'arc_flush', 'arc_reap',
     'dbu_evict', 'dbuf_evict', 'z_vdev_file', 'l2arc_feed', 'kworker/6:3',
     'kworker/14:3', 'kworker/12:3-events', 'kworker/0:2-kacpi_notify', 'lockd',
     'nfsd', 'krfcommd', 'kworker/u65:3-ttm', 'kworker/0:3-kacpi_notify',
     'kworker/0:4-cgroup_free', 'kworker/12:4', 'kworker/2:3',
     'kworker/u64:16-kcryptd-252:0-1', 'kworker/10:3', 'kworker/7:3-i915-unordered',
     'kworker/u64:17-kcryptd-252:0-1', 'kworker/u64:18-events_unbound']
    >>> gl.programlist['python']
    {'cmdline': ['python'],
     'cpu_percent': 69.5,
     'cpu_times': {'children_system': 0.02,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.52,
                   'user': 0.63},
     'io_counters': [39088128, 98304, 39088128, 98304, 1],
     'memory_info': {'data': 125509632,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 89300992,
                     'shared': 25632768,
                     'text': 31211520,
                     'vms': 668983296},
     'memory_percent': 0.5623462233790245,
     'name': 'python',
     'nice': 0,
     'nprocs': 1,
     'num_threads': 7,
     'status': 'S',
     'time_since_update': 0.7508246898651123,
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
    {'time_since_update': 0.7284471250000024, 'version': '7.2.2'}

Psutilversion fields:

* ``version``: psutil version. (unit is *string*)

Glances quicklook
-----------------

.. code-block:: python

    >>> gl.quicklook
    {'bar_char': '▪',
     'cpu': 5.4,
     'cpu_hz': 4475000000,
     'cpu_hz_current': 724598312,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'gpu_proc': 0.0,
     'load': 2.4,
     'max_cpu_display': 4,
     'mem': 16.9,
     'percpu': [{'cpu_number': 0, 'level': 'ok', 'total': 2.6},
                {'cpu_number': 1, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 2, 'level': 'ok', 'total': 2.4},
                {'cpu_number': 3, 'level': 'ok', 'total': 2.5},
                {'cpu_number': 4, 'level': 'ok', 'total': 7.7},
                {'cpu_number': 5, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 6, 'level': 'ok', 'total': 30.0},
                {'cpu_number': 7, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 8, 'level': 'ok', 'total': 5.1},
                {'cpu_number': 9, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 10, 'level': 'ok', 'total': 7.5},
                {'cpu_number': 11, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 12, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 13, 'level': 'ok', 'total': 2.5},
                {'cpu_number': 14, 'level': 'ok', 'total': 5.0},
                {'cpu_number': 15, 'level': 'ok', 'total': 2.6}],
     'percpu_other': {'level': 'ok', 'total': 1.4666666666666668},
     'stats_list': ['cpu', 'mem', 'load'],
     'swap': 0.0,
     'time_since_update': 0.7284522559999971}

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
     'value': 23,
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
     'time_since_update': 0.3400127740000016}

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
    {'seconds': 211, 'time_since_update': 0.34067554300000324}

Uptime fields:

* ``seconds``: Seconds elapsed since the system booted. (unit is *seconds*)

Glances version
---------------

.. code-block:: python

    >>> gl.version
    {'time_since_update': 0.3413223750000043, 'version': '5.0.0b1'}

Version fields:

* ``version``: Glances version. (unit is *string*)

Glances wifi
------------

.. code-block:: python

    >>> gl.wifi.keys()
    ['wlp0s20f3']
    >>> gl.wifi['wlp0s20f3']
    {'quality_level': -65.0, 'quality_link': 45.0, 'ssid': 'wlp0s20f3'}

Wifi fields:

* ``ssid``: Wi-Fi network name (interface name). (unit is *string*)
* ``quality_link``: Signal quality level. (unit is *dBm*)
* ``quality_level``: Signal strength level. (unit is *dBm*)

Helpers
-------

Human-readable units, as the terminal interface shows them:

.. code-block:: python

    >>> gl.auto_unit(gl.mem["used"])
    '2.50G'

A percentage as a text bar:

.. code-block:: python

    >>> gl.bar(gl.mem["percent"])
    '■■■□□□□□□□□□□□□□□□'

The top processes (the API's own process is left out):

.. code-block:: python

    >>> gl.top_process()
    [{'cpu_percent': 0.0,
      'memory_percent': 1.9100220249261601,
      'name': 'dropbox',
      'pid': 8489},
     {'cpu_percent': 0.0,
      'memory_percent': 1.7506192334170154,
      'name': 'gnome-shell',
      'pid': 7925},
     {'cpu_percent': 0.0,
      'memory_percent': 1.5771590759899934,
      'name': 'snap-store',
      'pid': 8448}]

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
