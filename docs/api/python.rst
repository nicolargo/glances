.. _api:

Python API documentation
========================

This documentation describes the Glances Python API.

Note: This API is only available in Glances 4.4.0 or higher.


TL;DR
-----

You can access the Glances API by importing the `glances.api` module and creating an
instance of the `GlancesAPI` class. This instance provides access to all Glances plugins
and their fields. For example, to access the CPU plugin and its total field, you can
use the following code:

.. code-block:: python

    >>> from glances import api
    >>> gl = api.GlancesAPI()
    >>> gl.cpu
    {'cpucore': 16,
     'ctx_switches': 75032573,
     'guest': 0.0,
     'idle': 92.8,
     'interrupts': 52127034,
     'iowait': 0.2,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 25186254,
     'steal': 0.0,
     'syscalls': 0,
     'system': 4.6,
     'total': 6.6,
     'user': 2.3}
    >>> gl.cpu.get("total")
    6.6
    >>> gl.mem.get("used")
    10449404952
    >>> gl.auto_unit(gl.mem.get("used"))
    9.73G

If the stats return a list of items (like network interfaces or processes), you can
access them by their name:

.. code-block:: python

    >>> gl.network.keys()
    ['wlp0s20f3']
    >>> gl.network["wlp0s20f3"]
    {'alias': None,
     'bytes_all': 0,
     'bytes_all_gauge': 2239851362,
     'bytes_all_rate_per_sec': 0.0,
     'bytes_recv': 0,
     'bytes_recv_gauge': 2126755379,
     'bytes_recv_rate_per_sec': 0.0,
     'bytes_sent': 0,
     'bytes_sent_gauge': 113095983,
     'bytes_sent_rate_per_sec': 0.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.15889406204223633}

Init Glances Python API
-----------------------

Init the Glances API:

.. code-block:: python

    >>> from glances import api
    >>> gl = api.GlancesAPI()

Get Glances plugins list
------------------------

Get the plugins list:

.. code-block:: python

    >>> gl.plugins()
    ['alert', 'ports', 'diskio', 'containers', 'processcount', 'programlist', 'gpu', 'percpu', 'system', 'network', 'cpu', 'amps', 'processlist', 'load', 'sensors', 'uptime', 'now', 'fs', 'wifi', 'ip', 'help', 'version', 'psutilversion', 'core', 'mem', 'folders', 'quicklook', 'memswap']

Glances alert
-------------

Alert stats:

.. code-block:: python

    >>> type(gl.alert)
    <class 'glances.plugins.alert.AlertPlugin'>
    >>> gl.alert
    []

Alert fields description:

* begin: Begin timestamp of the event
* end: End timestamp of the event (or -1 if ongoing)
* state: State of the event (WARNING|CRITICAL)
* type: Type of the event (CPU|LOAD|MEM)
* max: Maximum value during the event period
* avg: Average value during the event period
* min: Minimum value during the event period
* sum: Sum of the values during the event period
* count: Number of values during the event period
* top: Top 3 processes name during the event period
* desc: Description of the event
* sort: Sort key of the top processes
* global_msg: Global alert message

Alert limits:

.. code-block:: python

    >>> gl.alert.limits
    {'alert_disable': ['False'], 'history_size': 1200.0}

Glances ports
-------------

Ports stats:

.. code-block:: python

    >>> type(gl.ports)
    <class 'glances.plugins.ports.PortsPlugin'>
    >>> gl.ports
    [{'description': 'DefaultGateway',
      'host': '192.168.1.1',
      'indice': 'port_0',
      'port': 0,
      'refresh': 30,
      'rtt_warning': None,
      'status': 0.006345,
      'timeout': 3}]

Ports fields description:

* host: Measurement is be done on this host (or IP address)
* port: Measurement is be done on this port (0 for ICMP)
* description: Human readable description for the host/port
* refresh: Refresh time (in seconds) for this host/port
* timeout: Timeout (in seconds) for the measurement
* status: Measurement result (in seconds)
* rtt_warning: Warning threshold (in seconds) for the measurement
* indice: Unique indice for the host/port

Ports limits:

.. code-block:: python

    >>> gl.ports.limits
    {'history_size': 1200.0,
     'ports_disable': ['False'],
     'ports_port_default_gateway': ['True'],
     'ports_refresh': 30.0,
     'ports_timeout': 3.0}

Glances diskio
--------------

Diskio stats:

.. code-block:: python

    >>> type(gl.diskio)
    <class 'glances.plugins.diskio.DiskioPlugin'>
    >>> gl.diskio
    Return a dict of dict with key=<disk_name>
    >>> gl.diskio.keys()
    ['nvme0n1', 'nvme0n1p1', 'nvme0n1p2', 'nvme0n1p3', 'dm-0', 'dm-1']
    >>> gl.diskio.get("nvme0n1")
    {'disk_name': 'nvme0n1',
     'key': 'disk_name',
     'read_bytes': 10319813120,
     'read_count': 536973,
     'read_latency': 0,
     'read_time': 73073,
     'write_bytes': 15554712576,
     'write_count': 662603,
     'write_latency': 0,
     'write_time': 882884}

Diskio fields description:

* disk_name: Disk name.
* read_count: Number of reads.
* write_count: Number of writes.
* read_bytes: Number of bytes read.
* write_bytes: Number of bytes written.
* read_time: Time spent reading.
* write_time: Time spent writing.
* read_latency: Mean time spent reading per operation.
* write_latency: Mean time spent writing per operation.

Diskio limits:

.. code-block:: python

    >>> gl.diskio.limits
    {'diskio_disable': ['False'],
     'diskio_hide': ['loop.*', '/dev/loop.*'],
     'diskio_hide_zero': ['False'],
     'diskio_rx_latency_careful': 10.0,
     'diskio_rx_latency_critical': 50.0,
     'diskio_rx_latency_warning': 20.0,
     'diskio_tx_latency_careful': 10.0,
     'diskio_tx_latency_critical': 50.0,
     'diskio_tx_latency_warning': 20.0,
     'history_size': 1200.0}

