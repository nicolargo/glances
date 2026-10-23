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
     'ctx_switches': 3951.8737646706936,
     'guest': 0.0,
     'idle': 90.0,
     'interrupts': 3616.327919698654,
     'iowait': 0.2,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 2253.2351548122397,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 3.9,
     'time_since_update': 1.0043336999988242,
     'total': 10.0,
     'user': 5.9}
    >>> gl.cpu["total"]
    10.0
    >>> gl.mem["used"]
    9147789312
    >>> gl.auto_unit(gl.mem["used"])
    '8.52G'
    >>> gl.network.keys()
    ['wlp0s20f3', 'mpqemubrzone1', 'tap-8d309783ee6']
    >>> gl.network["wlp0s20f3"]
    {'bytes_recv': 101.7532271038767,
     'bytes_recv_cumul': 1325395189,
     'bytes_sent': 122.51919181895359,
     'bytes_sent_cumul': 115887846,
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
     'timer': 1.100034475326538}

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
    {'log': 16, 'phys': 10, 'time_since_update': 1.018045417000394}

Core fields:

* ``phys``: Number of physical cores (hyper-thread CPUs excluded). (unit is *number*)
* ``log``: Number of logical CPU cores (physical cores × threads per core). (unit is *number*)

Glances cpu
-----------

