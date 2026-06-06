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
     'ctx_switches': 46085823,
     'guest': 0.0,
     'idle': 93.6,
     'interrupts': 26310691,
     'iowait': 0.4,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 13059668,
     'steal': 0.0,
     'syscalls': 0,
     'system': 4.4,
     'total': 5.9,
     'user': 1.5}
    >>> gl.cpu.get("total")
    5.9
    >>> gl.mem.get("used")
    8459125432
    >>> gl.auto_unit(gl.mem.get("used"))
    7.88G

If the stats return a list of items (like network interfaces or processes), you can
access them by their name:

.. code-block:: python

    >>> gl.network.keys()
    ['wlp0s20f3', 'vethc98be9d']
    >>> gl.network["wlp0s20f3"]
    {'alias': None,
     'bytes_all': 0,
     'bytes_all_gauge': 1852099268,
     'bytes_all_rate_per_sec': 0.0,
     'bytes_recv': 0,
     'bytes_recv_gauge': 1770765857,
     'bytes_recv_rate_per_sec': 0.0,
     'bytes_sent': 0,
     'bytes_sent_gauge': 81333411,
     'bytes_sent_rate_per_sec': 0.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.17501330375671387}

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
      'host': '192.168.0.254',
      'indice': 'port_0',
      'port': 0,
      'refresh': 30,
      'rtt_warning': None,
      'status': 0.005473,
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
     'read_bytes': 6421974528,
     'read_count': 228749,
     'read_latency': 0,
     'read_time': 36036,
     'write_bytes': 6594712576,
     'write_count': 233974,
     'write_latency': 0,
     'write_time': 347445}

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
    ['confident_swirles']
    >>> gl.containers.get("confident_swirles")
    {'command': '/bin/sh -c /venv/bin/python${PYTHON_VERSION} -m glances '
                '${GLANCES_OPT}',
     'cpu': {'total': 0.0},
     'cpu_limit': None,
     'cpu_percent': 0.0,
     'created': '2026-02-08T13:57:45.724222229Z',
     'engine': 'docker',
     'id': 'eea098d4b63ec6734bd66b5b9d34f54497733d2250bc1cc66de904d9c4a0bc48',
     'image': ('nicolargo/glances:latest-full',),
     'io': {},
     'io_rx': None,
     'io_wx': None,
     'key': 'name',
     'memory': {},
     'memory_inactive_file': None,
     'memory_limit': None,
     'memory_percent': None,
     'memory_usage': None,
     'name': 'confident_swirles',
     'network': {},
     'network_rx': None,
     'network_tx': None,
     'ports': '61208->61208/tcp,61209->61209/tcp',
     'status': 'running',
     'uptime': '5 days'}

Containers fields description:

* name: Container name
* id: Container ID
* image: Container image
* status: Container status
* created: Container creation date
* command: Container command
* cpu_percent: Container CPU consumption
* cpu_limit: Container CPU limit
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
    {'pid_max': 0, 'running': 1, 'sleeping': 407, 'thread': 1893, 'total': 553}
    >>> gl.processcount.keys()
    ['total', 'running', 'sleeping', 'thread', 'pid_max']
    >>> gl.processcount.get("total")
    553

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
     'idle': 27.0,
     'interrupt': None,
     'iowait': 0.0,
     'irq': 0.0,
     'key': 'cpu_number',
     'nice': 0.0,
     'softirq': 1.0,
     'steal': 0.0,
     'system': 8.0,
     'total': 73.0,
     'user': 1.0}

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
     'hr_name': 'Ubuntu 24.04 64bit / Linux 6.17.0-29-generic',
     'linux_distro': 'Ubuntu 24.04',
     'os_name': 'Linux',
     'os_version': '6.17.0-29-generic',
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
    ['wlp0s20f3', 'vethc98be9d']
    >>> gl.network.get("wlp0s20f3")
    {'alias': None,
     'bytes_all': 0,
     'bytes_all_gauge': 1852099268,
     'bytes_all_rate_per_sec': 0.0,
     'bytes_recv': 0,
     'bytes_recv_gauge': 1770765857,
     'bytes_recv_rate_per_sec': 0.0,
     'bytes_sent': 0,
     'bytes_sent_gauge': 81333411,
     'bytes_sent_rate_per_sec': 0.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.002991199493408203}

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
     'ctx_switches': 46085823,
     'guest': 0.0,
     'idle': 93.6,
     'interrupts': 26310691,
     'iowait': 0.4,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 13059668,
     'steal': 0.0,
     'syscalls': 0,
     'system': 4.4,
     'total': 5.9,
     'user': 1.5}
    >>> gl.cpu.keys()
    ['total', 'user', 'nice', 'system', 'idle', 'iowait', 'irq', 'steal', 'guest', 'ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls', 'cpucore']
    >>> gl.cpu.get("total")
    5.9

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
     'timer': 0.22232937812805176}

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
    [75255, 129, 50158, 9811, 3995, 6946, 9903, 7208, 7291, 7298, 10697, 5767, 6193, 11191, 12883, 7250, 9634, 11124, 15754, 6406, 7218, 9902, 9654, 9901, 9846, 8483, 9994, 9696, 10433, 10717, 4729, 9740, 9666, 74225, 73684, 74785, 6007, 71693, 10597, 5923, 7991, 56765, 6229, 9636, 9637, 3420, 14940, 2985, 6404, 75252, 6144, 7194, 7191, 6728, 6295, 6127, 9082, 10713, 6439, 5938, 6468, 7362, 5954, 3414, 9690, 5465, 5955, 5907, 3090, 5943, 785, 5986, 3991, 5722, 5951, 3018, 5463, 5459, 1, 5591, 2959, 4690, 6129, 3445, 6393, 3023, 3020, 6649, 5443, 2934, 3843, 4001, 5940, 5978, 3241, 5945, 6044, 3386, 2971, 3091, 5965, 48545, 5467, 5422, 3978, 3373, 3844, 5983, 6357, 6182, 51523, 4062, 51513, 3007, 823, 5949, 6033, 5980, 5701, 6244, 3244, 2992, 5536, 2965, 2935, 5769, 6322, 2954, 6234, 3012, 6203, 5896, 6148, 5717, 2933, 6126, 27554, 8492, 6205, 5941, 3001, 5971, 5671, 2953, 6254, 5478, 5972, 5540, 5576, 10234, 10369, 5926, 3115, 2979, 10444, 5460, 71124, 5685, 5785, 4798, 4805, 4828, 2952, 4820, 2932, 5450, 2958, 4166, 9651, 7061, 2944, 2996, 75248, 71069, 4003, 4010, 4026, 3609, 75273, 4007, 5547, 4015, 51566, 75251, 3396, 2942, 3398, 3087, 3610, 3890, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 74, 75, 76, 77, 78, 80, 81, 82, 83, 84, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 98, 99, 100, 101, 102, 104, 105, 106, 107, 108, 110, 111, 112, 113, 114, 115, 116, 117, 118, 121, 122, 123, 124, 125, 126, 127, 132, 134, 135, 136, 137, 138, 140, 141, 142, 143, 144, 145, 146, 147, 148, 151, 153, 156, 157, 158, 159, 178, 179, 206, 210, 211, 230, 232, 235, 236, 237, 240, 244, 268, 270, 271, 353, 358, 361, 362, 363, 364, 443, 445, 446, 675, 676, 679, 680, 685, 718, 719, 816, 817, 848, 1031, 1049, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1058, 1059, 1060, 1061, 1062, 1063, 1064, 1112, 1315, 1333, 1334, 1355, 1376, 1377, 1378, 1379, 1463, 1546, 1619, 1621, 1681, 1686, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145, 2146, 2147, 2148, 2149, 2179, 2180, 2181, 2182, 2183, 2184, 2186, 2187, 2189, 2190, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232, 2233, 2234, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2243, 2246, 2247, 2248, 2249, 2250, 2251, 2252, 2253, 2254, 2255, 2256, 2257, 2258, 2259, 2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270, 2274, 2283, 2284, 2285, 2290, 2291, 2292, 2293, 2294, 2295, 2296, 2297, 2298, 2300, 2301, 2302, 2303, 2304, 2305, 2307, 2308, 2310, 2312, 2315, 4043, 4084, 4085, 4086, 4087, 4088, 4089, 4090, 4091, 4334, 6831, 9240, 16696, 39106, 40800, 42611, 42694, 42970, 48917, 50264, 51807, 52574, 54869, 54929, 57389, 59087, 60099, 61814, 63427, 63595, 63598, 63627, 64969, 67715, 67846, 67903, 67904, 68842, 69061, 69336, 69436, 69811, 69836, 69984, 70374, 70905, 70995, 70996, 70997, 70998, 71001, 71002, 71003, 71004, 71005, 71007, 71008, 71009, 71010, 71011, 71557, 71558, 72333, 73213, 75075, 75076, 75099]
    >>> gl.processlist.get("75255")
    {'cmdline': ['/home/nicolargo/dev/glances/.venv/bin/python3',
                 '-m',
                 'glances',
                 '-C',
                 'conf/glances.conf',
                 '--api-doc'],
     'cpu_percent': 75.6,
     'cpu_times': {'children_system': 0.01,
                   'children_user': 0.0,
                   'iowait': 0.0,
                   'system': 0.44,
                   'user': 0.38},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [0, 8192, 0, 8192, 1],
     'key': 'pid',
     'memory_info': {'data': 124387328,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 94289920,
                     'shared': 23633920,
                     'text': 31211520,
                     'vms': 585416704},
     'memory_percent': 0.5741961441057718,
     'name': 'python3',
     'nice': 0,
     'num_threads': 5,
     'pid': 75255,
     'status': 'R',
     'time_since_update': 0.4991872310638428,
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
     'min1': 0.56005859375,
     'min15': 0.61669921875,
     'min5': 0.6103515625}
    >>> gl.load.keys()
    ['min1', 'min5', 'min15', 'cpucore']
    >>> gl.load.get("min1")
    0.56005859375

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
     'value': 38,
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
    '5 days, 21:42:27'

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
    {'custom': '2026-06-06 14:49:34 CEST', 'iso': '2026-06-06T14:49:34+02:00'}
    >>> gl.now.keys()
    ['iso', 'custom']
    >>> gl.now.get("iso")
    '2026-06-06T14:49:34+02:00'

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
     'free': 530499649536,
     'fs_type': 'ext4',
     'key': 'mnt_point',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 44.3,
     'size': 1003736440832,
     'used': 422174285824}

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
     'quality_level': -67.0,
     'quality_link': 43.0,
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
    {'address': '172.17.0.1', 'mask': '255.255.0.0', 'mask_cidr': 16}
    >>> gl.ip.keys()
    ['address', 'mask', 'mask_cidr']
    >>> gl.ip.get("address")
    '172.17.0.1'

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
    '4.5.5_dev1'

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
    {'active': 6975696896,
     'available': 7962078536,
     'buffers': 339484672,
     'cached': 6701300424,
     'free': 2028904448,
     'inactive': 5744734208,
     'percent': 51.5,
     'percent_max': 51.5,
     'percent_mean': 51.5,
     'percent_min': 51.5,
     'shared': 978440192,
     'total': 16421203968,
     'used': 8459125432}
    >>> gl.mem.keys()
    ['total', 'available', 'percent', 'used', 'free', 'active', 'inactive', 'buffers', 'cached', 'shared', 'percent_min', 'percent_max', 'percent_mean']
    >>> gl.mem.get("total")
    16421203968

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
    {'cpu': 5.9,
     'cpu_hz': 4475000000.0,
     'cpu_hz_current': 526114000.00000006,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'gpu_mem': 0,
     'gpu_proc': 0,
     'load': 3.9,
     'mem': 51.5,
     'percpu': [{'cpu_number': 0,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 1.0,
                 'steal': 0.0,
                 'system': 8.0,
                 'total': 73.0,
                 'user': 1.0},
                {'cpu_number': 1,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 63.0,
                 'user': 0.0},
                {'cpu_number': 2,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 63.0,
                 'user': 0.0},
                {'cpu_number': 3,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 63.0,
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
                 'system': 0.0,
                 'total': 64.0,
                 'user': 0.0},
                {'cpu_number': 5,
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
                 'system': 0.0,
                 'total': 62.0,
                 'user': 0.0},
                {'cpu_number': 6,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 18.0,
                 'interrupt': None,
                 'iowait': 1.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 12.0,
                 'total': 82.0,
                 'user': 7.0},
                {'cpu_number': 7,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 33.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 4.0,
                 'total': 67.0,
                 'user': 0.0},
                {'cpu_number': 8,
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
                 'system': 0.0,
                 'total': 64.0,
                 'user': 1.0},
                {'cpu_number': 9,
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
                 'system': 0.0,
                 'total': 62.0,
                 'user': 0.0},
                {'cpu_number': 10,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 63.0,
                 'user': 0.0},
                {'cpu_number': 11,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 63.0,
                 'user': 0.0},
                {'cpu_number': 12,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 63.0,
                 'user': 0.0},
                {'cpu_number': 13,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 63.0,
                 'user': 1.0},
                {'cpu_number': 14,
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
                 'system': 0.0,
                 'total': 62.0,
                 'user': 1.0},
                {'cpu_number': 15,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 63.0,
                 'user': 0.0}],
     'swap': 0.0}
    >>> gl.quicklook.keys()
    ['cpu_name', 'cpu_hz_current', 'cpu_hz', 'cpu', 'percpu', 'mem', 'swap', 'cpu_log_core', 'cpu_phys_core', 'load', 'gpu_mem', 'gpu_proc']
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
* gpu_mem: Average GPU Memory consumption
* gpu_proc: Average GPU Processor consumption