Glances containers
------------------

Containers stats:

.. code-block:: python

    >>> type(gl.containers)
    <class 'glances.plugins.containers.ContainersPlugin'>
    >>> gl.containers
    []

Containers fields description:

* name: Container name
* id: Container ID
* image: Container image
* status: Container status
* created: Container creation date
* command: Container command
* cpu_percent: Container CPU consumption
* memory_inactive_file: Container memory inactive file
* memory_limit: Container memory limit
* memory_usage: Container memory usage
* io_rx: Container IO bytes read rate
* io_wx: Container IO bytes write rate
* network_rx: Container network RX bitrate
* network_tx: Container network TX bitrate
* ports: Container ports
* uptime: Container uptime
* engine: Container engine (Docker, Podman, and LXD are currently supported)
* pod_name: Pod name (only with Podman)
* pod_id: Pod ID (only with Podman)

Containers limits:

.. code-block:: python

    >>> gl.containers.limits
    {'containers_all': ['False'],
     'containers_disable': ['False'],
     'containers_disable_stats': ['command'],
     'containers_max_name_size': 20.0,
     'history_size': 1200.0}

Glances processcount
--------------------

Processcount stats:

.. code-block:: python

    >>> type(gl.processcount)
    <class 'glances.plugins.processcount.ProcesscountPlugin'>
    >>> gl.processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 415, 'thread': 2099, 'total': 564}
    >>> gl.processcount.keys()
    ['total', 'running', 'sleeping', 'thread', 'pid_max']
    >>> gl.processcount.get("total")
    564

Processcount fields description:

* total: Total number of processes
* running: Total number of running processes
* sleeping: Total number of sleeping processes
* thread: Total number of threads
* pid_max: Maximum number of processes

Processcount limits:

.. code-block:: python

    >>> gl.processcount.limits
    {'history_size': 1200.0, 'processcount_disable': ['False']}

Glances gpu
-----------

Gpu stats:

.. code-block:: python

    >>> type(gl.gpu)
    <class 'glances.plugins.gpu.GpuPlugin'>
    >>> gl.gpu
    Return a dict of dict with key=<gpu_id>
    >>> gl.gpu.keys()
    ['intel0', 'intel1']
    >>> gl.gpu.get("intel0")
    {'fan_speed': None,
     'gpu_id': 'intel0',
     'key': 'gpu_id',
     'mem': None,
     'name': 'UHD Graphics',
     'proc': 0,
     'temperature': None}

Gpu fields description:

* gpu_id: GPU identification
* name: GPU name
* mem: Memory consumption
* proc: GPU processor consumption
* temperature: GPU temperature
* fan_speed: GPU fan speed

Gpu limits:

.. code-block:: python

    >>> gl.gpu.limits
    {'gpu_disable': ['False'],
     'gpu_mem_careful': 50.0,
     'gpu_mem_critical': 90.0,
     'gpu_mem_warning': 70.0,
     'gpu_proc_careful': 50.0,
     'gpu_proc_critical': 90.0,
     'gpu_proc_warning': 70.0,
     'gpu_temperature_careful': 60.0,
     'gpu_temperature_critical': 80.0,
     'gpu_temperature_warning': 70.0,
     'history_size': 1200.0}

Glances percpu
--------------

Percpu stats:

.. code-block:: python

    >>> type(gl.percpu)
    <class 'glances.plugins.percpu.PercpuPlugin'>
    >>> gl.percpu
    Return a dict of dict with key=<cpu_number>
    >>> gl.percpu.keys()
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    >>> gl.percpu.get("0")
    {'cpu_number': 0,
     'dpc': None,
     'guest': 0.0,
     'guest_nice': 0.0,
     'idle': 21.0,
     'interrupt': None,
     'iowait': 0.0,
     'irq': 0.0,
     'key': 'cpu_number',
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 5.0,
     'total': 79.0,
     'user': 0.0}

Percpu fields description:

* cpu_number: CPU number
* total: Sum of CPU percentages (except idle) for current CPU number.
* system: Percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel.
* user: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries).
* iowait: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete.
* idle: percent of CPU used by any program. Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle.
* irq: *(Linux and BSD)*: percent time spent servicing/handling hardware/software interrupts. Time servicing interrupts (hardware + software).
* nice: *(Unix)*: percent time occupied by user level processes with a positive nice value. The time the CPU has spent running users' processes that have been *niced*.
* steal: *(Linux)*: percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor.
* guest: *(Linux)*: percent of time spent running a virtual CPU for guest operating systems under the control of the Linux kernel.
* guest_nice: *(Linux)*: percent of time spent running a niced guest (virtual CPU).
* softirq: *(Linux)*: percent of time spent handling software interrupts.
* dpc: *(Windows)*: percent of time spent handling deferred procedure calls.
* interrupt: *(Windows)*: percent of time spent handling software interrupts.

Percpu limits:

.. code-block:: python

    >>> gl.percpu.limits
    {'history_size': 1200.0,
     'percpu_disable': ['False'],
     'percpu_iowait_careful': 50.0,
     'percpu_iowait_critical': 90.0,
     'percpu_iowait_warning': 70.0,
     'percpu_max_cpu_display': 4.0,
     'percpu_system_careful': 50.0,
     'percpu_system_critical': 90.0,
     'percpu_system_warning': 70.0,
     'percpu_user_careful': 50.0,
     'percpu_user_critical': 90.0,
     'percpu_user_warning': 70.0}

Glances system
--------------

System stats:

.. code-block:: python

    >>> type(gl.system)
    <class 'glances.plugins.system.SystemPlugin'>
    >>> gl.system
    {'hostname': 'nicolargo-xps15',
     'hr_name': 'Ubuntu 24.04 64bit / Linux 6.17.0-19-generic',
     'linux_distro': 'Ubuntu 24.04',
     'os_name': 'Linux',
     'os_version': '6.17.0-19-generic',
     'platform': '64bit'}
    >>> gl.system.keys()
    ['os_name', 'hostname', 'platform', 'os_version', 'linux_distro', 'hr_name']
    >>> gl.system.get("os_name")
    'Linux'

System fields description:

* os_name: Operating system name
* hostname: Hostname
* platform: Platform (32 or 64 bits)
* linux_distro: Linux distribution
* os_version: Operating system version
* hr_name: Human readable operating system name

System limits:

.. code-block:: python

    >>> gl.system.limits
    {'history_size': 1200.0, 'system_disable': ['False'], 'system_refresh': 60}

Glances network
---------------

Network stats:

.. code-block:: python

    >>> type(gl.network)
    <class 'glances.plugins.network.NetworkPlugin'>
    >>> gl.network
    Return a dict of dict with key=<interface_name>
    >>> gl.network.keys()
    ['wlp0s20f3']
    >>> gl.network.get("wlp0s20f3")
    {'alias': None,
     'bytes_all': 0,
     'bytes_all_gauge': 2239851362,
     'bytes_all_rate_per_sec': 0.0,
     'bytes_recv': 0,
     'bytes_recv_gauge': 2126755379,
     'bytes_recv_rate_per_sec': 0.0,
     'bytes_sent': 0,
     'bytes_sent_gauge': 113095983,
     'bytes_sent_rate_per_sec': 0.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.002747774124145508}

Network fields description:

* interface_name: Interface name.
* alias: Interface alias name (optional).
* bytes_recv: Number of bytes received.
* bytes_sent: Number of bytes sent.
* bytes_all: Number of bytes received and sent.
* speed: Maximum interface speed (in bit per second). Can return 0 on some operating-system.
* is_up: Is the interface up ?

Network limits:

.. code-block:: python

    >>> gl.network.limits
    {'history_size': 1200.0,
     'network_disable': ['False'],
     'network_hide': ['docker.*', 'lo'],
     'network_hide_no_ip': ['True'],
     'network_hide_no_up': ['True'],
     'network_hide_zero': ['False'],
     'network_rx_careful': 70.0,
     'network_rx_critical': 90.0,
     'network_rx_warning': 80.0,
     'network_tx_careful': 70.0,
     'network_tx_critical': 90.0,
     'network_tx_warning': 80.0}

Glances cpu
-----------

Cpu stats:

.. code-block:: python

    >>> type(gl.cpu)
    <class 'glances.plugins.cpu.CpuPlugin'>
    >>> gl.cpu
    {'cpucore': 16,
     'ctx_switches': 75032573,
     'guest': 0.0,
     'idle': 92.8,
     'interrupts': 52127034,
     'iowait': 0.2,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 25186254,
     'steal': 0.0,
     'syscalls': 0,
     'system': 4.6,
     'total': 6.6,
     'user': 2.3}
    >>> gl.cpu.keys()
    ['total', 'user', 'nice', 'system', 'idle', 'iowait', 'irq', 'steal', 'guest', 'ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls', 'cpucore']
    >>> gl.cpu.get("total")
    6.6

Cpu fields description:

* total: Sum of all CPU percentages (except idle).
* system: Percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel.
* user: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries).
* iowait: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete.
* dpc: *(Windows)*: time spent servicing deferred procedure calls (DPCs)
* idle: percent of CPU used by any program. Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle.
* irq: *(Linux and BSD)*: percent time spent servicing/handling hardware/software interrupts. Time servicing interrupts (hardware + software).
* nice: *(Unix)*: percent time occupied by user level processes with a positive nice value. The time the CPU has spent running users' processes that have been *niced*.
* steal: *(Linux)*: percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor.
* guest: *(Linux)*: time spent running a virtual CPU for guest operating systems under the control of the Linux kernel.
* ctx_switches: number of context switches (voluntary + involuntary) per second. A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict.
* interrupts: number of interrupts per second.
* soft_interrupts: number of software interrupts per second. Always set to 0 on Windows and SunOS.
* syscalls: number of system calls per second. Always 0 on Linux OS.
* cpucore: Total number of CPU core.
* time_since_update: Number of seconds since last update.
* total_min: Minimum total observed since Glances startup.
* total_max: Maximum total observed since Glances startup.
* total_mean: Mean (average) total computed from the history.

Cpu limits:

.. code-block:: python

    >>> gl.cpu.limits
    {'cpu_ctx_switches_careful': 640000.0,
     'cpu_ctx_switches_critical': 800000.0,
     'cpu_ctx_switches_warning': 720000.0,
     'cpu_disable': ['False'],
     'cpu_iowait_careful': 5.0,
     'cpu_iowait_critical': 6.25,
     'cpu_iowait_warning': 5.625,
     'cpu_steal_careful': 50.0,
     'cpu_steal_critical': 90.0,
     'cpu_steal_warning': 70.0,
     'cpu_system_careful': 50.0,
     'cpu_system_critical': 90.0,
     'cpu_system_log': ['False'],
     'cpu_system_warning': 70.0,
     'cpu_total_careful': 65.0,
     'cpu_total_critical': 85.0,
     'cpu_total_log': ['True'],
     'cpu_total_warning': 75.0,
     'cpu_user_careful': 50.0,
     'cpu_user_critical': 90.0,
     'cpu_user_log': ['False'],
     'cpu_user_warning': 70.0,
     'history_size': 1200.0}

Glances amps
------------

Amps stats:

.. code-block:: python

    >>> type(gl.amps)
    <class 'glances.plugins.amps.AmpsPlugin'>
    >>> gl.amps
    Return a dict of dict with key=<name>
    >>> gl.amps.keys()
    ['Dropbox', 'Python', 'Conntrack', 'Nginx', 'Systemd', 'SystemV']
    >>> gl.amps.get("Dropbox")
    {'count': 0,
     'countmax': None,
     'countmin': 1.0,
     'key': 'name',
     'name': 'Dropbox',
     'refresh': 3.0,
     'regex': True,
     'result': None,
     'timer': 0.1653919219970703}

Amps fields description:

* name: AMP name.
* result: AMP result (a string).
* refresh: AMP refresh interval.
* timer: Time until next refresh.
* count: Number of matching processes.
* countmin: Minimum number of matching processes.
* countmax: Maximum number of matching processes.

Amps limits:

.. code-block:: python

    >>> gl.amps.limits
    {'amps_disable': ['False'], 'history_size': 1200.0}

Glances processlist
-------------------

Processlist stats:

.. code-block:: python

    >>> type(gl.processlist)
    <class 'glances.plugins.processlist.ProcesslistPlugin'>
    >>> gl.processlist
    Return a dict of dict with key=<pid>
    >>> gl.processlist.keys()
    [164799, 9831, 129, 10763, 6978, 9685, 3825, 9915, 7572, 8378, 51019, 7994, 5655, 8492, 8274, 8003, 11673, 54321, 153216, 3361, 11529, 7282, 9930, 140222, 8261, 140289, 9931, 42928, 9863, 145633, 10305, 10374, 11332, 11908, 9705, 9790, 9717, 10516, 162110, 163500, 162319, 9747, 5871, 5781, 10491, 10506, 164766, 10602, 10499, 6065, 36800, 7988, 9687, 9688, 6248, 18275, 6251, 7292, 7256, 3377, 2916, 5904, 9052, 7252, 6128, 5995, 10768, 6419, 9741, 6292, 5827, 7375, 5794, 5825, 773, 5773, 6446, 5845, 3031, 3366, 5815, 5610, 145004, 5823, 2936, 1, 5496, 2900, 6012, 2937, 3402, 2938, 5364, 6238, 5341, 2908, 3159, 3705, 2741, 5866, 5818, 5321, 5840, 54349, 5360, 3832, 5365, 144973, 3037, 5367, 3780, 5831, 3195, 3706, 6200, 67497, 154538, 3896, 5843, 154527, 2929, 5810, 5891, 5989, 811, 5820, 5596, 6090, 2904, 2919, 3161, 2895, 5419, 5653, 2742, 5841, 6171, 2932, 6082, 6041, 5751, 5607, 2740, 6014, 127859, 6074, 5992, 2923, 6099, 5814, 6314, 5833, 5573, 5377, 2894, 5423, 5479, 5835, 5782, 10328, 10656, 2912, 3020, 5579, 11918, 5668, 5361, 144692, 2893, 2739, 3983, 2899, 5348, 2753, 2921, 164762, 7067, 10284, 3831, 9702, 3859, 3590, 3846, 3840, 5430, 142253, 3844, 164765, 3356, 3349, 2751, 3015, 3591, 3720, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 74, 75, 76, 77, 78, 80, 81, 82, 83, 84, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 98, 99, 100, 101, 102, 104, 105, 106, 107, 108, 110, 111, 112, 113, 114, 115, 116, 117, 118, 121, 122, 123, 124, 125, 126, 127, 133, 135, 136, 137, 138, 139, 141, 143, 144, 146, 147, 148, 149, 150, 151, 153, 156, 157, 158, 159, 160, 178, 180, 205, 209, 227, 228, 229, 230, 232, 234, 237, 245, 260, 268, 270, 355, 358, 360, 361, 362, 363, 378, 475, 477, 640, 641, 643, 645, 650, 707, 708, 805, 806, 836, 985, 1036, 1037, 1038, 1115, 1172, 1173, 1174, 1175, 1176, 1178, 1179, 1180, 1182, 1183, 1184, 1185, 1187, 1188, 1189, 1190, 1191, 1192, 1193, 1194, 1259, 1313, 1340, 1532, 1622, 1627, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2123, 2124, 2125, 2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2139, 2166, 2167, 2168, 2169, 2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2230, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2251, 2252, 2253, 2254, 2255, 2257, 2259, 3867, 3917, 3918, 3919, 3920, 3921, 3922, 3923, 3924, 4168, 14405, 50729, 58555, 81772, 98291, 117671, 124256, 124459, 125808, 127798, 128034, 135275, 135718, 137856, 137858, 138161, 138162, 140389, 141025, 142914, 143180, 143292, 144391, 144392, 144398, 144405, 145015, 145804, 147481, 147836, 148015, 149326, 150792, 151486, 154643, 154682, 154822, 155419, 155920, 156950, 157412, 157429, 157541, 157680, 157681, 157777, 157819, 159089, 159278, 159477, 159685, 160753, 160965, 161433, 161476, 161942, 162175, 162417, 162622, 163342, 163693, 164514]
    >>> gl.processlist.get("164799")
    {'cmdline': ['/home/nicolargo/dev/glances/.venv/bin/python3',
                 '-m',
                 'glances',
                 '-C',
                 'conf/glances.conf',
                 '--api-doc'],
     'cpu_percent': 79.9,
     'cpu_times': {'children_system': 0.01,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.32,
                   'user': 0.38},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [4096, 499712, 4096, 495616, 1],
     'key': 'pid',
     'memory_info': {'data': 114577408,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 93900800,
                     'shared': 23572480,
                     'text': 31211520,
                     'vms': 507863040},
     'memory_percent': 0.5718259543881188,
     'name': 'python3',
     'nice': 0,
     'num_threads': 3,
     'pid': 164799,
     'status': 'R',
     'time_since_update': 0.35520172119140625,
     'username': 'nicolargo'}