.. code-block:: python

    >>> gl.cpu
    {'cpucore': 16,
     'ctx_switches': 3951.8737646706936,
     'guest': 0.0,
     'idle': 90.0,
     'interrupts': 3616.327919698654,
     'iowait': 0.2,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 2253.2351548122397,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 3.9,
     'time_since_update': 1.0043336999988242,
     'total': 10.0,
     'user': 5.9}

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
     'read_bytes': 36106.94294699492,
     'read_bytes_cumul': 8299297792,
     'read_count': 4.897317565510379,
     'read_count_cumul': 278444,
     'read_latency': 0,
     'read_time': 0.9794635131020758,
     'write_bytes': 0.0,
     'write_bytes_cumul': 18433140736,
     'write_count': 0.9794635131020758,
     'write_count_cumul': 731837,
     'write_latency': 2,
     'write_time': 1.9589270262041516}

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
     'free': 447092822016,
     'fs_type': 'ext4',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 53.1,
     'size': 1003736440832,
     'used': 505581113344}

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
    {'address': '10.2.11.121',
     'mask': '255.255.0.0',
     'mask_cidr': 16,
     'time_since_update': 0.9942424949986162}

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
     'min1': 2.5849609375,
     'min15': 0.8740234375,
     'min5': 1.36962890625,
     'time_since_update': 0.9946450119987276}

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
    {'active': 6033539072,
     'available': 6732296192,
     'buffers': 290754560,
     'cached': 5508062480,
     'free': 875184128,
     'inactive': 7251116032,
     'percent': 57.6,
     'shared': 1015918592,
     'slab': 897712128,
     'time_since_update': 0.971760398000697,
     'total': 15880085504,
     'used': 9147789312}

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
    {'free': 3511128064,
     'percent': 18.3,
     'sin': 0.0,
     'sout': 0.0,
     'time_since_update': 0.9947321809995628,
     'total': 4294963200,
     'used': 783835136}

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
    ['wlp0s20f3', 'mpqemubrzone1', 'tap-8d309783ee6']
    >>> gl.network['wlp0s20f3']
    {'bytes_recv': 101.7532271038767,
     'bytes_recv_cumul': 1325395189,
     'bytes_sent': 122.51919181895359,
     'bytes_sent_cumul': 115887846,
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
    {'custom': '2026-10-21 12:38:22 CEST',
     'iso': '2026-10-21T12:38:22+02:00',
     'time_since_update': 0.9934825830005138}

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
     'idle': 87.5,
     'iowait': 6.3,
     'irq': 0.0,
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 6.3,
     'total': 12.5,
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
     'host': '10.2.0.1',
     'indice': 'port_0',
     'port': 0,
     'refresh': 30,
     'rtt_warning': None,
     'status': 0.00865,
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
     'running': 1,
     'sleeping': 429,
     'sort_key': 'cpu_percent',
     'thread': 2006,
     'time_since_update': 0.9647178890008945,
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
    [71223, 97174, 129, 7773, 71376, 10406, 17678, 71929, 71102, 14, 15, 123, 10722,
     10109, 10399, 10419, 72701, 8236, 17159, 58267, 3481, 10352, 71909, 71356,
     58706, 72449, 20449, 8225, 8202, 72782, 10361, 71298, 8839, 3929, 71135, 95409,
     94989, 96182, 87850, 8001, 8861, 72912, 97117, 7901, 72913, 8224, 9257, 3937,
     71105, 3210, 11136, 71104, 10334, 8027, 8823, 612, 8136, 3932, 8185, 3496,
     7996, 19217, 97171, 7910, 8134, 10495, 71541, 8272, 9135, 10331, 3502, 7225,
     3355, 7893, 3928, 72573, 1, 3229, 8814, 7215, 9587, 96842, 3525, 7166, 3250,
     658, 3245, 684, 8812, 3438, 3941, 7944, 3194, 3478, 7940, 7218, 7943, 3362,
     8279, 7204, 7960, 3464, 8084, 6905, 7933, 19191, 7930, 7729, 3925, 7937, 4029,
     8008, 7208, 7989, 8793, 7931, 7974, 7932, 3221, 19192, 3926, 8130, 19205, 3169,
     7986, 8357, 4422, 81659, 7353, 7969, 3211, 17843, 7410, 7720, 3225, 8167, 3441,
     3180, 650, 7948, 7862, 7939, 8141, 8375, 7703, 7203, 3215, 8335, 8132, 7726,
     7871, 654, 8363, 3168, 96301, 8350, 7956, 91729, 7357, 20807, 7393, 87556,
     72475, 7705, 71592, 8669, 97013, 3347, 58700, 3204, 72259, 7704, 7869, 3167,
     9365, 7216, 7182, 2988, 7209, 3174, 4471, 19236, 3936, 3015, 17612, 97167,
     71120, 10208, 3934, 58698, 96986, 96833, 7364, 3945, 4364, 97170, 3491, 3484,
     3938, 3312, 58699, 96836, 97007, 4365, 4402, 2, 3, 4, 5, 6, 7, 8, 10, 13, 16,
     17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 30, 31, 33, 34, 35, 36, 37, 39,
     40, 41, 42, 43, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 57, 58, 59, 60, 61, 63,
     64, 65, 66, 67, 69, 70, 71, 72, 73, 75, 76, 77, 78, 79, 81, 82, 83, 84, 85, 87,
     88, 89, 90, 91, 93, 94, 95, 96, 97, 99, 100, 101, 102, 103, 105, 106, 107, 108,
     109, 111, 112, 113, 114, 115, 116, 117, 118, 121, 122, 124, 125, 126, 127, 132,
     134, 135, 136, 137, 138, 139, 141, 142, 143, 144, 145, 146, 147, 148, 151, 153,
     155, 157, 158, 176, 260, 263, 265, 266, 267, 268, 315, 316, 317, 322, 479, 480,
     481, 482, 491, 517, 518, 522, 523, 524, 525, 526, 534, 535, 581, 649, 651, 655,
     682, 685, 736, 737, 766, 774, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788,
     789, 790, 791, 792, 793, 794, 809, 935, 993, 994, 995, 996, 1127, 1128, 1137,
     1138, 1228, 1300, 1304, 1537, 1546, 1804, 2168, 2169, 2170, 2171, 2172, 2173,
     2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186,
     2215, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2226, 2227, 2229, 2256, 2257,
     2258, 2259, 2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270,
     2271, 2272, 2273, 2274, 2275, 2276, 2277, 2278, 2279, 2280, 2283, 2284, 2285,
     2286, 2287, 2288, 2289, 2290, 2291, 2292, 2293, 2294, 2295, 2296, 2297, 2298,
     2299, 2300, 2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311,
     2312, 2324, 2325, 2330, 2331, 2332, 2333, 2334, 2335, 2336, 2337, 2338, 2339,
     2340, 2341, 2342, 2343, 2344, 2345, 2346, 2347, 2348, 2349, 2350, 2352, 3854,
     3990, 4070, 4071, 4072, 4073, 4074, 4075, 4076, 4077, 4078, 4079, 4080, 4081,
     4082, 4083, 4084, 4085, 5043, 17421, 17700, 23508, 59389, 64317, 64453, 64530,
     64735, 65506, 65651, 66038, 70545, 70716, 70968, 71864, 75481, 75705, 75713,
     75821, 78021, 80010, 80352, 82563, 83560, 83562, 83565, 83982, 84494, 85980,
     86356, 86357, 87023, 87152, 87458, 87460, 87462, 87467, 87471, 87473, 87475,
     87477, 87478, 88007, 90422, 92584, 92660, 92661, 92727, 93187, 93515, 93516,
     93517, 94057, 94466, 94596, 94763, 94894, 95337, 95459, 96069, 96100, 96101,
     96102]
    >>> gl.processlist[71223]
    {'cmdline': ['/snap/code/267/usr/share/code/code',
                 '--type=renderer',
                 '--crashpad-handler-pid=71120',
                 '--enable-crash-reporter=864d4bb7-dd20-4851-830f-29e81dd93517,no_channel',
                 '--user-data-dir=/home/nicolargo/.config/Code',
                 '--standard-schemes=vscode-webview,vscode-file',
                 '--secure-schemes=vscode-webview,vscode-file,vscode-remote-resource,vscode-managed-remote-resource',
                 '--cors-schemes=vscode-webview,vscode-file,vscode-remote-resource,vscode-managed-remote-resource',
                 '--fetch-schemes=vscode-webview,vscode-file,vscode-remote-resource,vscode-managed-remote-resource',
                 '--service-worker-schemes=vscode-webview',
                 '--code-cache-schemes=vscode-webview,vscode-file',
                 '--app-path=/snap/code/267/usr/share/code/resources/app',
                 '--enable-sandbox',
                 '--enable-blink-features=HighlightAPI',
                 '--no-sandbox',
                 '--max-active-webgl-contexts=32',
                 '--ozone-platform=x11',
                 '--disable-blink-features=FontMatchingCTMigration,StandardizedBrowserZoom,',
                 '--lang=en-US',
                 '--num-raster-threads=4',
                 '--enable-main-frame-before-activation',
                 '--renderer-client-id=5',
                 '--time-ticks-at-unix-epoch=-1792505208698099',
                 '--launch-time-ticks=7488129399',
                 '--shared-files=v8_context_snapshot_data:100',
                 '--field-trial-handle=3,i,907306203593588083,15267788544344052094,262144',
                 '--enable-features=DocumentPolicyIncludeJSCallStacksInCrashReports,EarlyEstablishGpuChannel,EstablishGpuChannelAsync,GlobalShortcutsPortal,GlobalShortcutsPortalPreferredTrigger,PdfUseShowSaveFilePicker',
                 '--disable-features=CalculateNativeWinOcclusion,DropInputEventsWhilePaintHolding,HideCursorWhileTyping,LocalNetworkAccessChecks,ScreenAIOCREnabled,SpareRendererForSitePerProcess,TraceSiteInstanceGetProcessCreation',
                 '--variations-seed-version',
                 '--pseudonymization-salt-handle=7,i,9778609106371155964,5069553376101663489,4',
                 '--trace-process-track-uuid=3190708990997080739',
                 '--vscode-window-config=vscode:97aa9a0c-b4ae-42ce-bf7d-90eb0e4ad615'],
     'cpu_num': 6,
     'cpu_percent': 104.2,
     'cpu_times': {'children_system': 0.0,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 12.4,
                   'user': 114.07},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [61864960, 0, 61864960, 0, 1],
     'key': 'pid',
     'memory_info': {'data': 1509089280,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 360349696,
                     'shared': 103587840,
                     'text': 163037184,
                     'vms': 1559239704576},
     'memory_percent': 2.269192416559925,
     'name': 'code',
     'nice': 0,
     'num_threads': 24,
     'pid': 71223,
     'status': 'S',
     'time_since_update': 0.9938578605651855,
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
    ['code', 'python', 'irq/9-acpi', 'gnome-shell', 'Isolated Web Co',
     'qemu-system-x86_64', 'ksoftirqd/0', 'rcu_preempt', 'ksmd', 'WebExtensions',
     'firefox', 'dropbox', 'multipassd', 'nautilus', 'python3', 'Privileged Cont',
     'gnome-text-editor', 'terminator', 'snap-store', 'Xwayland', 'RDD Process',
     'mutter-x11-frames', 'dockerd', 'Web Content', 'gjs', 'evolution-alarm-notify',
     'ibus-x11', 'evolution-source-registry', 'evolution-calendar-factory', 'fwupd',
     'libvirtd', 'snapd', 'Utility Process', 'Socket Process', 'goa-daemon',
     'xdg-desktop-portal-gnome', 'systemd-journald', 'ibus-extension-gtk3',
     'ollama', 'localsearch-3', 'unattended-upgr', 'update-notifier', 'uv', 'snap',
     'copilot-runtime', 'evolution-addressbook-factory', 'xdg-desktop-portal-gtk',
     'forkserver', 'containerd', 'NetworkManager', 'gnome-shell-calendar-server',
     'cups-browsed', 'ruff', 'systemd', 'udisksd', 'xdg-desktop-portal',
     'wireplumber', 'snapd-desktop-integration', 'glycin-svg', 'colord', 'virtlogd',
     'systemd-udevd', 'virtlockd', 'systemd-resolved', 'gsd-xsettings',
     'ModemManager', 'snmpd', 'gsd-print-notifications', 'polkitd', 'cupsd',
     'gsd-media-keys', 'pipewire-pulse', 'gsd-power', 'wpa_supplicant',
     'gvfs-udisks2-volume-monitor', 'pipewire', 'gsd-sharing', 'upowerd',
     'gsd-printer', 'gdm-session-worker', 'gsd-datetime', 'gvfsd-recent',
     'ibus-daemon', 'gnome-session-service', 'gsd-housekeeping', 'gdm3',
     'gsd-disk-utility-notify', 'gnome-keyring-daemon', 'gsd-wwan', 'gvfsd-trash',
     'gsd-a11y-settings', 'gsd-sound', 'gsd-color', 'systemd-logind',
     'gvfsd-network', 'cups-proxyd', 'goa-identity-service', 'gvfsd-dnssd',
     'dbus-daemon', 'gsd-usb-protection', 'gvfs-afc-volume-monitor', 'thermald',
     'gvfsd-wsdd', 'xdg-document-portal', 'gsd-smartcard', 'accounts-daemon',
     'dart:firmware-n', 'gnome-session-init-worker', 'gvfsd', 'systemd-machined',
     'gvfsd-metadata', 'boltd', 'iio-sensor-proxy', 'systemd-timesyncd',
     'gsd-rfkill', 'at-spi-bus-launcher', 'gsd-keyboard', 'ibus-portal',
     'ibus-engine-simple', 'gcr-ssh-agent', 'switcheroo-control',
     'gvfs-gphoto2-volume-monitor', 'ibus-memconf', 'gvfsd-fuse',
     'at-spi2-registryd', 'systemd-oomd', 'gvfs-mtp-volume-monitor', 'bluetoothd',
     'sleep', 'gvfs-goa-volume-monitor', 'gsd-screensaver-proxy', 'bash',
     'xdg-permission-store', 'ssh-agent', 'gdm-wayland-session', 'zed', 'dconf',
     'dconf-service', 'glycin-image-rs', 'rsyslogd', 'smartd', 'pet',
     'gnome-session-ctl', 'avahi-daemon', 'user-session-helper', '(sd-pam)',
     'rpcbind', 'mpris-proxy', 'fsidd', 'rtkit-daemon', 'uuidd', 'cron', 'nfsdcld',
     'dnsmasq', 'make', 'chrome_crashpad_handler', 'crashhelper', 'rpc.idmapd',
     'bwrap', 'fusermount3', 'rpc.statd', 'sh', 'run-cupsd', 'run-cups-browse',
     'rpc.mountd', 'kthreadd', 'pool_workqueue_release', 'kworker/R-rcu_gp',
     'kworker/R-sync_wq', 'kworker/R-kvfree_rcu_reclaim', 'kworker/R-slub_flushwq',
     'kworker/R-netns', 'kworker/0:0H-kblockd', 'kworker/R-mm_percpu_wq',
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
     'oom_reaper', 'kworker/R-writeback', 'kcompactd0', 'khugepaged',
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
     'kworker/R-USBC000:00-con3', 'kworker/6:1H-kblockd',
     'kworker/R-kdmflush/252:0', 'kworker/R-kcryptd_io-252:0-1',
     'kworker/R-kcryptd-252:0-1', 'dmcrypt_write/252:0', 'kworker/R-kdmflush/252:1',
     'kworker/14:1H-kblockd', 'kworker/4:1H-kblockd', 'kworker/13:1H-i915_cleanup',
     'kworker/10:1H-i915_cleanup', 'kworker/11:1H-kblockd', 'kworker/5:1H-kblockd',
     'kworker/7:1H-i915_cleanup', 'jbd2/dm-1-8', 'kworker/R-ext4-rsv-conversion',
     'kworker/3:1H-kblockd', 'kworker/12:1H-i915_cleanup',
     'kworker/15:1H-i915_cleanup', 'kworker/2:1H-kblockd',
     'kworker/8:1H-i915_cleanup', 'psimon', 'kworker/1:1H-i915_cleanup',
     'kworker/0:1H-kblockd', 'kworker/9:1H-kblockd', 'kworker/R-cfg80211',
     'irq/198-iwlwifi:default_queue', 'irq/199-iwlwifi:queue_1',
     'irq/200-iwlwifi:queue_2', 'irq/201-iwlwifi:queue_3',
     'irq/202-iwlwifi:queue_4', 'irq/203-iwlwifi:queue_5',
     'irq/204-iwlwifi:queue_6', 'irq/205-iwlwifi:queue_7',
     'irq/206-iwlwifi:queue_8', 'irq/207-iwlwifi:queue_9',
     'irq/208-iwlwifi:queue_10', 'irq/209-iwlwifi:queue_11',
     'irq/210-iwlwifi:queue_12', 'irq/211-iwlwifi:queue_13',
     'irq/212-iwlwifi:queue_14', 'irq/213-iwlwifi:exception',
     'irq/16-processor_thermal_device_pci', 'kworker/R-ttm', 'card1-crtc0',
     'card1-crtc1', 'card1-crtc2', 'card1-crtc3', 'jbd2/nvme0n1p2-8',
     'kworker/R-rpciod', 'kworker/R-xprtiod', 'irq/197-cs35l41 IRQ1 Controller',
     'irq/217-mei_gsc', 'irq/218-mei_gsc', 'irq/233-AudioDSP', 'spl_system_task',
     'spl_delay_taskq', 'spl_dynamic_tas', 'spl_kmem_cache', 'zvol_tq-0',
     'zvol_tq-1', 'zvol_tq-2', 'arc_prune', 'arc_evict', 'arc_flush', 'arc_reap',
     'dbu_evict', 'dbuf_evict', 'z_vdev_file', 'l2arc_feed', 'z_null_iss',
     'z_null_int', 'z_rd_iss', 'z_rd_int_0', 'z_rd_int_1', 'z_rd_int_2', 'z_wr_iss',
     'z_wr_int_0', 'z_wr_int_1', 'z_wr_int_2', 'z_fr_iss_0', 'z_fr_iss_1',
     'z_fr_iss_2', 'z_fr_iss_3', 'z_fr_int', 'z_cl_iss', 'z_cl_int', 'z_flush_iss',
     'z_flush_int', 'z_trim_iss', 'z_trim_int', 'z_zvol', 'z_metaslab',
     'z_prefetch', 'z_upgrade', 'dp_sync_taskq', 'dp_zil_clean_ta', 'z_zrele',
     'z_unlinked_drai', 'txg_quiesce', 'txg_sync', 'mmp', 'raidz_expand',
     'z_indirect_cond', 'z_livelist_dest', 'z_livelist_cond', 'z_checkpoint_di',
     'lockd', 'nfsd', 'krfcommd', 'kvm-pit/17678', 'kworker/14:1-events',
     'kworker/3:2-mm_percpu_wq', 'kworker/1:1-mm_percpu_wq', 'kworker/10:1-events',
     'kworker/5:1-events', 'kworker/u65:0-rb_allocator', 'kworker/2:1-mm_percpu_wq',
     'kworker/4:0-i915-unordered', 'kworker/15:0-mm_percpu_wq',
     'kworker/11:2-events', 'kworker/14:0-mm_percpu_wq', 'kworker/0:2-events',
     'kworker/7:1', 'kworker/0:0', 'kworker/u64:0-kcryptd-252:0-1',
     'kworker/u64:14-kcryptd-252:0-1', 'kworker/9:1-mm_percpu_wq',
     'kworker/9:0-events', 'kworker/6:0-events', 'kworker/7:2-events',
     'kworker/8:0-events', 'kworker/u64:1-kcryptd-252:0-1',
     'kworker/u64:4-kcryptd-252:0-1', 'kworker/u64:12-kcryptd-252:0-1',
     'kworker/3:0-mm_percpu_wq', 'kworker/13:1-events', 'kworker/12:2-events',
     'kworker/u64:7-kcryptd-252:0-1', 'kworker/u64:9-kcryptd-252:0-1',
     'kworker/8:2-events', 'kworker/10:0-mm_percpu_wq',
     'kworker/u64:16-kcryptd-252:0-1', 'kworker/u64:18-events_unbound',
     'kworker/u64:19-events_unbound', 'kworker/u64:24-kcryptd-252:0-1',
     'kworker/4:2-usb_hub_wq', 'irq/214-mei_me', 'kworker/11:1-events',
     'kworker/2:3-events', 'kworker/15:2-cgroup_free', 'kworker/u65:3-rb_allocator',
     'kworker/5:3-mm_percpu_wq', 'kworker/1:0-mm_percpu_wq',
     'kworker/u64:3-kcryptd-252:0-1', 'kworker/u64:5-kcryptd-252:0-1',
     'kworker/5:2-mm_percpu_wq', 'kworker/u64:6-kcryptd-252:0-1',
     'kworker/12:1-mm_percpu_wq', 'kworker/6:2-i915-unordered',
     'kworker/13:2-mm_percpu_wq', 'kworker/u65:1', 'kworker/1:2-mm_percpu_wq',
     'kworker/10:2', 'kworker/0:1-events', 'kworker/11:0', 'kworker/8:1',
     'kworker/u65:2-rb_allocator', 'kworker/5:0-events',
     'kworker/u64:2-kcryptd-252:0-1', 'kworker/u64:8-kcryptd-252:0-1',
     'kworker/u64:10-kcryptd-252:0-1']
    >>> gl.programlist['code']
    {'cmdline': ['code'],
     'cpu_percent': 108.3,
     'cpu_times': {'children_system': 40.35,
                   'children_user': 66.35000000000001,
                   'iowait': 0.0,
                   'system': 122.52000000000001,
                   'user': 334.49999999999994},
     'io_counters': [739906560, 927129600, 739906560, 927129600, 1],
     'memory_info': {'data': 9246576640,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 2757025792,
                     'shared': 1197760512,
                     'text': 2119483392,
                     'vms': 14227392053248},
     'memory_percent': 17.361529894190674,
     'name': 'code',
     'nice': 0,
     'nprocs': 13,
     'num_threads': 234,
     'status': 'S',
     'time_since_update': 0.9938578605651855,
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
    {'time_since_update': 0.9835122779986705, 'version': '7.2.2'}

Psutilversion fields:

* ``version``: psutil version. (unit is *string*)

Glances quicklook
-----------------

.. code-block:: python

    >>> gl.quicklook
    {'bar_char': '▪',
     'cpu': 10.0,
     'cpu_hz': 4475000000,
     'cpu_hz_current': 848033125,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'gpu_proc': 0.0,
     'load': 5.5,
     'max_cpu_display': 4,
     'mem': 57.4,
     'percpu': [{'cpu_number': 0, 'level': 'ok', 'total': 22.2},
                {'cpu_number': 1, 'level': 'ok', 'total': 5.6},
                {'cpu_number': 2, 'level': 'ok', 'total': 0.9},
                {'cpu_number': 3, 'level': 'ok', 'total': 7.5},
                {'cpu_number': 4, 'level': 'ok', 'total': 15.5},
                {'cpu_number': 5, 'level': 'ok', 'total': 2.8},
                {'cpu_number': 6, 'level': 'careful', 'total': 55.3},
                {'cpu_number': 7, 'level': 'ok', 'total': 5.5},
                {'cpu_number': 8, 'level': 'ok', 'total': 15.0},
                {'cpu_number': 9, 'level': 'ok', 'total': 0.9},
                {'cpu_number': 10, 'level': 'ok', 'total': 0.9},
                {'cpu_number': 11, 'level': 'ok', 'total': 9.3},
                {'cpu_number': 12, 'level': 'ok', 'total': 7.4},
                {'cpu_number': 13, 'level': 'ok', 'total': 3.7},
                {'cpu_number': 14, 'level': 'ok', 'total': 8.3},
                {'cpu_number': 15, 'level': 'ok', 'total': 9.2}],
     'percpu_other': {'level': 'ok', 'total': 5.166666666666667},
     'stats_list': ['cpu', 'mem', 'load'],
     'swap': 18.3,
     'time_since_update': 0.9848116770008346}

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
     'HDD', 'Package id 0', 'SODIMM', 'Sensor (mean)', 'Unknown (mean)',
     'Video Fan', 'dell_smm (mean)', 'i915 0', 'iwlwifi_1_14 0', 'temp']
    >>> gl.sensors['Ambient (mean)']
    {'critical': None,
     'label': 'Ambient (mean)',
     'type': 'temperature_core',
     'unit': 'C',
     'value': 36,
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
     'hr_name': 'Ubuntu 26.04 64bit / Linux 7.0.0-38-generic',
     'linux_distro': 'Ubuntu 26.04',
     'os_name': 'Linux',
     'os_version': '7.0.0-38-generic',
     'platform': '64bit',
     'time_since_update': 0.4021295700003975}

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
    {'seconds': 164711, 'time_since_update': 0.4027437889999419}

Uptime fields:

* ``seconds``: Seconds elapsed since the system booted. (unit is *seconds*)

Glances version
---------------

.. code-block:: python

    >>> gl.version
    {'time_since_update': 0.4034100300013961, 'version': '5.0.0b1'}

Version fields:

* ``version``: Glances version. (unit is *string*)

Glances wifi
------------

.. code-block:: python

    >>> gl.wifi.keys()
    ['wlp0s20f3']
    >>> gl.wifi['wlp0s20f3']
    {'quality_level': -64.0, 'quality_link': 46.0, 'ssid': 'wlp0s20f3'}

Wifi fields:

* ``ssid``: Wi-Fi network name (interface name). (unit is *string*)
* ``quality_link``: Signal quality level. (unit is *dBm*)
* ``quality_level``: Signal strength level. (unit is *dBm*)

Helpers
-------

Human-readable units, as the terminal interface shows them:

.. code-block:: python

    >>> gl.auto_unit(gl.mem["used"])
    '8.52G'

A percentage as a text bar:

.. code-block:: python

    >>> gl.bar(gl.mem["percent"])
    '■■■■■■■■■■□□□□□□□□'

The top processes (the API's own process is left out):

.. code-block:: python

    >>> gl.top_process()
    [{'cpu_percent': 104.2,
      'memory_percent': 2.269192416559925,
      'name': 'code',
      'pid': 71223},
     {'cpu_percent': 3.1,
      'memory_percent': 1.7076978076200666,
      'name': 'gnome-shell',
      'pid': 7773},
     {'cpu_percent': 2.1,
      'memory_percent': 0.8493479708659383,
      'name': 'code',
      'pid': 71376}]

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
