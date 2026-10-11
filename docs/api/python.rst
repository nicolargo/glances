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

    >>> from glances import api as api
    >>> gl = api.GlancesAPI()
    >>> gl.cpu
    {'cpucore': 4,
     'ctx_switches': 0.0,
     'guest': 0.0,
     'idle': 38.5,
     'interrupts': 0.0,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 15.4,
     'time_since_update': 0.06931250700017699,
     'total': 61.5,
     'user': 46.2}
    >>> gl.cpu["total"]
    61.5
    >>> gl.mem["used"]
    880214016
    >>> gl.auto_unit(gl.mem["used"])
    '839M'
    >>> gl.network.keys()
    ['eth0']
    >>> gl.network["eth0"]
    {'bytes_recv': 23345.13623607054,
     'bytes_recv_cumul': 192744834,
     'bytes_sent': 1114065.3621517206,
     'bytes_sent_cumul': 117394716,
     'bytes_speed_rate_per_sec': 0.0,
     'dropped_in': 0.0,
     'dropped_out': 0.0,
     'errors_in': 0.0,
     'errors_out': 0.0,
     'hidden': False,
     'interface_name': 'eth0',
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
     'timer': 0.08660578727722168}

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
    {'log': 4, 'phys': 4, 'time_since_update': 0.07368776400016941}

Core fields:

* ``phys``: Number of physical cores (hyper-thread CPUs excluded). (unit is *number*)
* ``log``: Number of logical CPU cores (physical cores × threads per core). (unit is *number*)

Glances cpu
-----------