Processlist fields description:

* pid: Process identifier (ID)
* name: Process name
* cmdline: Command line with arguments
* username: Process owner
* num_threads: Number of threads
* cpu_percent: Process CPU consumption (returned value can be > 100.0 in case of a process running multiple threads on different CPU cores)
* memory_percent: Process memory consumption
* memory_info: Process memory information (dict with rss, vms, shared, text, lib, data, dirty keys)
* status: Process status
* nice: Process nice value
* cpu_times: Process CPU times (dict with user, system, iowait keys)
* gids: Process group IDs (dict with real, effective, saved keys)
* io_counters: Process IO counters (list with read_count, write_count, read_bytes, write_bytes, io_tag keys)
* cpu_num: CPU core number where the process is currently executing (0-based indexing)

Processlist limits:

.. code-block:: python

    >>> gl.processlist.limits
    {'history_size': 1200.0,
     'processlist_cpu_careful': 50.0,
     'processlist_cpu_critical': 90.0,
     'processlist_cpu_warning': 70.0,
     'processlist_disable': ['False'],
     'processlist_disable_stats': ['cpu_num'],
     'processlist_mem_careful': 50.0,
     'processlist_mem_critical': 90.0,
     'processlist_mem_warning': 70.0,
     'processlist_nice_warning': ['-20',
                                  '-19',
                                  '-18',
                                  '-17',
                                  '-16',
                                  '-15',
                                  '-14',
                                  '-13',
                                  '-12',
                                  '-11',
                                  '-10',
                                  '-9',
                                  '-8',
                                  '-7',
                                  '-6',
                                  '-5',
                                  '-4',
                                  '-3',
                                  '-2',
                                  '-1',
                                  '1',
                                  '2',
                                  '3',
                                  '4',
                                  '5',
                                  '6',
                                  '7',
                                  '8',
                                  '9',
                                  '10',
                                  '11',
                                  '12',
                                  '13',
                                  '14',
                                  '15',
                                  '16',
                                  '17',
                                  '18',
                                  '19'],
     'processlist_status_critical': ['Z', 'D'],
     'processlist_status_ok': ['R', 'W', 'P', 'I']}

Glances load
------------

Load stats:

.. code-block:: python

    >>> type(gl.load)
    <class 'glances.plugins.load.LoadPlugin'>
    >>> gl.load
    {'cpucore': 16,
     'min1': 0.4638671875,
     'min15': 0.68701171875,
     'min5': 0.62158203125}
    >>> gl.load.keys()
    ['min1', 'min5', 'min15', 'cpucore']
    >>> gl.load.get("min1")
    0.4638671875

Load fields description:

* min1: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute.
* min5: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes.
* min15: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes.
* cpucore: Total number of CPU core.
* min1_min: Minimum min1 observed since Glances startup.
* min1_max: Maximum min1 observed since Glances startup.
* min1_mean: Mean (average) min1 computed from the history.

Load limits:

.. code-block:: python

    >>> gl.load.limits
    {'history_size': 1200.0,
     'load_careful': 0.7,
     'load_critical': 5.0,
     'load_disable': ['False'],
     'load_warning': 1.0}

Glances sensors
---------------

Sensors stats:

.. code-block:: python

    >>> type(gl.sensors)
    <class 'glances.plugins.sensors.SensorsPlugin'>
    >>> gl.sensors
    Return a dict of dict with key=<label>
    >>> gl.sensors.keys()
    ['Ambient', 'Ambient 3', 'Ambient 5', 'Ambient 6', 'CPU', 'Composite', 'Core 0', 'Core 4', 'Core 8', 'Core 12', 'Core 16', 'Core 20', 'Core 28', 'Core 29', 'Core 30', 'Core 31', 'HDD', 'Package id 0', 'SODIMM', 'Sensor 1', 'Sensor 2', 'dell_smm 0', 'dell_smm 1', 'dell_smm 2', 'dell_smm 3', 'dell_smm 4', 'dell_smm 5', 'dell_smm 6', 'dell_smm 7', 'dell_smm 8', 'dell_smm 9', 'i915 0', 'iwlwifi_1 0', 'temp', 'CPU Fan', 'Video Fan', 'BAT BAT0']
    >>> gl.sensors.get("Ambient")
    {'critical': None,
     'key': 'label',
     'label': 'Ambient',
     'type': 'temperature_core',
     'unit': 'C',
     'value': 40,
     'warning': 0}

Sensors fields description:

* label: Sensor label
* unit: Sensor unit
* value: Sensor value
* warning: System warning threshold (regardless of the user configuration in the glances.conf file)
* critical: System critical threshold (regardless of the user configuration in the glances.conf file)
* type: Sensor type (one of battery, temperature_core, fan_speed)

Sensors limits:

.. code-block:: python

    >>> gl.sensors.limits
    {'history_size': 1200.0,
     'sensors_battery_careful': 70.0,
     'sensors_battery_critical': 90.0,
     'sensors_battery_warning': 80.0,
     'sensors_disable': ['False'],
     'sensors_hide': ['unknown.*'],
     'sensors_refresh': 10.0,
     'sensors_temperature_core_careful': 45.0,
     'sensors_temperature_core_critical': 80.0,
     'sensors_temperature_core_warning': 65.0,
     'sensors_temperature_hdd_careful': 45.0,
     'sensors_temperature_hdd_critical': 60.0,
     'sensors_temperature_hdd_warning': 52.0}

Glances uptime
--------------

Uptime stats:

.. code-block:: python

    >>> type(gl.uptime)
    <class 'glances.plugins.uptime.UptimePlugin'>
    >>> gl.uptime
    '1 day, 0:49:56'

Uptime limits:

.. code-block:: python

    >>> gl.uptime.limits
    {'history_size': 1200.0}