Quicklook limits:

.. code-block:: python

    >>> gl.quicklook.limits
    {'history_size': 1200.0,
     'quicklook_bar_char': ['▪'],
     'quicklook_cpu_careful': 50.0,
     'quicklook_cpu_critical': 90.0,
     'quicklook_cpu_warning': 70.0,
     'quicklook_disable': ['False'],
     'quicklook_gpu_mem_careful': 50.0,
     'quicklook_gpu_mem_critical': 90.0,
     'quicklook_gpu_mem_warning': 70.0,
     'quicklook_gpu_proc_careful': 50.0,
     'quicklook_gpu_proc_critical': 90.0,
     'quicklook_gpu_proc_warning': 70.0,
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
    {'free': 4294213632,
     'percent': 0.0,
     'sin': 0,
     'sout': 790528,
     'time_since_update': 0.4233095645904541,
     'total': 4294963200,
     'used': 749568}
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
    8459125432

    >>> gl.auto_unit(gl.mem.get("used"))
    7.88G


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
    ■■■■■■■■■□□□□□□□□□


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
    [{'cpu_times': {'user': 99.34, 'system': 7.35, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0}, 'memory_info': {'rss': 711610368, 'vms': 3391684608, 'shared': 127184896, 'text': 602112, 'lib': 0, 'data': 656412672, 'dirty': 0}, 'cpu_percent': 2.1, 'pid': 50158, 'io_counters': [263168, 0, 263168, 0, 1, 8404992, 0, 8404992, 0, 1, 6502400, 0, 6502400, 0, 1], 'status': 'S', 'num_threads': 29, 'memory_percent': 4.333484739527718, 'name': 'Isolated Web Co', 'nice': 0, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.4991872310638428, 'cmdline': ['/snap/firefox/8306/usr/lib/firefox/firefox', '-contentproc', '-isForBrowser', '-prefsHandle', '0:47804', '-prefMapHandle', '1:289651', '-jsInitHandle', '2:156120', '-parentBuildID', '20260512031714', '-sandboxReporter', '3', '-chrootClient', '4', '-ipcHandle', '5', '-initialChannelId', '{9884ebfb-e16d-4846-b859-9ad96971d903}', '-parentPid', '6946', '-crashReporter', '6', '-crashHelper', '7', '-greomni', '/snap/firefox/8306/usr/lib/firefox/omni.ja', '-appomni', '/snap/firefox/8306/usr/lib/firefox/browser/omni.ja', '-appDir', '/snap/firefox/8306/usr/lib/firefox/browser', '111', 'tab'], 'username': 'nicolargo'}, {'cpu_times': {'user': 135.76, 'system': 10.86, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0}, 'memory_info': {'rss': 505200640, 'vms': 1517458186240, 'shared': 142065664, 'text': 148168704, 'lib': 0, 'data': 1334460416, 'dirty': 0}, 'cpu_percent': 2.1, 'pid': 9811, 'io_counters': [23391232, 5935104, 23391232, 5935104, 1, 603881472, 50176000, 603881472, 50176000, 1, 53470208, 12288, 53470208, 12288, 1, 72314880, 46628864, 72314880, 46628864, 1, 21482496, 24576, 21482496, 24576, 1, 49386496, 0, 49386496, 0, 1, 28405760, 1680502784, 28405760, 1680502784, 1, 2883584, 0, 2883584, 0, 1, 519168, 4096, 519168, 4096, 1, 119808, 0, 119808, 0, 1, 3379200, 0, 3379200, 0, 1, 3781632, 2666496, 3781632, 2666496, 1, 704512, 0, 704512, 0, 1, 3273728, 0, 3273728, 0, 1], 'status': 'S', 'num_threads': 25, 'memory_percent': 3.076514005821281, 'name': 'code', 'nice': 0, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.4991872310638428, 'cmdline': ['/snap/code/238/usr/share/code/code', '--type=zygote', '--no-sandbox'], 'username': 'nicolargo'}, {'cpu_times': {'user': 12.87, 'system': 6.98, 'children_user': 0.17, 'children_system': 0.22, 'iowait': 0.0}, 'memory_info': {'rss': 109641728, 'vms': 7920209920, 'shared': 58437632, 'text': 35524608, 'lib': 0, 'data': 816402432, 'dirty': 0}, 'cpu_percent': 2.1, 'pid': 3995, 'io_counters': [0, 0, 0, 0, 0], 'status': 'S', 'num_threads': 86, 'memory_percent': 0.6676838568819853, 'name': 'dockerd', 'nice': 0, 'gids': {'real': 0, 'effective': 0, 'saved': 0}, 'key': 'pid', 'time_since_update': 0.4991872310638428, 'cmdline': ['/usr/bin/dockerd', '-H', 'fd://', '--containerd=/run/containerd/containerd.sock'], 'username': 'root'}]


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