.. code-block:: python

    >>> gl.cpu
    {'cpucore': 4,
     'ctx_switches': 0.0,
     'guest': 0.0,
     'idle': 38.5,
     'interrupts': 0.0,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0.0,
     'steal': 0.0,
     'syscalls': 0.0,
     'system': 15.4,
     'time_since_update': 0.06931250700017699,
     'total': 61.5,
     'user': 46.2}

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
    ['vda', 'vdb', 'vdc', 'vdd', 'vde', 'vdf', 'zram0']
    >>> gl.diskio['vda']
    {'disk_name': 'vda',
     'hidden': False,
     'read_bytes': 0.0,
     'read_bytes_cumul': 954582016,
     'read_count': 0.0,
     'read_count_cumul': 50197,
     'read_latency': 0,
     'read_time': 0.0,
     'write_bytes': 166557.29792685667,
     'write_bytes_cumul': 1369006080,
     'write_count': 13.554467604724664,
     'write_count_cumul': 24710,
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
    ['/', '/opt/rclone', '/opt/claude-code', '/opt/env-runner',
     '/mnt/skills/public', '/mnt/skills/examples']
    >>> gl.fs['/']
    {'device_name': '/dev/vda',
     'free': 29979713536,
     'fs_type': 'ext4',
     'mnt_point': '/',
     'options': 'rw,relatime,discard,no_prefetch_block_bitmaps,resv_strict,resuid=65534,resgid=65534',
     'percent': 27.1,
     'size': 270553174016,
     'used': 11154362368}

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
    []

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
    {'address': '192.0.2.2',
     'mask': '255.255.255.0',
     'mask_cidr': 24,
     'time_since_update': 0.0756522789997689}

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
    {'cpucore': 4,
     'min1': 0.904296875,
     'min15': 0.56201171875,
     'min5': 0.560546875,
     'time_since_update': 0.07595141100000546}

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
    {'active': 1073631232,
     'available': 15994716160,
     'buffers': 264708096,
     'cached': 1597554688,
     'free': 14419484672,
     'inactive': 1089409024,
     'percent': 5.2,
     'shared': 14733312,
     'slab': 143499264,
     'time_since_update': 0.06781277100026273,
     'total': 16874930176,
     'used': 880214016}

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
    {'free': 0,
     'percent': 0.0,
     'sin': 0.0,
     'sout': 0.0,
     'time_since_update': 0.07642880200000945,
     'total': 0,
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
    ['eth0']
    >>> gl.network['eth0']
    {'bytes_recv': 23345.13623607054,
     'bytes_recv_cumul': 192744834,
     'bytes_sent': 1114065.3621517206,
     'bytes_sent_cumul': 117394716,
     'bytes_speed_rate_per_sec': 0.0,
     'dropped_in': 0.0,
     'dropped_out': 0.0,
     'errors_in': 0.0,
     'errors_out': 0.0,
     'hidden': False,
     'interface_name': 'eth0',
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
    {'custom': '2026-10-11 15:10:50 UTC',
     'iso': '2026-10-11T15:10:50+00:00',
     'time_since_update': 0.07584123300011925}

Now fields:

* ``custom``: Current date in custom format. (unit is *string*)
* ``iso``: Current date in ISO 8601 format. (unit is *string*)

Glances percpu
--------------

.. code-block:: python

    >>> gl.percpu.keys()
    [0, 1, 2, 3]
    >>> gl.percpu[0]
    {'cpu_number': 0,
     'guest': 0.0,
     'guest_nice': 0.0,
     'idle': 66.7,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 0.0,
     'total': 33.3,
     'user': 33.3}

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
     'host': '192.0.2.1',
     'indice': 'port_0',
     'port': 0,
     'refresh': 30,
     'rtt_warning': None,
     'status': None,
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
     'pid_max': 32768,
     'running': 1,
     'sleeping': 36,
     'sort_key': 'cpu_percent',
     'thread': 125,
     'time_since_update': 0.04733782700031952,
     'total': 82}

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
    [6121, 6154, 120, 87, 6150, 1, 82, 6120, 83, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14,
     15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36,
     37, 38, 39, 40, 41, 42, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58,
     59, 60, 61, 62, 63, 64, 67, 68, 69, 76, 77, 79, 80, 1693, 4530, 5452, 17040,
     17198, 19363, 21728, 21777, 26236, 28559]
    >>> gl.processlist[6121]
    {'cmdline': ['npm exec block-no-verify@1.1.2',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 '',
                 ''],
     'cpu_num': 1,
     'cpu_percent': 141.3,
     'cpu_times': {'children_system': 0.0,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.08,
                   'user': 0.56},
     'gids': {'effective': 0, 'real': 0, 'saved': 0},
     'io_counters': [0, 16384, 0, 16384, 1],
     'key': 'pid',
     'memory_info': {'data': 129896448,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 101978112,
                     'shared': 53035008,
                     'text': 39653376,
                     'vms': 1375858688},
     'memory_percent': 0.6043172382724057,
     'name': 'npm exec block-no-verify@1.1.2',
     'nice': 0,
     'num_threads': 11,
     'pid': 6121,
     'status': 'R',
     'time_since_update': 0.07651209831237793,
     'username': 'root'}

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
    ['npm exec block-no-verify@1.1.2', 'python', 'claude', 'environment-manager',
     'bash', 'process_api', '6', 'sh', 'kthreadd', 'pool_workqueue_release',
     'kworker/R-rcu_gp', 'kworker/R-sync_wq', 'kworker/R-kvfree_rcu_reclaim',
     'kworker/R-slub_flushwq', 'kworker/R-netns', 'kworker/0:0H-events_highpri',
     'kworker/R-mm_percpu_wq', 'ksoftirqd/0', 'rcu_preempt',
     'rcu_exp_par_gp_kthread_worker/0', 'rcu_exp_gp_kthread_worker', 'migration/0',
     'cpuhp/0', 'cpuhp/1', 'migration/1', 'ksoftirqd/1',
     'kworker/1:0H-events_highpri', 'cpuhp/2', 'migration/2', 'ksoftirqd/2',
     'kworker/2:0-slub_flushwq', 'kworker/2:0H-events_highpri', 'cpuhp/3',
     'migration/3', 'ksoftirqd/3', 'kworker/3:0H-events_highpri', 'kdevtmpfs',
     'kworker/R-inet_frag_wq', 'rcu_tasks_kthread', 'rcu_tasks_rude_kthread',
     'rcu_tasks_trace_kthread', 'kauditd', 'khungtaskd', 'oom_reaper',
     'kworker/R-writeback', 'kcompactd0', 'ksmd', 'khugepaged', 'kworker/R-kblockd',
     'kworker/1:1-events_freezable', 'kworker/2:1-events', 'kworker/3:1-events',
     'watchdogd', 'kworker/R-quota_events_unbound', 'kworker/2:1H-kblockd',
     'kswapd0', 'kworker/R-xfsalloc', 'kworker/R-xfs_mru_cache', 'kworker/u17:0',
     'kworker/R-kthrotld', 'irq/24-ACPI:Ged', 'irq/25-ACPI:Ged', 'hwrng',
     'kworker/R-kstrp', 'kworker/1:1H-kblockd', 'kworker/0:1H-kblockd',
     'kworker/3:1H-kblockd', 'kworker/0:2-events', 'kworker/R-ext4-rsv-conversion',
     'kworker/u16:3-iou_exit', 'kworker/u16:0', 'kworker/u16:1-iou_exit',
     'kworker/0:0', 'kworker/3:2', 'kworker/u16:2-iou_exit',
     'kworker/u16:5-iou_exit', 'kworker/u16:7-ext4-rsv-conversion',
     'kworker/u16:8-iou_exit', 'kworker/1:0-mm_percpu_wq']
    >>> gl.programlist['npm exec block-no-verify@1.1.2']
    {'cmdline': ['npm exec block-no-verify@1.1.2'],
     'cpu_percent': 141.3,
     'cpu_times': {'children_system': 0.0,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.08,
                   'user': 0.56},
     'io_counters': [0, 16384, 0, 16384, 1],
     'memory_info': {'data': 129896448,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 101978112,
                     'shared': 53035008,
                     'text': 39653376,
                     'vms': 1375858688},
     'memory_percent': 0.6043172382724057,
     'name': 'npm exec block-no-verify@1.1.2',
     'nice': 0,
     'nprocs': 1,
     'num_threads': 11,
     'status': 'R',
     'time_since_update': 0.07651209831237793,
     'username': 'root'}

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
    {'time_since_update': 0.05393677900019611, 'version': '7.2.2'}

Psutilversion fields:

* ``version``: psutil version. (unit is *string*)

Glances quicklook
-----------------

.. code-block:: python

    >>> gl.quicklook
    {'bar_char': '▪',
     'cpu': 61.5,
     'cpu_hz_current': 2799998000,
     'cpu_log_core': 4,
     'cpu_name': 'Intel(R) Xeon(R) Processor @ 2.80GHz',
     'cpu_phys_core': 4,
     'load': 14.1,
     'max_cpu_display': 4,
     'mem': 5.2,
     'percpu': [{'cpu_number': 0, 'level': 'ok', 'total': 33.3},
                {'cpu_number': 1, 'level': 'warning', 'total': 80.0},
                {'cpu_number': 2, 'level': 'careful', 'total': 66.7},
                {'cpu_number': 3, 'level': 'careful', 'total': 66.7}],
     'percpu_other': None,
     'stats_list': ['cpu', 'mem', 'load'],
     'swap': 0.0,
     'time_since_update': 0.0543863739999324}

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
    []

Sensors fields:

* ``label``: Sensor label. (unit is *string*)
* ``type``: Sensor type (temperature\_core, fan\_speed, temperature\_hdd, battery). (unit is *string*)
* ``unit``: Sensor unit. (unit is *string*)
* ``value``: Sensor value. (unit is *number*)
* ``warning``: Hardware warning threshold. (unit is *number*)
* ``critical``: Hardware critical threshold. (unit is *number*)
* ``status``: Battery charge status. (unit is *string*)

Glances system
--------------

.. code-block:: python

    >>> gl.system
    {'hostname': 'vm',
     'hr_name': 'Ubuntu 24.04 64bit / Linux 6.18.44-fc-v114',
     'linux_distro': 'Ubuntu 24.04',
     'os_name': 'Linux',
     'os_version': '6.18.44-fc-v114',
     'platform': '64bit',
     'time_since_update': 0.053897801999937656}

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
    {'seconds': 3613, 'time_since_update': 0.05446407499994166}

Uptime fields:

* ``seconds``: Seconds elapsed since the system booted. (unit is *seconds*)

Glances version
---------------

.. code-block:: python

    >>> gl.version
    {'time_since_update': 0.05470002999982171, 'version': '5.0.0b1'}

Version fields:

* ``version``: Glances version. (unit is *string*)

Glances wifi
------------

.. code-block:: python

    >>> gl.wifi.keys()
    []

Wifi fields:

* ``ssid``: Wi-Fi network name (interface name). (unit is *string*)
* ``quality_link``: Signal quality level. (unit is *dBm*)
* ``quality_level``: Signal strength level. (unit is *dBm*)

Helpers
-------

Human-readable units, as the terminal interface shows them:

.. code-block:: python

    >>> gl.auto_unit(gl.mem["used"])
    '839M'

A percentage as a text bar:

.. code-block:: python

    >>> gl.bar(gl.mem["percent"])
    '■□□□□□□□□□□□□□□□□□'

The top processes (the API's own process is left out):

.. code-block:: python

    >>> gl.top_process()
    [{'cpu_percent': 141.3,
      'memory_percent': 0.6043172382724057,
      'name': 'npm exec block-no-verify@1.1.2',
      'pid': 6121},
     {'cpu_percent': 56.3,
      'memory_percent': 2.658806521392981,
      'name': 'claude',
      'pid': 120},
     {'cpu_percent': 0.0,
      'memory_percent': 0.2695725287485776,
      'name': 'environment-manager',
      'pid': 87}]

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