Glances now
-----------

Now stats:

.. code-block:: python

    >>> type(gl.now)
    <class 'glances.plugins.now.NowPlugin'>
    >>> gl.now
    {'custom': '2026-04-19 09:37:35 CEST', 'iso': '2026-04-19T09:37:35+02:00'}
    >>> gl.now.keys()
    ['iso', 'custom']
    >>> gl.now.get("iso")
    '2026-04-19T09:37:35+02:00'

Now fields description:

* custom: Current date in custom format.
* iso: Current date in ISO 8601 format.

Now limits:

.. code-block:: python

    >>> gl.now.limits
    {'history_size': 1200.0}

Glances fs
----------

Fs stats:

.. code-block:: python

    >>> type(gl.fs)
    <class 'glances.plugins.fs.FsPlugin'>
    >>> gl.fs
    Return a dict of dict with key=<mnt_point>
    >>> gl.fs.keys()
    ['/', '/zsfpool']
    >>> gl.fs.get("/")
    {'device_name': '/dev/mapper/ubuntu--vg-ubuntu--lv',
     'free': 543400046592,
     'fs_type': 'ext4',
     'key': 'mnt_point',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 43.0,
     'size': 1003736440832,
     'used': 409273888768}

Fs fields description:

* device_name: Device name.
* fs_type: File system type.
* mnt_point: Mount point.
* options: Mount options.
* size: Total size.
* used: Used size.
* free: Free size.
* percent: File system usage in percent.

Fs limits:

.. code-block:: python

    >>> gl.fs.limits
    {'fs_careful': 50.0,
     'fs_critical': 90.0,
     'fs_disable': ['False'],
     'fs_hide': ['/boot.*', '.*/snap.*'],
     'fs_refresh': 60.0,
     'fs_warning': 70.0,
     'history_size': 1200.0}

Glances wifi
------------

Wifi stats:

.. code-block:: python

    >>> type(gl.wifi)
    <class 'glances.plugins.wifi.WifiPlugin'>
    >>> gl.wifi
    Return a dict of dict with key=<ssid>
    >>> gl.wifi.keys()
    ['wlp0s20f3']
    >>> gl.wifi.get("wlp0s20f3")
    {'key': 'ssid',
     'quality_level': -57.0,
     'quality_link': 53.0,
     'ssid': 'wlp0s20f3'}

Wifi limits:

.. code-block:: python

    >>> gl.wifi.limits
    {'history_size': 1200.0,
     'wifi_careful': -65.0,
     'wifi_critical': -85.0,
     'wifi_disable': ['False'],
     'wifi_warning': -75.0}

Glances ip
----------

Ip stats:

.. code-block:: python

    >>> type(gl.ip)
    <class 'glances.plugins.ip.IpPlugin'>
    >>> gl.ip
    {'address': '192.168.1.26', 'mask': '255.255.255.0', 'mask_cidr': 24}
    >>> gl.ip.keys()
    ['address', 'mask', 'mask_cidr']
    >>> gl.ip.get("address")
    '192.168.1.26'

Ip fields description:

* address: Private IP address
* mask: Private IP mask
* mask_cidr: Private IP mask in CIDR format
* gateway: Private IP gateway
* public_address: Public IP address
* public_info_human: Public IP information

Ip limits:

.. code-block:: python

    >>> gl.ip.limits
    {'history_size': 1200.0,
     'ip_disable': ['False'],
     'ip_public_api': ['https://ipv4.ipleak.net/json/'],
     'ip_public_disabled': ['True'],
     'ip_public_field': ['ip'],
     'ip_public_refresh_interval': 300.0,
     'ip_public_template': ['{continent_name}/{country_name}/{city_name}'],
     'ip_refresh': 60.0}

Glances version
---------------

Version stats:

.. code-block:: python

    >>> type(gl.version)
    <class 'glances.plugins.version.VersionPlugin'>
    >>> gl.version
    '4.5.4'

Version limits:

.. code-block:: python

    >>> gl.version.limits
    {'history_size': 1200.0}

Glances psutilversion
---------------------

Psutilversion stats:

.. code-block:: python

    >>> type(gl.psutilversion)
    <class 'glances.plugins.psutilversion.PsutilversionPlugin'>
    >>> gl.psutilversion
    '7.2.2'

Psutilversion limits:

.. code-block:: python

    >>> gl.psutilversion.limits
    {'history_size': 1200.0}

Glances core
------------

Core stats:

.. code-block:: python

    >>> type(gl.core)
    <class 'glances.plugins.core.CorePlugin'>
    >>> gl.core
    {'log': 16, 'phys': 10}
    >>> gl.core.keys()
    ['phys', 'log']
    >>> gl.core.get("phys")
    10

Core fields description:

* phys: Number of physical cores (hyper thread CPUs are excluded).
* log: Number of logical CPU cores. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core.

Core limits:

.. code-block:: python

    >>> gl.core.limits
    {'history_size': 1200.0}

Glances mem
-----------

Mem stats:

.. code-block:: python

    >>> type(gl.mem)
    <class 'glances.plugins.mem.MemPlugin'>
    >>> gl.mem
    {'active': 5243355136,
     'available': 5971815400,
     'buffers': 269574144,
     'cached': 6832290664,
     'free': 938921984,
     'inactive': 7583997952,
     'percent': 63.6,
     'percent_max': 63.6,
     'percent_mean': 63.6,
     'percent_min': 63.6,
     'shared': 1811132416,
     'total': 16421220352,
     'used': 10449404952}
    >>> gl.mem.keys()
    ['total', 'available', 'percent', 'used', 'free', 'active', 'inactive', 'buffers', 'cached', 'shared', 'percent_min', 'percent_max', 'percent_mean']
    >>> gl.mem.get("total")
    16421220352

Mem fields description:

