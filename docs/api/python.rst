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
     'ctx_switches': 141489209,
     'guest': 0.0,
     'idle': 83.6,
     'interrupts': 134809689,
     'iowait': 0.3,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 50555335,
     'steal': 0.0,
     'syscalls': 0,
     'system': 6.7,
     'total': 13.0,
     'user': 9.2}
    >>> gl.cpu["total"]
    13.0
    >>> gl.mem["used"]
    12217220376
    >>> gl.auto_unit(gl.mem["used"])
    11.4G

If the stats return a list of items (like network interfaces or processes), you can
access them by their name:

.. code-block:: python

    >>> gl.network.keys()
    ['wlp0s20f3', 'proton0', 'ipv6leakintrf0']
    >>> gl.network["wlp0s20f3"]
    {'alias': None,
     'bytes_all': 1418,
     'bytes_all_gauge': 3814485980,
     'bytes_all_rate_per_sec': 3548.0,
     'bytes_recv': 878,
     'bytes_recv_gauge': 3426747987,
     'bytes_recv_rate_per_sec': 2197.0,
     'bytes_sent': 540,
     'bytes_sent_gauge': 387737993,
     'bytes_sent_rate_per_sec': 1351.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.39958786964416504}

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
    [{'avg': 74.17635559941367,
      'begin': 1762623475,
      'count': 2,
      'desc': '',
      'end': -1,
      'global_msg': 'EVENTS history',
      'max': 74.39152017524864,
      'min': 73.96119102357869,
      'sort': 'memory_percent',
      'state': 'WARNING',
      'sum': 148.35271119882734,
      'top': [],
      'type': 'MEM_'},
     {'avg': 36.0,
      'begin': 1762623475,
      'count': 2,
      'desc': '',
      'end': -1,
      'global_msg': 'EVENTS history',
      'max': 36.0,
      'min': 36.0,
      'sort': 'cpu_percent',
      'state': 'CRITICAL',
      'sum': 72.0,
      'top': ['python3', 'gnome-shell', 'code'],
      'type': 'SENSORS_TEMPERATURE_CORE_AMBIENT'}]

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
      'status': 0.009099,
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
    >>> gl.diskio["nvme0n1"]
    {'disk_name': 'nvme0n1',
     'key': 'disk_name',
     'read_bytes': 11793614336,
     'read_count': 653495,
     'read_latency': 0,
     'read_time': 109355,
     'write_bytes': 19190170624,
     'write_count': 1575941,
     'write_latency': 0,
     'write_time': 1227242}

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
    Return a dict of dict with key=<name>
    >>> gl.containers.keys()
    ['homeassistant']
    >>> gl.containers["homeassistant"]
    {'command': '/init',
     'cpu': {'total': 0.0},
     'cpu_percent': 0.0,
     'created': '2025-11-03T09:43:31.02993333Z',
     'engine': 'docker',
     'id': '3bf16da8d0ac1690a7a9fba938ef52d338a9e8db00a8fcba8f707d87e4886471',
     'image': ('ghcr.io/home-assistant/home-assistant:stable',),
     'io': {},
     'io_rx': None,
     'io_wx': None,
     'key': 'name',
     'memory': {},
     'memory_inactive_file': None,
     'memory_limit': None,
     'memory_percent': None,
     'memory_usage': None,
     'name': 'homeassistant',
     'network': {},
     'network_rx': None,
     'network_tx': None,
     'ports': '',
     'status': 'running',
     'uptime': '3 days'}

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
* engine: Container engine (Docker and Podman are currently supported)
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
    {'pid_max': 0, 'running': 2, 'sleeping': 417, 'thread': 2254, 'total': 574}
    >>> gl.processcount.keys()
    ['total', 'running', 'sleeping', 'thread', 'pid_max']
    >>> gl.processcount["total"]
    574

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
    []

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
    >>> gl.percpu["0"]
    {'cpu_number': 0,
     'dpc': None,
     'guest': 0.0,
     'guest_nice': 0.0,
     'idle': 38.0,
     'interrupt': None,
     'iowait': 0.0,
     'irq': 0.0,
     'key': 'cpu_number',
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 11.0,
     'total': 62.0,
     'user': 2.0}

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
     'hr_name': 'Ubuntu 24.04 64bit / Linux 6.14.0-34-generic',
     'linux_distro': 'Ubuntu 24.04',
     'os_name': 'Linux',
     'os_version': '6.14.0-34-generic',
     'platform': '64bit'}
    >>> gl.system.keys()
    ['os_name', 'hostname', 'platform', 'os_version', 'linux_distro', 'hr_name']
    >>> gl.system["os_name"]
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
    ['wlp0s20f3', 'proton0', 'ipv6leakintrf0']
    >>> gl.network["wlp0s20f3"]
    {'alias': None,
     'bytes_all': 0,
     'bytes_all_gauge': 3814485980,
     'bytes_all_rate_per_sec': 0.0,
     'bytes_recv': 0,
     'bytes_recv_gauge': 3426747987,
     'bytes_recv_rate_per_sec': 0.0,
     'bytes_sent': 0,
     'bytes_sent_gauge': 387737993,
     'bytes_sent_rate_per_sec': 0.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.0037963390350341797}

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
     'ctx_switches': 141489209,
     'guest': 0.0,
     'idle': 83.6,
     'interrupts': 134809689,
     'iowait': 0.3,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 50555335,
     'steal': 0.0,
     'syscalls': 0,
     'system': 6.7,
     'total': 13.0,
     'user': 9.2}
    >>> gl.cpu.keys()
    ['total', 'user', 'nice', 'system', 'idle', 'iowait', 'irq', 'steal', 'guest', 'ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls', 'cpucore']
    >>> gl.cpu["total"]
    13.0

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
    >>> gl.amps["Dropbox"]
    {'count': 0,
     'countmax': None,
     'countmin': 1.0,
     'key': 'name',
     'name': 'Dropbox',
     'refresh': 3.0,
     'regex': True,
     'result': None,
     'timer': 0.35003662109375}

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
    [11415, 12155, 13003, 6739, 11329, 7375, 7237, 7422, 13039, 79604, 7391, 5814, 8545, 7405, 183614, 7383, 97061, 4649, 161872, 7296, 11738, 3755, 11413, 11209, 51475, 7246, 11363, 8479, 11414, 12886, 2968, 11758, 13333, 186443, 11959, 12005, 184847, 185925, 185011, 12434, 11282, 12021, 12004, 161504, 6025, 6995, 6907, 11212, 39419, 8140, 5933, 11211, 6229, 186440, 7195, 6454, 6458, 11992, 8910, 2643, 6142, 7151, 6945, 6282, 5518, 6134, 5979, 2974, 5981, 12006, 5945, 6497, 6546, 2987, 5925, 5779, 2731, 728, 6975, 3754, 5969, 6008, 5977, 1, 2669, 5666, 5516, 5496, 3014, 2657, 6182, 2662, 2626, 5513, 2632, 6384, 54037, 7526, 5973, 5998, 2496, 6515, 5987, 6039, 5474, 3697, 2955, 5520, 6004, 2734, 5966, 2863, 2836, 6359, 2654, 3826, 3765, 51003, 6193, 6002, 5975, 6244, 5589, 2838, 2646, 2497, 784, 2655, 2629, 5906, 5815, 2495, 5531, 5765, 6036, 6230, 6206, 13354, 3519, 6319, 5991, 2622, 6149, 6132, 5968, 2651, 6215, 5745, 6253, 5777, 5652, 5992, 5593, 2639, 6341, 6386, 5514, 5446, 5749, 144633, 2621, 4461, 161273, 11996, 2754, 5829, 3520, 2620, 11782, 2494, 11739, 2625, 3934, 6998, 2506, 186436, 2649, 11226, 3767, 3775, 3791, 6968, 5503, 5600, 3776, 156437, 3771, 176753, 186439, 2963, 3196, 2504, 2966, 2718, 3686, 3197, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 41, 42, 43, 44, 45, 47, 48, 49, 50, 51, 53, 54, 55, 56, 57, 59, 60, 61, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 77, 78, 79, 80, 81, 83, 84, 85, 86, 87, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 121, 122, 123, 124, 125, 126, 127, 128, 133, 135, 136, 137, 138, 139, 140, 143, 144, 145, 146, 147, 148, 149, 152, 153, 154, 155, 156, 164, 177, 186, 187, 213, 216, 218, 242, 246, 256, 257, 258, 259, 260, 262, 263, 265, 353, 356, 359, 360, 361, 362, 365, 445, 446, 607, 612, 613, 614, 619, 663, 664, 761, 762, 793, 963, 997, 998, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1162, 1193, 1205, 1345, 1346, 1407, 1414, 1415, 1416, 1417, 1466, 1475, 1506, 1510, 1880, 1881, 1882, 1883, 1884, 1885, 1886, 1887, 1888, 1889, 1890, 1891, 1892, 1893, 1923, 1925, 1926, 1927, 1928, 1929, 1930, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2023, 2024, 2025, 2026, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039, 2042, 2043, 2044, 2046, 2047, 2048, 2054, 2055, 3476, 3478, 3803, 3850, 3851, 3852, 3853, 3854, 3855, 3856, 3857, 4225, 4508, 4594, 4597, 4607, 4608, 4616, 4647, 5463, 18896, 18897, 18898, 18925, 19095, 112706, 137195, 139938, 146812, 159359, 160981, 160983, 161001, 161010, 161016, 161022, 162213, 162224, 164678, 166110, 167501, 168703, 169997, 170590, 170634, 172358, 173690, 174010, 174162, 174620, 174767, 175618, 175684, 176103, 176456, 177054, 177430, 177522, 177853, 177915, 179500, 179801, 179993, 180835, 180836, 180837, 181376, 181684, 181893, 181997, 182096, 182273, 182312, 182326, 182426, 182812, 182962, 183066, 183122, 183190, 184159, 184160, 184289, 184446, 184842, 184843, 184846, 185221, 185352, 185614, 185999, 186082, 186227, 186459]
    >>> gl.processlist["11415"]
    {'cmdline': ['/proc/self/exe',
                 '--type=utility',
                 '--utility-sub-type=node.mojom.NodeService',
                 '--lang=en-US',
                 '--service-sandbox-type=none',
                 '--no-sandbox',
                 '--dns-result-order=ipv4first',
                 '--experimental-network-inspection',
                 '--inspect-port=0',
                 '--crashpad-handler-pid=11226',
                 '--enable-crash-reporter=864d4bb7-dd20-4851-830f-29e81dd93517,no_channel',
                 '--user-data-dir=/home/nicolargo/.config/Code',
                 '--standard-schemes=vscode-webview,vscode-file',
                 '--secure-schemes=vscode-webview,vscode-file',
                 '--cors-schemes=vscode-webview,vscode-file',
                 '--fetch-schemes=vscode-webview,vscode-file',
                 '--service-worker-schemes=vscode-webview',
                 '--code-cache-schemes=vscode-webview,vscode-file',
                 '--shared-files=v8_context_snapshot_data:100',
                 '--field-trial-handle=3,i,1837833807548475681,9806205746640435922,262144',
                 '--enable-features=DocumentPolicyIncludeJSCallStacksInCrashReports,EarlyEstablishGpuChannel,EstablishGpuChannelAsync',
                 '--disable-features=CalculateNativeWinOcclusion,FontationsLinuxSystemFonts,ScreenAIOCREnabled,SpareRendererForSitePerProcess',
                 '--variations-seed-version'],
     'cpu_percent': 12.8,
     'cpu_times': {'children_system': 390.8,
                   'children_user': 411.47,
                   'iowait': 0.0,
                   'system': 492.94,
                   'user': 4187.94},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [1471952896,
                     1401286656,
                     1471952896,
                     1401286656,
                     1,
                     130555904,
                     2252800,
                     130555904,
                     2252800,
                     1,
                     39992320,
                     184320,
                     39992320,
                     184320,
                     1,
                     77603840,
                     0,
                     77603840,
                     0,
                     1,
                     10226688,
                     0,
                     10226688,
                     0,
                     1,
                     36971520,
                     184791040,
                     36971520,
                     184791040,
                     1,
                     87132160,
                     64901120,
                     87132160,
                     64901120,
                     1,
                     3109888,
                     0,
                     3109888,
                     0,
                     1,
                     37898240,
                     0,
                     37898240,
                     0,
                     1,
                     15155200,
                     0,
                     15155200,
                     0,
                     1,
                     905216,
                     0,
                     905216,
                     0,
                     1,
                     1100800,
                     0,
                     1100800,
                     0,
                     1,
                     5189632,
                     0,
                     5189632,
                     0,
                     1,
                     5059584,
                     5304320,
                     5059584,
                     5304320,
                     1,
                     1364992,
                     0,
                     1364992,
                     0,
                     1,
                     1082368,
                     0,
                     1082368,
                     0,
                     1],
     'key': 'pid',
     'memory_info': {'data': 5432098816,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 3156586496,
                     'shared': 102801408,
                     'text': 148733952,
                     'vms': 1528154443776},
     'memory_percent': 19.220678744847536,
     'name': 'code',
     'nice': 0,
     'num_threads': 98,
     'pid': 11415,
     'status': 'S',
     'time_since_update': 0.7100718021392822,
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

Processlist limits:

.. code-block:: python

    >>> gl.processlist.limits
    {'history_size': 1200.0,
     'processlist_cpu_careful': 50.0,
     'processlist_cpu_critical': 90.0,
     'processlist_cpu_warning': 70.0,
     'processlist_disable': ['False'],
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
     'min1': 2.5869140625,
     'min15': 1.8212890625,
     'min5': 2.208984375}
    >>> gl.load.keys()
    ['min1', 'min5', 'min15', 'cpucore']
    >>> gl.load["min1"]
    2.5869140625

Load fields description:

* min1: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute.
* min5: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes.
* min15: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes.
* cpucore: Total number of CPU core.

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
    ['Ambient', 'Ambient 3', 'Ambient 5', 'Ambient 6', 'CPU', 'Composite', 'Core 0', 'Core 4', 'Core 8', 'Core 12', 'Core 16', 'Core 20', 'Core 28', 'Core 29', 'Core 30', 'Core 31', 'HDD', 'Package id 0', 'SODIMM', 'Sensor 1', 'Sensor 2', 'dell_smm 0', 'dell_smm 1', 'dell_smm 2', 'dell_smm 3', 'dell_smm 4', 'dell_smm 5', 'dell_smm 6', 'dell_smm 7', 'dell_smm 8', 'dell_smm 9', 'i915 0', 'iwlwifi_1 0', 'spd5118 0', 'CPU Fan', 'Video Fan', 'BAT BAT0']
    >>> gl.sensors["Ambient"]
    {'critical': None,
     'key': 'label',
     'label': 'Ambient',
     'type': 'temperature_core',
     'unit': 'C',
     'value': 36,
     'warning': 0}

Sensors fields description:

* label: Sensor label
* unit: Sensor unit
* value: Sensor value
* warning: Warning threshold
* critical: Critical threshold
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
     'sensors_temperature_core_ambient_careful': 4.0,
     'sensors_temperature_core_ambient_critical': 8.0,
     'sensors_temperature_core_ambient_critical_action': ['echo "{{time}} '
                                                          '{{label}} temperature '
                                                          '{{value}}{{unit}} '
                                                          'higher than '
                                                          '{{critical}}{{unit}}" > '
                                                          '/tmp/temperature.alert'],
     'sensors_temperature_core_ambient_log': ['True'],
     'sensors_temperature_core_ambient_warning': 6.0,
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
    '3 days, 20:46:25'

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
    {'custom': '2025-11-08 18:37:56 CET', 'iso': '2025-11-08T18:37:56+01:00'}
    >>> gl.now.keys()
    ['iso', 'custom']
    >>> gl.now["iso"]
    '2025-11-08T18:37:56+01:00'

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
    >>> gl.fs["/"]
    {'device_name': '/dev/mapper/ubuntu--vg-ubuntu--lv',
     'free': 706867216384,
     'fs_type': 'ext4',
     'key': 'mnt_point',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 25.8,
     'size': 1003736440832,
     'used': 245806718976}

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
    >>> gl.wifi["wlp0s20f3"]
    {'key': 'ssid',
     'quality_level': -60.0,
     'quality_link': 50.0,
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
    {'address': '192.168.1.26',
     'mask': '255.255.255.0',
     'mask_cidr': 24,
     'public_address': '',
     'public_info_human': ''}
    >>> gl.ip.keys()
    ['address', 'mask', 'mask_cidr', 'public_address', 'public_info_human']
    >>> gl.ip["address"]
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
     'ip_public_template': ['{continent_name}/{country_name}/{city_name}']}

Glances version
---------------

Version stats:

.. code-block:: python

    >>> type(gl.version)
    <class 'glances.plugins.version.VersionPlugin'>
    >>> gl.version
    '4.4.2_dev1'

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
    '7.1.3'

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
    >>> gl.core["phys"]
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
    {'active': 6243459072,
     'available': 4205646568,
     'buffers': 204169216,
     'cached': 3469065064,
     'free': 1692520448,
     'inactive': 6013091840,
     'percent': 74.4,
     'shared': 901468160,
     'total': 16422866944,
     'used': 12217220376}
    >>> gl.mem.keys()
    ['total', 'available', 'percent', 'used', 'free', 'active', 'inactive', 'buffers', 'cached', 'shared']
    >>> gl.mem["total"]
    16422866944

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
    {'folders_disable': ['False'], 'history_size': 1200.0}

Glances quicklook
-----------------

Quicklook stats:

.. code-block:: python

    >>> type(gl.quicklook)
    <class 'glances.plugins.quicklook.QuicklookPlugin'>
    >>> gl.quicklook
    {'cpu': 13.0,
     'cpu_hz': 4475000000.0,
     'cpu_hz_current': 922595062.5,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'load': 11.4,
     'mem': 74.4,
     'percpu': [{'cpu_number': 0,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 38.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 11.0,
                 'total': 62.0,
                 'user': 2.0},
                {'cpu_number': 1,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 42.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 4.0,
                 'total': 58.0,
                 'user': 4.0},
                {'cpu_number': 2,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 45.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 4.0,
                 'total': 55.0,
                 'user': 3.0},
                {'cpu_number': 3,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 51.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 49.0,
                 'user': 0.0},
                {'cpu_number': 4,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 36.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 5.0,
                 'total': 64.0,
                 'user': 10.0},
                {'cpu_number': 5,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 48.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 52.0,
                 'user': 2.0},
                {'cpu_number': 6,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 40.0,
                 'interrupt': None,
                 'iowait': 2.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 6.0,
                 'total': 60.0,
                 'user': 4.0},
                {'cpu_number': 7,
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
                 'system': 11.0,
                 'total': 79.0,
                 'user': 19.0},
                {'cpu_number': 8,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 45.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 4.0,
                 'total': 55.0,
                 'user': 2.0},
                {'cpu_number': 9,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 49.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 51.0,
                 'user': 2.0},
                {'cpu_number': 10,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 44.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.0,
                 'total': 56.0,
                 'user': 4.0},
                {'cpu_number': 11,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 51.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 49.0,
                 'user': 1.0},
                {'cpu_number': 12,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 50.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 50.0,
                 'user': 1.0},
                {'cpu_number': 13,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 48.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.0,
                 'total': 52.0,
                 'user': 2.0},
                {'cpu_number': 14,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 50.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 50.0,
                 'user': 1.0},
                {'cpu_number': 15,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 51.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 49.0,
                 'user': 1.0}],
     'swap': 66.0}
    >>> gl.quicklook.keys()
    ['cpu_name', 'cpu_hz_current', 'cpu_hz', 'cpu', 'percpu', 'mem', 'swap', 'cpu_log_core', 'cpu_phys_core', 'load']
    >>> gl.quicklook["cpu_name"]
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
     'quicklook_bar_char': ['|'],
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
    {'free': 1461514240,
     'percent': 66.0,
     'sin': 690438144,
     'sout': 3169746944,
     'time_since_update': 0.8186845779418945,
     'total': 4294963200,
     'used': 2833448960}
    >>> gl.memswap.keys()
    ['total', 'used', 'free', 'percent', 'sin', 'sout', 'time_since_update']
    >>> gl.memswap["total"]
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

    >>> gl.mem["used"]
    12217220376

    >>> gl.auto_unit(gl.mem["used"])
    11.4G


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
    ■■■■■■■■■■■■■□□□□□


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
    [{'nice': 0, 'pid': 5814, 'num_threads': 40, 'cpu_times': {'user': 1074.26, 'system': 519.88, 'children_user': 10.92, 'children_system': 2.88, 'iowait': 0.0}, 'status': 'S', 'memory_percent': 1.7639404921674557, 'io_counters': [141689856, 274432, 141689856, 274432, 1], 'cpu_percent': 51.1, 'memory_info': {'rss': 289689600, 'vms': 5983772672, 'shared': 97443840, 'text': 8192, 'lib': 0, 'data': 532787200, 'dirty': 0}, 'name': 'gnome-shell', 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.7100718021392822, 'cmdline': ['/usr/bin/gnome-shell'], 'username': 'nicolargo'}, {'nice': 0, 'pid': 11329, 'num_threads': 25, 'cpu_times': {'user': 2305.12, 'system': 171.06, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0}, 'status': 'S', 'memory_percent': 3.6975285379259053, 'io_counters': [39992320, 184320, 39992320, 184320, 1], 'cpu_percent': 35.7, 'memory_info': {'rss': 607240192, 'vms': 1519213568000, 'shared': 117051392, 'text': 148733952, 'lib': 0, 'data': 1529090048, 'dirty': 0}, 'name': 'code', 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.7100718021392822, 'cmdline': ['/snap/code/211/usr/share/code/code', '--type=zygote', '--no-sandbox'], 'username': 'nicolargo'}, {'nice': 0, 'pid': 11363, 'num_threads': 25, 'cpu_times': {'user': 513.87, 'system': 64.3, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0}, 'status': 'S', 'memory_percent': 0.6491849709526576, 'io_counters': [3109888, 0, 3109888, 0, 1], 'cpu_percent': 18.5, 'memory_info': {'rss': 106614784, 'vms': 34888216576, 'shared': 104083456, 'text': 148733952, 'lib': 0, 'data': 222760960, 'dirty': 0}, 'name': 'code', 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.7100718021392822, 'cmdline': ['/proc/self/exe', '--type=gpu-process', '--disable-gpu-sandbox', '--no-sandbox', '--crashpad-handler-pid=11226', '--enable-crash-reporter=864d4bb7-dd20-4851-830f-29e81dd93517,no_channel', '--user-data-dir=/home/nicolargo/.config/Code', '--gpu-preferences=UAAAAAAAAAAgAAAEAAAAAAAAAAAAAAAAAABgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAABAAAAAAAAAAEAAAAAAAAAAIAAAAAAAAAAgAAAAAAAAA', '--use-gl=angle', '--use-angle=swiftshader-webgl', '--shared-files', '--field-trial-handle=3,i,1837833807548475681,9806205746640435922,262144', '--enable-features=DocumentPolicyIncludeJSCallStacksInCrashReports,EarlyEstablishGpuChannel,EstablishGpuChannelAsync', '--disable-features=CalculateNativeWinOcclusion,FontationsLinuxSystemFonts,ScreenAIOCREnabled,SpareRendererForSitePerProcess', '--variations-seed-version'], 'username': 'nicolargo'}]


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


