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
     'idle': 92.8,
     'interrupts': 0.0,
     'iowait': 1.6,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 2.8,
     'time_since_update': 0.9812228270020569,
     'total': 7.2,
     'user': 2.8}
    >>> gl.cpu["total"]
    7.2
    >>> gl.mem["used"]
    7062646784
    >>> gl.auto_unit(gl.mem["used"])
    '6.58G'
    >>> gl.network.keys()
    ['wlp0s20f3', 'tailscale0']
    >>> gl.network["wlp0s20f3"]
    {'bytes_recv': 1369.2062086879355,
     'bytes_recv_cumul': 4270742054,
     'bytes_sent': 571.0495692993786,
     'bytes_sent_cumul': 222560057,
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
     'timer': 1.1539652347564697}

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
    {'log': 16, 'phys': 10, 'time_since_update': 1.003720182001416}

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
     'idle': 92.8,
     'interrupts': 0.0,
     'iowait': 1.6,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 2.8,
     'time_since_update': 0.9812228270020569,
     'total': 7.2,
     'user': 2.8}

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
     'read_bytes': 32627.56853042126,
     'read_bytes_cumul': 61118526464,
     'read_count': 4.9785718582796115,
     'read_count_cumul': 4462766,
     'read_latency': 5,
     'read_time': 27.880002406365822,
     'write_bytes': 562825.5571497667,
     'write_bytes_cumul': 53392274432,
     'write_count': 4.9785718582796115,
     'write_count_cumul': 5875604,
     'write_latency': 9,
     'write_time': 46.79857546782835}

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
     'free': 435863838720,
     'fs_type': 'ext4',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 54.2,
     'size': 1003736440832,
     'used': 516810096640}

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
     'proc': 1,
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
     'time_since_update': 0.8184524799944484}

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
     'min1': 1.44775390625,
     'min15': 1.009765625,
     'min5': 1.22509765625,
     'time_since_update': 0.8185004800034221}

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
    {'active': 4175380480,
     'available': 8817426432,
     'buffers': 312918016,
     'cached': 6755233536,
     'free': 2056323072,
     'inactive': 7082876928,
     'percent': 44.5,
     'shared': 1117564928,
     'slab': 1675554816,
     'time_since_update': 0.7697641150007257,
     'total': 15880073216,
     'used': 7062646784}

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
    {'free': 2940100608,
     'percent': 31.5,
     'sin': 5011.164338269173,
     'sout': 0.0,
     'time_since_update': 0.8173749100023997,
     'total': 4294963200,
     'used': 1354862592}

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
    {'bytes_recv': 1369.2062086879355,
     'bytes_recv_cumul': 4270742054,
     'bytes_sent': 571.0495692993786,
     'bytes_sent_cumul': 222560057,
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
    {'custom': '2026-11-28 10:21:16 CET',
     'iso': '2026-11-28T10:21:16+01:00',
     'time_since_update': 0.8155975090048742}

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
     'idle': 96.2,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 1.9,
     'total': 3.8,
     'user': 1.9}

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
     'status': 0.017594,
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
     'sleeping': 319,
     'sort_key': 'cpu_percent',
     'thread': 1763,
     'time_since_update': 0.7969542689970694,
     'total': 477}

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
    [831536, 130, 713185, 3138, 805840, 825641, 713550, 714319, 7925, 289229,
     683819, 713506, 713500, 470171, 826968, 713450, 719886, 289435, 713458, 8489,
     827117, 827203, 827197, 165014, 732945, 714747, 3125, 713431, 8456, 4063,
     831533, 3448, 9567, 713428, 631, 8482, 778949, 657437, 661770, 289415, 4069,
     657394, 7351, 3461, 1, 8163, 13733, 7333, 8256, 8247, 8149, 8448, 8377, 7339,
     8291, 3110, 7278, 676, 226226, 9117, 826934, 8141, 3242, 3092, 4076, 804700,
     9108, 9858, 3482, 3146, 226200, 9424, 732029, 8561, 8201, 8507, 826606, 8348,
     465393, 7337, 3404, 8217, 3366, 7045, 8198, 9090, 7332, 143050, 9162, 7457,
     675303, 7847, 8559, 9180, 250150, 8265, 8195, 700, 4184, 9153, 3132, 3805,
     3101, 3091, 3806, 8206, 8414, 143065, 8624, 255897, 3130, 8346, 7837, 8184,
     8150, 8603, 8236, 226215, 3367, 831529, 8188, 671, 713322, 8547, 226201, 7812,
     3142, 8618, 8243, 10838, 8196, 8231, 8211, 8224, 8189, 470545, 8122, 8113,
     8356, 8612, 8213, 8187, 8386, 826603, 7461, 4079, 4031, 670, 4683, 57083, 3090,
     8344, 8120, 831532, 7500, 7844, 7520, 3118, 826605, 7338, 3451, 143283, 3433,
     4408, 143339, 3860, 4075, 226272, 3096, 7342, 3155, 4074, 2924, 3151, 2908,
     7814, 7815, 9735, 4080, 4084, 7307, 3435, 3442, 4411, 7468, 3218, 2, 3, 4, 5,
     6, 7, 8, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29,
     30, 31, 33, 34, 35, 36, 37, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49, 51, 52, 53,
     54, 55, 57, 58, 59, 60, 61, 63, 64, 65, 66, 67, 69, 70, 71, 72, 73, 75, 76, 77,
     78, 79, 81, 82, 83, 84, 85, 87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 99, 100,
     101, 102, 103, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 117, 119,
     121, 122, 123, 124, 125, 126, 127, 133, 135, 136, 137, 138, 139, 140, 143, 144,
     146, 147, 149, 150, 151, 152, 155, 157, 159, 160, 161, 179, 260, 262, 263, 264,
     265, 266, 312, 313, 314, 475, 476, 477, 478, 486, 488, 514, 515, 518, 519, 522,
     529, 530, 532, 550, 553, 554, 586, 696, 703, 704, 705, 724, 753, 833, 960, 992,
     996, 998, 1055, 1056, 1057, 1058, 1148, 1149, 1150, 1152, 1153, 1154, 1156,
     1157, 1158, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1167, 1168, 1203, 1602,
     1611, 1636, 1747, 1885, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209,
     2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 4142, 4237, 4238,
     4239, 4240, 4241, 4242, 4243, 4244, 4245, 4246, 4247, 4248, 4249, 4250, 4251,
     4252, 5196, 143062, 412669, 475590, 657203, 657221, 661725, 698428, 720037,
     726057, 731760, 739704, 744599, 746623, 769198, 778477, 781523, 781558, 782448,
     783782, 791810, 792817, 793910, 794634, 795531, 802548, 803524, 804524, 804525,
     806255, 811404, 812292, 819068, 819751, 819795, 820846, 820859, 820861, 821180,
     825487, 825536, 825538, 825562, 825581, 825830, 825842, 826665, 826675, 826694,
     826711, 826895, 826953, 827004, 827069, 827091, 827256, 827416, 830344, 830383,
     830554, 830583, 831443]
    >>> gl.processlist[831536]
    {'cmdline': ['/home/nicolargo/dev/glances/.venv/bin/python',
                 '-m',
                 'glances.api_doc',
                 '-C',
                 'conf/glances.conf'],
     'cpu_num': 4,
     'cpu_percent': 66.5,
     'cpu_times': {'children_system': 0.03,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.57,
                   'user': 0.81},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [36933632, 794624, 36933632, 794624, 1],
     'key': 'pid',
     'memory_info': {'data': 125710336,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 89100288,
                     'shared': 25690112,
                     'text': 31211520,
                     'vms': 669437952},
     'memory_percent': 0.5610823501130134,
     'name': 'python',
     'nice': 0,
     'num_threads': 7,
     'pid': 831536,
     'status': 'S',
     'time_since_update': 0.815732479095459,
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
* ``disable_virtual_memory``: Hide the VIRT column (\`[processlist] disable\_virtual\_memory\`). (unit is *boolean*)

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
    ['python', 'irq/9-acpi', 'firefox', 'systemd-logind',
     'kworker/4:2-mm_percpu_wq', 'kworker/u64:9-events_unbound', 'Isolated Web Co',
     'WebExtensions', 'gnome-shell', 'Scratch', 'kworker/6:2-events', 'multipassd',
     'Privileged Cont', 'WebKitWebProcess', 'RDD Process', 'dropbox', 'Web Content',
     'terminator', 'gjs', 'Utility Process', 'snapd', 'Socket Process',
     'localsearch-3', 'dockerd', 'uv', 'tailscaled', 'fwupd', 'forkserver',
     'systemd-journald', 'evolution-calendar-factory', 'python3', 'cups-browsed',
     'NetworkManager', 'WebKitNetworkProcess', 'ollama', 'cupsd', 'pipewire-pulse',
     'containerd', 'systemd', 'snap', 'pipewire', 'evolution-alarm-notify',
     'update-notifier', 'evolution-source-registry', 'snap-store', 'wireplumber',
     'goa-daemon', 'polkitd', 'systemd-udevd', 'xdg-desktop-portal-gnome',
     '(udev-worker)', 'gnome-shell-calendar-server', 'wpa_supplicant',
     'dbus-daemon', 'libvirtd', 'sleep', 'xdg-desktop-portal',
     'snapd-desktop-integration', 'colord', 'udisksd', 'gvfsd-recent',
     'xdg-desktop-portal-gtk', 'zed', 'gvfs-udisks2-volume-monitor', 'gsd-power',
     'Xwayland', 'glycin-image-rs', 'ibus-extension-gtk3', 'dart:firmware-n',
     'gnome-keyring-daemon', 'upowerd', 'gsd-sharing', 'ModemManager',
     'gdm-session-worker', 'gsd-media-keys', 'gvfsd-trash', 'speech-dispatcher',
     'mutter-x11-frames', 'xdg-document-portal', 'rsyslogd',
     'gnome-session-service', 'evolution-addressbook-factory', 'ibus-x11', 'bash',
     'gsd-disk-utility-notify', 'gsd-housekeeping', 'systemd-resolved', 'gdm3',
     'gsd-xsettings', 'switcheroo-control', 'iio-sensor-proxy', 'bluetoothd',
     'cups-proxyd', 'gsd-print-notifications', 'gvfsd-metadata', 'sd_espeak-ng',
     'gvfs-mtp-volume-monitor', 'gvfsd-wsdd', 'accounts-daemon', 'gsd-printer',
     'gvfsd', 'ibus-daemon', 'dconf-service', 'gvfs-gphoto2-volume-monitor',
     'gsd-usb-protection', 'gvfsd-dnssd', 'boltd', 'make', 'gsd-color',
     'systemd-timesyncd', 'crashhelper', 'ibus-engine-simple', 'gvfsd-network',
     'gcr-ssh-agent', 'systemd-machined', 'gvfs-afc-volume-monitor', 'gsd-wwan',
     'ssh-agent', 'gsd-keyboard', 'gsd-sound', 'gsd-rfkill', 'gsd-smartcard',
     'gsd-datetime', 'dnsmasq', 'at-spi2-registryd', 'at-spi-bus-launcher',
     'ibus-portal', 'gvfs-goa-volume-monitor', 'gsd-screensaver-proxy',
     'gsd-a11y-settings', 'goa-identity-service', 'bwrap', 'xdg-permission-store',
     'snmpd', 'thermald', 'systemd-oomd', 'rtkit-daemon', 'gvfsd-http',
     'avahi-daemon', 'ibus-memconf', 'sh', 'gdm-wayland-session', 'gvfsd-fuse',
     'gnome-session-init-worker', 'smartd', 'mpris-proxy', 'unattended-upgr',
     'sd_dummy', 'run-cups-browse', 'cron', 'uuidd', 'fsidd', 'virtlogd',
     'rpc.idmapd', 'nfsdcld', 'virtlockd', 'rpcbind', 'gnome-session-ctl',
     'user-session-helper', 'rpc.mountd', 'rpc.statd', '(sd-pam)', 'run-cupsd',
     'fusermount3', 'kthreadd', 'pool_workqueue_release', 'kworker/R-rcu_gp',
     'kworker/R-sync_wq', 'kworker/R-kvfree_rcu_reclaim', 'kworker/R-slub_flushwq',
     'kworker/R-netns', 'kworker/0:0H-kblockd', 'kworker/R-mm_percpu_wq',
     'ksoftirqd/0', 'rcu_preempt', 'rcu_exp_par_gp_kthread_worker/0',
     'rcu_exp_gp_kthread_worker', 'migration/0', 'kprobe-optimizer',
     'idle_inject/0', 'cpuhp/0', 'cpuhp/2', 'idle_inject/2', 'migration/2',
     'ksoftirqd/2', 'kworker/2:0H-kblockd', 'cpuhp/4', 'idle_inject/4',
     'migration/4', 'ksoftirqd/4', 'kworker/4:0H-kblockd', 'cpuhp/6',
     'idle_inject/6', 'migration/6', 'ksoftirqd/6', 'kworker/6:0H-kblockd',
     'cpuhp/8', 'idle_inject/8', 'migration/8', 'ksoftirqd/8',
     'kworker/8:0H-kblockd', 'cpuhp/10', 'idle_inject/10', 'migration/10',
     'ksoftirqd/10', 'kworker/10:0H-kblockd', 'cpuhp/12', 'idle_inject/12',
     'migration/12', 'ksoftirqd/12', 'kworker/12:0H-kblockd', 'cpuhp/13',
     'idle_inject/13', 'migration/13', 'ksoftirqd/13', 'kworker/13:0H-kblockd',
     'cpuhp/14', 'idle_inject/14', 'migration/14', 'ksoftirqd/14',
     'kworker/14:0H-kblockd', 'cpuhp/15', 'idle_inject/15', 'migration/15',
     'ksoftirqd/15', 'kworker/15:0H-kblockd', 'cpuhp/1', 'idle_inject/1',
     'migration/1', 'ksoftirqd/1', 'kworker/1:0H-kblockd', 'cpuhp/3',
     'idle_inject/3', 'migration/3', 'ksoftirqd/3', 'kworker/3:0H-kblockd',
     'cpuhp/5', 'idle_inject/5', 'migration/5', 'ksoftirqd/5',
     'kworker/5:0H-kblockd', 'cpuhp/7', 'idle_inject/7', 'migration/7',
     'ksoftirqd/7', 'kworker/7:0H-kblockd', 'cpuhp/9', 'idle_inject/9',
     'migration/9', 'ksoftirqd/9', 'kworker/9:0H-kblockd', 'cpuhp/11',
     'idle_inject/11', 'migration/11', 'ksoftirqd/11', 'kworker/11:0H-kblockd',
     'kdevtmpfs', 'kworker/R-inet_frag_wq', 'rcu_tasks_kthread',
     'rcu_tasks_rude_kthread', 'kauditd', 'khungtaskd', 'oom_reaper',
     'kworker/R-writeback', 'kcompactd0', 'ksmd', 'khugepaged', 'kworker/R-kblockd',
     'kworker/R-blkcg_punt_bio', 'kworker/R-kintegrityd', 'kworker/R-tpm_dev_wq',
     'kworker/R-ata_sff', 'kworker/R-md_bitmap', 'kworker/R-md_llbitmap_io',
     'kworker/R-md_llbitmap_unplug', 'kworker/R-edac-poller',
     'kworker/R-devfreq_wq', 'watchdogd', 'kworker/R-quota_events_unbound',
     'kswapd0', 'ecryptfs-kthread', 'kworker/R-kthrotld', 'irq/123-pciehp',
     'irq/124-pciehp', 'kworker/R-acpi_thermal_pm', 'hwrng',
     'kworker/R-hfi-updates', 'kworker/R-mld', 'kworker/R-ipv6_addrconf',
     'kworker/R-kstrp', 'kworker/R-charger_manager', 'irq/178-VEN_04F3:00', 'spi0',
     'kworker/R-nvme-wq', 'kworker/R-nvme-reset-wq', 'kworker/R-nvme-delete-wq',
     'kworker/R-nvme-auth-wq', 'kworker/R-USBC000:00-con1',
     'kworker/R-USBC000:00-con2', 'kworker/R-USBC000:00-con3',
     'kworker/R-kdmflush/252:0', 'kworker/R-kcryptd_io-252:0-1',
     'kworker/R-kcryptd-252:0-1', 'dmcrypt_write/252:0',
     'kworker/2:1H-i915_cleanup', 'kworker/R-kdmflush/252:1',
     'kworker/0:1H-kblockd', 'kworker/12:1H-kblockd', 'kworker/11:1H-kblockd',
     'kworker/6:1H-i915_cleanup', 'kworker/15:1H-i915_cleanup',
     'kworker/1:1H-i915_cleanup', 'kworker/7:1H-i915_cleanup',
     'kworker/10:1H-kblockd', 'kworker/5:1H-kblockd', 'jbd2/dm-1-8',
     'kworker/R-ext4-rsv-conversion', 'kworker/4:1H-kblockd',
     'kworker/14:1H-i915_cleanup', 'kworker/8:1H-i915_cleanup',
     'kworker/9:1H-kblockd', 'psimon', 'kworker/13:1H-i915_cleanup',
     'kworker/3:1H-i915_cleanup', 'irq/16-processor_thermal_device_pci',
     'kworker/R-ttm', 'kworker/R-cfg80211', 'jbd2/nvme0n1p2-8', 'card1-crtc0',
     'card1-crtc1', 'card1-crtc2', 'card1-crtc3', 'irq/200-iwlwifi:default_queue',
     'irq/201-iwlwifi:queue_1', 'irq/202-iwlwifi:queue_2',
     'irq/203-iwlwifi:queue_3', 'irq/204-iwlwifi:queue_4',
     'irq/205-iwlwifi:queue_5', 'irq/206-iwlwifi:queue_6',
     'irq/207-iwlwifi:queue_7', 'irq/208-iwlwifi:queue_8',
     'irq/209-iwlwifi:queue_9', 'irq/210-iwlwifi:queue_10',
     'irq/211-iwlwifi:queue_11', 'irq/212-iwlwifi:queue_12',
     'irq/213-iwlwifi:queue_13', 'irq/214-iwlwifi:queue_14',
     'irq/215-iwlwifi:exception', 'kworker/R-rpciod', 'kworker/R-xprtiod',
     'irq/217-mei_gsc', 'irq/218-mei_gsc', 'irq/197-cs35l41 IRQ1 Controller',
     'irq/233-AudioDSP', 'spl_system_task', 'spl_delay_taskq', 'spl_dynamic_tas',
     'spl_kmem_cache', 'zvol_tq-0', 'zvol_tq-1', 'zvol_tq-2', 'arc_prune',
     'arc_evict', 'arc_flush', 'arc_reap', 'dbu_evict', 'dbuf_evict', 'z_vdev_file',
     'l2arc_feed', 'lockd', 'nfsd', 'krfcommd', 'sd_espeak-ng-mb',
     'kworker/14:2-mm_percpu_wq', 'kworker/5:2-mm_percpu_wq',
     'kworker/u64:15-kcryptd-252:0-1', 'kworker/15:2-events',
     'kworker/u64:8-kcryptd-252:0-1', 'kworker/13:1-mm_percpu_wq',
     'kworker/3:2-mm_percpu_wq', 'irq/198-mei_me', 'kworker/u65:0-rb_allocator',
     'kworker/11:2-mm_percpu_wq', 'kworker/u64:0-kcryptd-252:0-1',
     'kworker/u64:4-kcryptd-252:0-1', 'kworker/0:2-events', 'kworker/3:0',
     'kworker/5:1', 'kworker/u64:6-kcryptd-252:0-1', 'kworker/11:1',
     'kworker/10:0-events', 'kworker/13:0-mm_percpu_wq', 'kworker/12:0-events',
     'kworker/u64:10-kcryptd-252:0-1', 'kworker/10:2-mm_percpu_wq',
     'kworker/u64:2-kcryptd-252:0-1', 'kworker/u64:5-kcryptd-252:0-1',
     'kworker/u64:13-kcryptd-252:0-1', 'kworker/u64:14-kcryptd-252:0-1',
     'kworker/15:1-events', 'kworker/0:0-events', 'kworker/8:0-events',
     'kworker/2:1-cgroup_release', 'kworker/9:1-mm_percpu_wq', 'kworker/1:1-events',
     'kworker/8:1-events', 'kworker/7:0-events', 'kworker/7:4-i915-unordered',
     'kworker/6:0-mm_percpu_wq', 'kworker/2:0-cgroup_release',
     'kworker/u65:2-rb_allocator', 'kworker/u64:1-kcryptd-252:0-1',
     'kworker/12:2-events', 'kworker/1:0-events', 'kworker/9:0-mm_percpu_wq',
     'kworker/u64:16-kcryptd-252:0-1', 'kworker/14:0', 'kworker/8:3-events',
     'kworker/4:0', 'kworker/10:1-events', 'kworker/0:1-events', 'kworker/13:2',
     'kworker/1:2-events', 'kworker/u65:1-rb_allocator', 'kworker/6:1',
     'kworker/7:1-i915-unordered', 'kworker/5:0-mm_percpu_wq', 'kworker/8:2-events',
     'kworker/u64:3-kcryptd-252:0-1', 'kworker/u65:3-rb_allocator',
     'kworker/u64:7-kcryptd-252:0-1', 'kworker/2:2-mm_percpu_wq']
    >>> gl.programlist['python']
    {'cmdline': ['python'],
     'cpu_percent': 66.5,
     'cpu_times': {'children_system': 0.03,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.57,
                   'user': 0.81},
     'io_counters': [36933632, 794624, 36933632, 794624, 1],
     'memory_info': {'data': 125710336,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 89100288,
                     'shared': 25690112,
                     'text': 31211520,
                     'vms': 669437952},
     'memory_percent': 0.5610823501130134,
     'name': 'python',
     'nice': 0,
     'nprocs': 1,
     'num_threads': 7,
     'status': 'S',
     'time_since_update': 0.815732479095459,
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
* ``disable_virtual_memory``: Hide the VIRT column (\`[processlist] disable\_virtual\_memory\`). (unit is *boolean*)

Programlist limits:

.. code-block:: python

    >>> gl.programlist.limits
    {'cpu_percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0},
     'memory_percent': {'careful': 50.0, 'critical': 90.0, 'warning': 70.0}}

Glances psutilversion
---------------------

.. code-block:: python

    >>> gl.psutilversion
    {'time_since_update': 0.812858151999535, 'version': '7.2.2'}

Psutilversion fields:

* ``version``: psutil version. (unit is *string*)

Glances quicklook
-----------------

.. code-block:: python

    >>> gl.quicklook
    {'bar_char': '▪',
     'cpu': 5.2,
     'cpu_hz': 4475000000,
     'cpu_hz_current': 695126687,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'gpu_proc': 0.5,
     'load': 6.3,
     'max_cpu_display': 4,
     'mem': 44.5,
     'percpu': [{'cpu_number': 0, 'level': 'ok', 'total': 3.8},
                {'cpu_number': 1, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 2, 'level': 'ok', 'total': 1.9},
                {'cpu_number': 3, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 4, 'level': 'careful', 'total': 55.6},
                {'cpu_number': 5, 'level': 'ok', 'total': 1.9},
                {'cpu_number': 6, 'level': 'ok', 'total': 5.7},
                {'cpu_number': 7, 'level': 'ok', 'total': 1.9},
                {'cpu_number': 8, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 9, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 10, 'level': 'ok', 'total': 3.8},
                {'cpu_number': 11, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 12, 'level': 'ok', 'total': 1.9},
                {'cpu_number': 13, 'level': 'ok', 'total': 5.7},
                {'cpu_number': 14, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 15, 'level': 'ok', 'total': 1.9}],
     'percpu_other': {'level': 'ok', 'total': 1.1083333333333332},
     'stats_list': ['cpu', 'mem', 'load'],
     'swap': 31.5,
     'time_since_update': 0.8124930370031507}

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
     'value': 33,
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
     'time_since_update': 0.4018429690040648}

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
    {'seconds': 1095017, 'time_since_update': 0.40252667700406164}

Uptime fields:

* ``seconds``: Seconds elapsed since the system booted. (unit is *seconds*)

Glances version
---------------

.. code-block:: python

    >>> gl.version
    {'time_since_update': 0.40301509400160285, 'version': '5.0.0b2'}

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
    '6.58G'

A percentage as a text bar:

.. code-block:: python

    >>> gl.bar(gl.mem["percent"])
    '■■■■■■■■□□□□□□□□□□'

The top processes (the API's own process is left out):

.. code-block:: python

    >>> gl.top_process()
    [{'cpu_percent': 2.5,
      'memory_percent': 5.73968698759934,
      'name': 'firefox',
      'pid': 713185},
     {'cpu_percent': 1.3,
      'memory_percent': 0.03616225140709074,
      'name': 'systemd-logind',
      'pid': 3138},
     {'cpu_percent': 1.2,
      'memory_percent': 6.9205573113649805,
      'name': 'Isolated Web Co',
      'pid': 713550}]

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
