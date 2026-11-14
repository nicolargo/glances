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
     'iowait': 0.8,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 3.3,
     'time_since_update': 0.4468085649996283,
     'total': 6.7,
     'user': 2.5}
    >>> gl.cpu["total"]
    6.7
    >>> gl.mem["used"]
    9208840192
    >>> gl.auto_unit(gl.mem["used"])
    '8.58G'
    >>> gl.network.keys()
    ['wlp0s20f3', 'tailscale0']
    >>> gl.network["wlp0s20f3"]
    {'bytes_recv': 795.0019089062059,
     'bytes_recv_cumul': 877594189,
     'bytes_sent': 735.6734082415637,
     'bytes_sent_cumul': 33502427,
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
     'timer': 0.5018563270568848}

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
    {'log': 16, 'phys': 10, 'time_since_update': 0.45157768900025985}

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
     'iowait': 0.8,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 3.3,
     'time_since_update': 0.4468085649996283,
     'total': 6.7,
     'user': 2.5}

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
     'read_bytes': 0.0,
     'read_bytes_cumul': 14945772544,
     'read_count': 0.0,
     'read_count_cumul': 762974,
     'read_latency': 0,
     'read_time': 0.0,
     'write_bytes': 0.0,
     'write_bytes_cumul': 18132812800,
     'write_count': 0.0,
     'write_count_cumul': 798366,
     'write_latency': 0,
     'write_time': 0.0}

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
    ['/', '/zsfpool']
    >>> gl.fs['/']
    {'device_name': '/dev/mapper/ubuntu--vg-ubuntu--lv',
     'free': 436907360256,
     'fs_type': 'ext4',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 54.1,
     'size': 1003736440832,
     'used': 515766575104}

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
     'time_since_update': 0.43195821500012244}

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
     'min1': 0.68212890625,
     'min15': 2.609375,
     'min5': 1.57568359375,
     'time_since_update': 0.43217602700042335}

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
    {'active': 4537454592,
     'available': 6671228928,
     'buffers': 325537792,
     'cached': 7660734824,
     'free': 932929536,
     'inactive': 7432122368,
     'percent': 58.0,
     'shared': 2120863744,
     'slab': 2016624640,
     'time_since_update': 0.42427428900009545,
     'total': 15880069120,
     'used': 9208840192}

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
    {'free': 3266539520,
     'percent': 23.9,
     'sin': 0.0,
     'sout': 0.0,
     'time_since_update': 0.4320532990004722,
     'total': 4294963200,
     'used': 1028423680}

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
    {'bytes_recv': 795.0019089062059,
     'bytes_recv_cumul': 877594189,
     'bytes_sent': 735.6734082415637,
     'bytes_sent_cumul': 33502427,
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
    {'custom': '2026-11-14 10:40:39 CET',
     'iso': '2026-11-14T10:40:39+01:00',
     'time_since_update': 0.4310274979998212}

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
     'status': 0.006269,
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
     'sleeping': 430,
     'sort_key': 'cpu_percent',
     'thread': 2093,
     'time_since_update': 0.41471945099965524,
     'total': 586}

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
    [119547, 134479, 129, 10039, 120799, 38731, 39031, 38359, 38746, 119317, 120490,
     38724, 119446, 16232, 119227, 115828, 10432, 10448, 119521, 38672, 119568,
     119567, 107329, 120177, 40702, 38681, 120621, 120601, 119260, 11297, 131906,
     133429, 132610, 11305, 120292, 3695, 120294, 120293, 10234, 119229, 119230,
     612, 4300, 10410, 10428, 11784, 3342, 10133, 10467, 39460, 11316, 4307, 134476,
     38654, 47611, 120296, 10214, 38820, 4313, 38651, 10336, 10535, 120348, 10352,
     3734, 11623, 3715, 10340, 44333, 3713, 10122, 14692, 3459, 10144, 9510, 11303,
     1, 3363, 3745, 658, 3364, 3369, 9449, 3327, 683, 3590, 10177, 9494, 10172,
     3660, 12087, 9517, 11276, 10330, 3462, 10191, 47586, 14688, 10506, 9224, 10024,
     10166, 51917, 10174, 36584, 10167, 4440, 9499, 10238, 10164, 47588, 47600,
     3353, 71873, 10217, 10165, 11244, 4323, 3307, 10211, 10204, 9746, 10588, 10426,
     3346, 10199, 10162, 3316, 10418, 3355, 10015, 651, 115862, 3592, 10613, 9625,
     3348, 10557, 10179, 98868, 10169, 9999, 4072, 127418, 10081, 10356, 10594,
     10021, 3306, 10345, 10090, 10579, 655, 10181, 4073, 9493, 42429, 120212, 43809,
     9696, 9629, 119738, 40884, 10127, 10001, 7993, 120059, 3463, 3337, 10000,
     10088, 3305, 9513, 9501, 9472, 119245, 3132, 48074, 3311, 4833, 4311, 134472,
     3679, 38545, 16596, 4310, 115844, 71870, 9636, 4326, 3707, 134475, 3704, 4528,
     4316, 71872, 115861, 3421, 4249, 12015, 4529, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14,
     15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 30, 31, 33, 34, 35, 36,
     37, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 57, 58, 59, 60,
     61, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 75, 76, 77, 78, 79, 81, 82, 83,
     84, 85, 87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 99, 100, 101, 102, 103, 105,
     106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 121, 122, 123,
     124, 125, 126, 127, 133, 134, 135, 136, 137, 138, 139, 140, 141, 143, 144, 145,
     146, 147, 148, 152, 155, 156, 157, 158, 178, 261, 264, 267, 268, 269, 270, 275,
     321, 322, 323, 485, 486, 487, 488, 497, 523, 524, 525, 526, 529, 532, 533, 641,
     652, 654, 677, 681, 685, 736, 737, 740, 813, 815, 816, 817, 818, 819, 820, 821,
     822, 823, 824, 825, 826, 827, 828, 829, 830, 834, 944, 988, 989, 990, 992,
     1246, 1253, 1254, 1264, 1265, 1451, 1486, 1578, 1585, 2270, 2301, 2302, 2303,
     2304, 2305, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316, 2317,
     2318, 2319, 2320, 2321, 2350, 2352, 2353, 2354, 2355, 2356, 2357, 2358, 2359,
     2388, 2389, 2390, 2391, 2392, 2393, 2394, 2395, 2396, 2397, 2398, 2399, 2400,
     2401, 2402, 2403, 2404, 2405, 2406, 2407, 2408, 2409, 2410, 2411, 2412, 2415,
     2416, 2417, 2418, 2419, 2420, 2421, 2422, 2423, 2424, 2425, 2426, 2427, 2428,
     2429, 2430, 2431, 2432, 2433, 2434, 2435, 2436, 2437, 2438, 2439, 2440, 2441,
     2453, 2454, 2455, 2456, 2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469,
     2470, 2471, 2472, 2473, 2474, 2475, 2476, 2477, 2478, 2479, 2480, 2481, 2483,
     2484, 2485, 2486, 2487, 2488, 2489, 2511, 2518, 4283, 4385, 4602, 4605, 4606,
     4610, 4611, 4612, 4615, 4616, 4617, 4621, 4622, 4623, 4627, 4628, 4629, 4631,
     5424, 7832, 36577, 46578, 46612, 47161, 62099, 86202, 98866, 99885, 102867,
     103046, 104514, 105564, 105581, 106166, 106170, 106456, 106613, 106622, 106674,
     106694, 106736, 108062, 108067, 108533, 110122, 110227, 113063, 114045, 116354,
     116917, 117977, 120801, 122458, 122465, 122839, 127533, 127677, 128625, 129363,
     129413, 129824, 129836, 130198, 130284, 130285, 130286, 130447, 130448, 130449,
     130450, 131072, 131905, 132353, 132529, 132827, 133301, 134278]
    >>> gl.processlist[119547]
    {'cmdline': ['/snap/code/267/usr/share/code/code',
                 '--type=utility',
                 '--utility-sub-type=node.mojom.NodeService',
                 '--lang=en-US',
                 '--service-sandbox-type=none',
                 '--no-sandbox',
                 '--dns-result-order=ipv4first',
                 '--experimental-network-inspection',
                 '--inspect-port=0',
                 '--crashpad-handler-pid=119245',
                 '--enable-crash-reporter=864d4bb7-dd20-4851-830f-29e81dd93517,no_channel',
                 '--user-data-dir=/home/nicolargo/.config/Code',
                 '--standard-schemes=vscode-webview,vscode-file',
                 '--secure-schemes=vscode-webview,vscode-file,vscode-remote-resource,vscode-managed-remote-resource',
                 '--cors-schemes=vscode-webview,vscode-file,vscode-remote-resource,vscode-managed-remote-resource',
                 '--fetch-schemes=vscode-webview,vscode-file,vscode-remote-resource,vscode-managed-remote-resource',
                 '--service-worker-schemes=vscode-webview',
                 '--code-cache-schemes=vscode-webview,vscode-file',
                 '--shared-files=v8_context_snapshot_data:100',
                 '--field-trial-handle=3,i,1878308425939312504,7864207901725785798,262144',
                 '--enable-features=DocumentPolicyIncludeJSCallStacksInCrashReports,EarlyEstablishGpuChannel,EstablishGpuChannelAsync,GlobalShortcutsPortal,GlobalShortcutsPortalPreferredTrigger,PdfUseShowSaveFilePicker',
                 '--disable-features=CalculateNativeWinOcclusion,DropInputEventsWhilePaintHolding,HideCursorWhileTyping,LocalNetworkAccessChecks,ScreenAIOCREnabled,SpareRendererForSitePerProcess,TraceSiteInstanceGetProcessCreation',
                 '--variations-seed-version',
                 '--pseudonymization-salt-handle=7,i,12722428090919659955,2873085837061125516,4',
                 '--trace-process-track-uuid=3190708995682289984'],
     'cpu_num': 10,
     'cpu_percent': 115.3,
     'cpu_times': {'children_system': 9.13,
                   'children_user': 4.67,
                   'iowait': 0.0,
                   'system': 5.25,
                   'user': 20.35},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [393436160, 52043776, 393436160, 52043776, 1],
     'key': 'pid',
     'memory_info': {'data': 1649942528,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 789004288,
                     'shared': 154095616,
                     'text': 163037184,
                     'vms': 1554998202368},
     'memory_percent': 4.9685192302236025,
     'name': 'code',
     'nice': 0,
     'num_threads': 36,
     'pid': 119547,
     'status': 'S',
     'time_since_update': 0.4304656982421875,
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
    ['code', 'python', 'irq/9-acpi', 'gnome-shell', 'kworker/u64:13-events_unbound',
     'Isolated Web Co', 'WebExtensions', 'firefox', 'multipassd', 'loupe',
     'dropbox', 'Xwayland', 'Privileged Cont', 'gjs', 'terminator', 'RDD Process',
     'mutter-x11-frames', 'Web Content', 'ibus-x11', 'python3',
     'evolution-alarm-notify', 'systemd-journald', 'dockerd', 'snap-store',
     'localsearch-3', 'fwupd', 'snapd', 'evolution-source-registry',
     'evolution-calendar-factory', 'Utility Process', 'xdg-desktop-portal-gnome',
     'ollama', 'uv', 'Socket Process', 'copilot-runtime', 'update-notifier', 'snap',
     'libvirtd', 'forkserver', 'goa-daemon', 'evolution-addressbook-factory',
     'ruff', 'ibus-extension-gtk3', 'containerd', 'xdg-desktop-portal-gtk',
     'unattended-upgr', 'tailscaled', 'gnome-shell-calendar-server', 'cups-browsed',
     'NetworkManager', 'wireplumber', 'xdg-desktop-portal', 'systemd', 'udisksd',
     'colord', 'systemd-udevd', 'virtlockd', 'virtlogd', 'polkitd',
     'systemd-resolved', 'ModemManager', 'gsd-print-notifications', 'pipewire',
     'gsd-media-keys', 'upowerd', 'snapd-desktop-integration', 'pipewire-pulse',
     'gsd-xsettings', 'gsd-printer', 'wpa_supplicant', 'gsd-sharing',
     'gvfsd-recent', 'cupsd', 'gvfs-udisks2-volume-monitor', 'gdm-session-worker',
     'gnome-session-service', 'gsd-datetime', 'gvfsd-http', 'gsd-power', 'snmpd',
     'gsd-housekeeping', 'gdm3', 'gnome-keyring-daemon', 'gsd-disk-utility-notify',
     'gsd-a11y-settings', 'gvfsd-network', 'gvfsd-dnssd', 'systemd-logind',
     'glycin-image-rs', 'gsd-wwan', 'gsd-color', 'gvfsd-trash', 'thermald',
     'dbus-daemon', 'gsd-usb-protection', 'gsd-sound', 'gnome-session-init-worker',
     'gvfs-afc-volume-monitor', 'goa-identity-service', 'accounts-daemon',
     'gsd-smartcard', 'ibus-daemon', 'iio-sensor-proxy', 'gvfsd-metadata',
     'systemd-machined', 'gvfsd', 'systemd-timesyncd', 'boltd',
     'ibus-engine-simple', 'xdg-document-portal', 'switcheroo-control',
     'gvfs-gphoto2-volume-monitor', 'gsd-rfkill', 'sleep', 'gsd-keyboard',
     'gcr-ssh-agent', 'bash', 'at-spi-bus-launcher', 'ibus-portal',
     'gvfs-mtp-volume-monitor', 'gvfsd-fuse', 'bluetoothd', 'ibus-memconf',
     'at-spi2-registryd', 'gvfs-goa-volume-monitor', 'systemd-oomd',
     'gsd-screensaver-proxy', 'cups-proxyd', 'ssh-agent', 'gdm-wayland-session',
     'xdg-permission-store', 'dconf', 'dconf-service', 'zed', 'pet', 'rsyslogd',
     'smartd', 'gnome-session-ctl', 'avahi-daemon', 'mpris-proxy', '(sd-pam)',
     'chrome_crashpad_handler', 'rpcbind', 'uuidd', 'fsidd', 'rtkit-daemon', 'cron',
     'make', 'nfsdcld', 'crashhelper', 'dnsmasq', 'rpc.idmapd', 'bwrap',
     'fusermount3', 'rpc.statd', 'run-cupsd', 'sh', 'run-cups-browse', 'rpc.mountd',
     'user-session-helper', 'kthreadd', 'pool_workqueue_release',
     'kworker/R-rcu_gp', 'kworker/R-sync_wq', 'kworker/R-kvfree_rcu_reclaim',
     'kworker/R-slub_flushwq', 'kworker/R-netns', 'kworker/0:0H-kblockd',
     'kworker/R-mm_percpu_wq', 'ksoftirqd/0', 'rcu_preempt',
     'rcu_exp_par_gp_kthread_worker/0', 'rcu_exp_gp_kthread_worker', 'migration/0',
     'kprobe-optimizer', 'idle_inject/0', 'cpuhp/0', 'cpuhp/2', 'idle_inject/2',
     'migration/2', 'ksoftirqd/2', 'kworker/2:0H-kblockd', 'cpuhp/4',
     'idle_inject/4', 'migration/4', 'ksoftirqd/4', 'kworker/4:0H-kblockd',
     'cpuhp/6', 'idle_inject/6', 'migration/6', 'ksoftirqd/6',
     'kworker/6:0H-i915_cleanup', 'cpuhp/8', 'idle_inject/8', 'migration/8',
     'ksoftirqd/8', 'kworker/8:0H-kblockd', 'cpuhp/10', 'idle_inject/10',
     'migration/10', 'ksoftirqd/10', 'kworker/10:0H-kblockd', 'cpuhp/12',
     'idle_inject/12', 'migration/12', 'ksoftirqd/12', 'kworker/12:0H-kblockd',
     'cpuhp/13', 'idle_inject/13', 'migration/13', 'ksoftirqd/13',
     'kworker/13:0H-kblockd', 'cpuhp/14', 'idle_inject/14', 'migration/14',
     'ksoftirqd/14', 'kworker/14:0-events', 'kworker/14:0H-kblockd', 'cpuhp/15',
     'idle_inject/15', 'migration/15', 'ksoftirqd/15', 'kworker/15:0H-kblockd',
     'cpuhp/1', 'idle_inject/1', 'migration/1', 'ksoftirqd/1',
     'kworker/1:0H-kblockd', 'cpuhp/3', 'idle_inject/3', 'migration/3',
     'ksoftirqd/3', 'kworker/3:0H-kblockd', 'cpuhp/5', 'idle_inject/5',
     'migration/5', 'ksoftirqd/5', 'kworker/5:0H-kblockd', 'cpuhp/7',
     'idle_inject/7', 'migration/7', 'ksoftirqd/7', 'kworker/7:0H-kblockd',
     'cpuhp/9', 'idle_inject/9', 'migration/9', 'ksoftirqd/9',
     'kworker/9:0H-kblockd', 'cpuhp/11', 'idle_inject/11', 'migration/11',
     'ksoftirqd/11', 'kworker/11:0-mm_percpu_wq', 'kworker/11:0H-kblockd',
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
     'kworker/7:1H-kblockd', 'kworker/R-kdmflush/252:0',
     'kworker/R-kcryptd_io-252:0-1', 'kworker/R-kcryptd-252:0-1',
     'dmcrypt_write/252:0', 'kworker/R-kdmflush/252:1',
     'kworker/14:1H-i915_cleanup', 'kworker/13:1H-i915_cleanup',
     'kworker/11:1H-kblockd', 'kworker/5:1H-i915_cleanup',
     'kworker/4:1H-i915_cleanup', 'jbd2/dm-1-8', 'kworker/R-ext4-rsv-conversion',
     'kworker/1:1H-kblockd', 'kworker/15:1H-i915_cleanup', 'kworker/3:1H-kblockd',
     'kworker/12:1H-i915_cleanup', 'kworker/2:1H-kblockd', 'psimon',
     'kworker/9:1H-i915_cleanup', 'kworker/8:1H-i915_cleanup',
     'kworker/10:1H-i915_cleanup', 'kworker/R-cfg80211',
     'irq/197-iwlwifi:default_queue', 'irq/198-iwlwifi:queue_1',
     'irq/199-iwlwifi:queue_2', 'irq/200-iwlwifi:queue_3',
     'irq/201-iwlwifi:queue_4', 'irq/202-iwlwifi:queue_5',
     'irq/203-iwlwifi:queue_6', 'irq/204-iwlwifi:queue_7',
     'irq/205-iwlwifi:queue_8', 'irq/206-iwlwifi:queue_9',
     'irq/207-iwlwifi:queue_10', 'irq/208-iwlwifi:queue_11',
     'irq/209-iwlwifi:queue_12', 'irq/210-iwlwifi:queue_13',
     'irq/211-iwlwifi:queue_14', 'irq/212-iwlwifi:exception',
     'irq/16-processor_thermal_device_pci', 'kworker/R-ttm', 'card1-crtc0',
     'card1-crtc1', 'card1-crtc2', 'card1-crtc3', 'jbd2/nvme0n1p2-8',
     'kworker/R-rpciod', 'kworker/R-xprtiod', 'irq/213-cs35l41 IRQ1 Controller',
     'irq/217-mei_gsc', 'irq/218-mei_gsc', 'irq/233-AudioDSP', 'spl_system_task',
     'spl_delay_taskq', 'spl_dynamic_tas', 'spl_kmem_cache',
     'kworker/6:1H-i915_cleanup', 'zvol_tq-0', 'zvol_tq-1', 'zvol_tq-2',
     'arc_prune', 'arc_evict', 'arc_flush', 'arc_reap', 'dbu_evict', 'dbuf_evict',
     'z_vdev_file', 'l2arc_feed', 'z_null_iss', 'z_null_int', 'z_rd_iss',
     'z_rd_int_0', 'z_rd_int_1', 'z_rd_int_2', 'z_wr_iss', 'z_wr_int_0',
     'z_wr_int_1', 'z_wr_int_2', 'z_fr_iss_0', 'z_fr_iss_1', 'z_fr_iss_2',
     'z_fr_iss_3', 'z_fr_int', 'z_cl_iss', 'z_cl_int', 'z_flush_iss', 'z_flush_int',
     'z_trim_iss', 'z_trim_int', 'z_zvol', 'z_metaslab', 'z_prefetch', 'z_upgrade',
     'dp_sync_taskq', 'dp_zil_clean_ta', 'z_zrele', 'z_unlinked_drai',
     'txg_quiesce', 'txg_sync', 'mmp', 'raidz_expand', 'z_indirect_cond',
     'z_livelist_dest', 'z_livelist_cond', 'z_checkpoint_di',
     'kworker/0:1H-i915_cleanup', 'kworker/u64:11-kcryptd-252:0-1', 'lockd', 'nfsd',
     'krfcommd', 'irq/214-mei_me', 'kworker/u65:0-i915_flip', 'kworker/4:2-events',
     'kworker/u64:4-kcryptd-252:0-1', 'kworker/15:0-events',
     'kworker/u65:3-rb_allocator', 'kworker/9:2-mm_percpu_wq', 'kworker/6:1-events',
     'kworker/u64:0-kcryptd-252:0-1', 'kworker/6:0-memcg',
     'kworker/10:1-mm_percpu_wq', 'kworker/0:2-events', 'kworker/2:2-events',
     'kworker/u64:1-kcryptd-252:0-1', 'kworker/9:1-mm_percpu_wq',
     'kworker/5:2-events', 'kworker/u64:5-kcryptd-252:0-1',
     'kworker/u64:6-kcryptd-252:0-1', 'kworker/13:1-mm_percpu_wq',
     'kworker/1:0-events', 'kworker/15:2-mm_percpu_wq', 'kworker/8:0-events',
     'kworker/14:2-mm_percpu_wq', 'kworker/11:2-events',
     'kworker/12:0-mm_percpu_wq', 'kworker/u64:10-kcryptd-252:0-1',
     'kworker/4:0-cgroup_offline', 'kworker/0:1-mm_percpu_wq',
     'kworker/7:2-mm_percpu_wq', 'kworker/2:0-events', 'kworker/3:1-mm_percpu_wq',
     'kworker/u64:16-events_unbound', 'kworker/13:0-mm_percpu_wq',
     'kworker/1:2-events', 'kworker/10:3-events', 'kworker/5:1-events',
     'kworker/12:2-cgroup_free', 'kworker/7:0-events', 'kworker/3:0-mm_percpu_wq',
     'kworker/8:1-events', 'kworker/u65:1-rb_allocator', 'kworker/0:0-events',
     'kworker/u64:2-kcryptd-252:0-1', 'kworker/u64:3-kcryptd-252:0-1',
     'kworker/u64:7-kcryptd-252:0-1', 'kworker/u64:8-kcryptd-252:0-1',
     'kworker/u64:9-kcryptd-252:0-1', 'kworker/u64:12-kcryptd-252:0-1',
     'kworker/u64:14-kcryptd-252:0-1', 'kworker/u64:15-kcryptd-252:0-1',
     'kworker/2:1', 'kworker/u65:2-hci0', 'kworker/5:0-events',
     'kworker/13:2-mm_percpu_wq', 'kworker/1:1', 'kworker/5:3',
     'kworker/4:1-events']
    >>> gl.programlist['code']
    {'cmdline': ['code'],
     'cpu_percent': 115.3,
     'cpu_times': {'children_system': 10.270000000000003,
                   'children_user': 8.09,
                   'iowait': 0.0,
                   'system': 84.06000000000002,
                   'user': 143.41000000000003},
     'io_counters': [653464576, 769744896, 653464576, 769744896, 1],
     'memory_info': {'data': 9929465856,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 3405107200,
                     'shared': 1600831488,
                     'text': 2282520576,
                     'vms': 15784431882240},
     'memory_percent': 21.442647221928457,
     'name': 'code',
     'nice': 0,
     'nprocs': 14,
     'num_threads': 250,
     'status': 'S',
     'time_since_update': 0.4304656982421875,
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
    {'time_since_update': 0.41938052300065465, 'version': '7.2.2'}

Psutilversion fields:

* ``version``: psutil version. (unit is *string*)

Glances quicklook
-----------------

.. code-block:: python

    >>> gl.quicklook
    {'bar_char': '▪',
     'cpu': 6.7,
     'cpu_hz': 4475000000,
     'cpu_hz_current': 962367625,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'gpu_proc': 0.0,
     'load': 16.3,
     'max_cpu_display': 4,
     'mem': 58.0,
     'percpu': [{'cpu_number': 0, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 1, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 2, 'level': 'ok', 'total': 10.0},
                {'cpu_number': 3, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 4, 'level': 'ok', 'total': 20.0},
                {'cpu_number': 5, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 6, 'level': 'ok', 'total': 44.4},
                {'cpu_number': 7, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 8, 'level': 'ok', 'total': 18.2},
                {'cpu_number': 9, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 10, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 11, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 12, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 13, 'level': 'ok', 'total': 10.0},
                {'cpu_number': 14, 'level': 'ok', 'total': 0.0},
                {'cpu_number': 15, 'level': 'ok', 'total': 0.0}],
     'percpu_other': {'level': 'ok', 'total': 0.8333333333333334},
     'stats_list': ['cpu', 'mem', 'load'],
     'swap': 23.9,
     'time_since_update': 0.41940965300000244}

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
     'value': 38,
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
     'hr_name': 'Ubuntu 26.04 64bit / Linux 7.0.0-42-generic',
     'linux_distro': 'Ubuntu 26.04',
     'os_name': 'Linux',
     'os_version': '7.0.0-42-generic',
     'platform': '64bit',
     'time_since_update': 0.19420321100005822}

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
    {'seconds': 142213, 'time_since_update': 0.1946942519998629}

Uptime fields:

* ``seconds``: Seconds elapsed since the system booted. (unit is *seconds*)

Glances version
---------------

.. code-block:: python

    >>> gl.version
    {'time_since_update': 0.1949992640002165, 'version': '5.0.0b1'}

Version fields:

* ``version``: Glances version. (unit is *string*)

Glances wifi
------------

.. code-block:: python

    >>> gl.wifi.keys()
    ['wlp0s20f3']
    >>> gl.wifi['wlp0s20f3']
    {'quality_level': -55.0, 'quality_link': 55.0, 'ssid': 'wlp0s20f3'}

Wifi fields:

* ``ssid``: Wi-Fi network name (interface name). (unit is *string*)
* ``quality_link``: Signal quality level. (unit is *dBm*)
* ``quality_level``: Signal strength level. (unit is *dBm*)

Helpers
-------

Human-readable units, as the terminal interface shows them:

.. code-block:: python

    >>> gl.auto_unit(gl.mem["used"])
    '8.58G'

A percentage as a text bar:

.. code-block:: python

    >>> gl.bar(gl.mem["percent"])
    '■■■■■■■■■■□□□□□□□□'

The top processes (the API's own process is left out):

.. code-block:: python

    >>> gl.top_process()
    [{'cpu_percent': 115.3,
      'memory_percent': 4.9685192302236025,
      'name': 'code',
      'pid': 119547},
     {'cpu_percent': 2.4,
      'memory_percent': 2.461380923762629,
      'name': 'gnome-shell',
      'pid': 10039},
     {'cpu_percent': 0.0,
      'memory_percent': 4.773727937022985,
      'name': 'Isolated Web Co',
      'pid': 38731}]

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