* total: Total physical memory available.
* available: The actual amount of available memory that can be given instantly to processes that request more memory in bytes; this is calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux) and it is supposed to be used to monitor actual memory usage in a cross platform fashion.
* percent: The percentage usage calculated as (total - available) / total * 100.
* used: Memory used, calculated differently depending on the platform and designed for informational purposes only.
* free: Memory not being used at all (zeroed) that is readily available; note that this doesn't reflect the actual memory available (use 'available' instead).
* active: *(UNIX)*: memory currently in use or very recently used, and so it is in RAM.
* inactive: *(UNIX)*: memory that is marked as not used.
* buffers: *(Linux, BSD)*: cache for things like file system metadata.
* cached: *(Linux, BSD)*: cache for various things (including ZFS cache).
* wired: *(BSD, macOS)*: memory that is marked to always stay in RAM. It is never moved to disk.
* shared: *(BSD)*: memory that may be simultaneously accessed by multiple processes.
* percent_min: Minimum percent observed since Glances startup.
* percent_max: Maximum percent observed since Glances startup.
* percent_mean: Mean (average) percent computed from the history.

Mem limits:

.. code-block:: python

    >>> gl.mem.limits
    {'history_size': 1200.0,
     'mem_careful': 50.0,
     'mem_critical': 90.0,
     'mem_disable': ['False'],
     'mem_warning': 70.0}

Glances folders
---------------

Folders stats:

.. code-block:: python

    >>> type(gl.folders)
    <class 'glances.plugins.folders.FoldersPlugin'>
    >>> gl.folders
    []

Folders fields description:

* path: Absolute path.
* size: Folder size in bytes.
* refresh: Refresh interval in seconds.
* errno: Return code when retrieving folder size (0 is no error).
* careful: Careful threshold in MB.
* warning: Warning threshold in MB.
* critical: Critical threshold in MB.

Folders limits:

.. code-block:: python

    >>> gl.folders.limits
    {'folders_disable': ['False'], 'folders_refresh': 60.0, 'history_size': 1200.0}

Glances quicklook
-----------------

Quicklook stats:

.. code-block:: python

    >>> type(gl.quicklook)
    <class 'glances.plugins.quicklook.QuicklookPlugin'>
    >>> gl.quicklook
    {'cpu': 6.6,
     'cpu_hz': 4475000000.0,
     'cpu_hz_current': 567079999.9999999,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'load': 4.3,
     'mem': 63.6,
     'percpu': [{'cpu_number': 0,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 21.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 5.0,
                 'total': 79.0,
                 'user': 0.0},
                {'cpu_number': 1,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0},
                {'cpu_number': 2,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0},
                {'cpu_number': 3,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0},
                {'cpu_number': 4,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 26.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 74.0,
                 'user': 1.0},
                {'cpu_number': 5,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0},
                {'cpu_number': 6,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 21.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 4.0,
                 'total': 79.0,
                 'user': 1.0},
                {'cpu_number': 7,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 12.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 8.0,
                 'total': 88.0,
                 'user': 7.0},
                {'cpu_number': 8,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 25.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 75.0,
                 'user': 2.0},
                {'cpu_number': 9,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0},
                {'cpu_number': 10,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 26.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 74.0,
                 'user': 0.0},
                {'cpu_number': 11,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0},
                {'cpu_number': 12,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 26.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 74.0,
                 'user': 0.0},
                {'cpu_number': 13,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0},
                {'cpu_number': 14,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 26.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 74.0,
                 'user': 1.0},
                {'cpu_number': 15,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 73.0,
                 'user': 0.0}],
     'swap': 9.8}
    >>> gl.quicklook.keys()
    ['cpu_name', 'cpu_hz_current', 'cpu_hz', 'cpu', 'percpu', 'mem', 'swap', 'cpu_log_core', 'cpu_phys_core', 'load']
    >>> gl.quicklook.get("cpu_name")
    '13th Gen Intel(R) Core(TM) i7-13620H'

Quicklook fields description:

* cpu: CPU percent usage
* mem: MEM percent usage
* swap: SWAP percent usage
* load: LOAD percent usage
* cpu_log_core: Number of logical CPU core
* cpu_phys_core: Number of physical CPU core
* cpu_name: CPU name
* cpu_hz_current: CPU current frequency
* cpu_hz: CPU max frequency

Quicklook limits:

.. code-block:: python

    >>> gl.quicklook.limits
    {'history_size': 1200.0,
     'quicklook_bar_char': ['▪'],
     'quicklook_cpu_careful': 50.0,
     'quicklook_cpu_critical': 90.0,
     'quicklook_cpu_warning': 70.0,
     'quicklook_disable': ['False'],
     'quicklook_list': ['cpu', 'mem', 'load'],
     'quicklook_load_careful': 70.0,
     'quicklook_load_critical': 500.0,
     'quicklook_load_warning': 100.0,
     'quicklook_mem_careful': 50.0,
     'quicklook_mem_critical': 90.0,
     'quicklook_mem_warning': 70.0,
     'quicklook_swap_careful': 50.0,
     'quicklook_swap_critical': 90.0,
     'quicklook_swap_warning': 70.0}

Glances memswap
---------------

Memswap stats:

.. code-block:: python

    >>> type(gl.memswap)
    <class 'glances.plugins.memswap.MemswapPlugin'>
    >>> gl.memswap
    {'free': 3873906688,
     'percent': 9.8,
     'sin': 14299136,
     'sout': 404652032,
     'time_since_update': 0.3477146625518799,
     'total': 4294963200,
     'used': 421056512}
    >>> gl.memswap.keys()
    ['total', 'used', 'free', 'percent', 'sin', 'sout', 'time_since_update']
    >>> gl.memswap.get("total")
    4294963200

Memswap fields description:

* total: Total swap memory.
* used: Used swap memory.
* free: Free swap memory.
* percent: Used swap memory in percentage.
* sin: The number of bytes the system has swapped in from disk (cumulative).
* sout: The number of bytes the system has swapped out from disk (cumulative).
* time_since_update: Number of seconds since last update.

Memswap limits:

.. code-block:: python

    >>> gl.memswap.limits
    {'history_size': 1200.0,
     'memswap_careful': 50.0,
     'memswap_critical': 90.0,
     'memswap_disable': ['False'],
     'memswap_warning': 70.0}

Use auto_unit to display a human-readable string with the unit
--------------------------------------------------------------

Use auto_unit() function to generate a human-readable string with the unit:

.. code-block:: python

    >>> gl.mem.get("used")
    10449404952

    >>> gl.auto_unit(gl.mem.get("used"))
    9.73G


Args:

    number (float or int): The numeric value to be converted.

    low_precision (bool, optional): If True, use lower precision for the output. Defaults to False.

    min_symbol (str, optional): The minimum unit symbol to use (e.g., 'K' for kilo). Defaults to 'K'.

    none_symbol (str, optional): The symbol to display if the number is None. Defaults to '-'.

Returns:

    str: A human-readable string representation of the number with units.


Use to display stat as a bar
----------------------------

Use bar() function to generate a bar:

.. code-block:: python

    >>> gl.bar(gl.mem["percent"])
    ■■■■■■■■■■■□□□□□□□


Args:

    value (float): The percentage value to represent in the bar (typically between 0 and 100).

    size (int, optional): The total length of the bar in characters. Defaults to 18.

    bar_char (str, optional): The character used to represent the filled portion of the bar. Defaults to '■'.

    empty_char (str, optional): The character used to represent the empty portion of the bar. Defaults to '□'.

    pre_char (str, optional): A string to prepend to the bar. Defaults to ''.

    post_char (str, optional): A string to append to the bar. Defaults to ''.

Returns:

    str: A string representing the progress bar.


Use to display top process list
-------------------------------

Use top_process() function to generate a list of top processes sorted by CPU or MEM usage:

.. code-block:: python

    >>> gl.top_process()
    [{'name': 'code', 'status': 'S', 'memory_info': {'rss': 470945792, 'vms': 1515709743104, 'shared': 138481664, 'text': 148103168, 'lib': 0, 'data': 1368666112, 'dirty': 0}, 'num_threads': 24, 'io_counters': [23345152, 122880, 23345152, 122880, 1, 108816384, 417792, 108816384, 417792, 1, 95969280, 42209280, 95969280, 42209280, 1, 486802432, 219062272, 486802432, 219062272, 1, 21748736, 20480, 21748736, 20480, 1, 36664320, 1407008768, 36664320, 1407008768, 1, 34781184, 0, 34781184, 0, 1, 2734080, 0, 2734080, 0, 1, 616448, 0, 616448, 0, 1, 121856, 0, 121856, 0, 1, 3375104, 0, 3375104, 0, 1, 3760128, 29786112, 3760128, 29786112, 1, 1240064, 0, 1240064, 0, 1, 988160, 13963264, 988160, 13963264, 1], 'pid': 9831, 'cpu_percent': 8.8, 'memory_percent': 2.8679098258531184, 'cpu_times': {'user': 599.87, 'system': 45.39, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0}, 'nice': 0, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.35520172119140625, 'cmdline': ['/snap/code/226/usr/share/code/code', '--type=zygote', '--no-sandbox'], 'username': 'nicolargo'}, {'name': 'code', 'status': 'S', 'memory_info': {'rss': 901496832, 'vms': 1501545361408, 'shared': 76783616, 'text': 148103168, 'lib': 0, 'data': 1548865536, 'dirty': 0}, 'num_threads': 12, 'io_counters': [108816384, 417792, 108816384, 417792, 1], 'pid': 10763, 'cpu_percent': 5.9, 'memory_percent': 5.489828482145685, 'cpu_times': {'user': 192.06, 'system': 12.28, 'children_user': 3.67, 'children_system': 0.79, 'iowait': 0.0}, 'nice': 0, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.35520172119140625, 'cmdline': ['/snap/code/226/usr/share/code/code', '/home/nicolargo/.vscode/extensions/ms-python.vscode-pylance-2026.2.1/dist/server.bundle.js', '--cancellationReceive=file:d9b079d6cf45532e61b65f3bc9aa4ad4171e8a2f85', '--node-ipc', '--clientProcessId=9915'], 'username': 'nicolargo'}, {'name': 'firefox', 'status': 'S', 'memory_info': {'rss': 702849024, 'vms': 30116962304, 'shared': 288358400, 'text': 659456, 'lib': 0, 'data': 955273216, 'dirty': 0}, 'num_threads': 131, 'io_counters': [788417536, 1930473472, 788417536, 1930473472, 1], 'pid': 6978, 'cpu_percent': 2.9, 'memory_percent': 4.280126622345686, 'cpu_times': {'user': 793.16, 'system': 272.93, 'children_user': 0.14, 'children_system': 0.47, 'iowait': 0.0}, 'nice': 0, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.35520172119140625, 'cmdline': ['/snap/firefox/7967/usr/lib/firefox/firefox'], 'username': 'nicolargo'}]


Args:

    limit (int, optional): The maximum number of top processes to return. Defaults to 3.

    sorted_by (str, optional): The primary key to sort processes by (e.g., 'cpu_percent').
                                Defaults to 'cpu_percent'.

    sorted_by_secondary (str, optional): The secondary key to sort processes by if primary keys are equal
                                            (e.g., 'memory_percent'). Defaults to 'memory_percent'.

Returns:

    list: A list of dictionaries representing the top processes, excluding those with 'glances' in their
            command line.

Note:

    The 'glances' process is excluded from the returned list to avoid self-generated CPU load affecting
    the results.


