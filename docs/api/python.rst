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
     'ctx_switches': 1012144285,
     'guest': 0.0,
     'idle': 92.5,
     'interrupts': 655694940,
     'iowait': 0.3,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 280504300,
     'steal': 0.0,
     'syscalls': 0,
     'system': 5.0,
     'total': 6.4,
     'user': 2.2}
    >>> gl.cpu.get("total")
    6.4
    >>> gl.mem.get("used")
    12980750344
    >>> gl.auto_unit(gl.mem.get("used"))
    12.1G

If the stats return a list of items (like network interfaces or processes), you can
access them by their name:

.. code-block:: python

    >>> gl.network.keys()
    ['wlp0s20f3', 'veth65928bd', 'vethd29cb30']
    >>> gl.network["wlp0s20f3"]
    {'alias': None,
     'bytes_all': 0,
     'bytes_all_gauge': 11321996470,
     'bytes_all_rate_per_sec': 0.0,
     'bytes_recv': 0,
     'bytes_recv_gauge': 10349570657,
     'bytes_recv_rate_per_sec': 0.0,
     'bytes_sent': 0,
     'bytes_sent_gauge': 972425813,
     'bytes_sent_rate_per_sec': 0.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.45229601860046387}

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
    [{'avg': 99.99537467515438,
      'begin': 1773497791,
      'count': 2,
      'desc': '',
      'end': -1,
      'global_msg': 'High swap (paging) usage',
      'max': 99.99542235891568,
      'min': 99.99532699139309,
      'sort': 'memory_percent',
      'state': 'CRITICAL',
      'sum': 199.99074935030876,
      'top': ['code', 'code', 'code'],
      'type': 'MEMSWAP'},
     {'avg': 79.03120888444045,
      'begin': 1773497791,
      'count': 2,
      'desc': '',
      'end': -1,
      'global_msg': 'High swap (paging) usage',
      'max': 79.04859438024761,
      'min': 79.0138233886333,
      'sort': 'memory_percent',
      'state': 'WARNING',
      'sum': 158.0624177688809,
      'top': [],
      'type': 'MEM'}]

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
      'status': 0.004961,
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
     'read_bytes': 46110341632,
     'read_count': 1868768,
     'read_latency': 0,
     'read_time': 685560,
     'write_bytes': 183729402880,
     'write_count': 6035415,
     'write_latency': 0,
     'write_time': 9894880}

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
    ['nats-for-glances', 'timescaledb-for-glances']
    >>> gl.containers.get("nats-for-glances")
    {'command': '/nats-server --config nats-server.conf',
     'cpu': {'total': 0.0},
     'cpu_percent': 0.0,
     'created': '2026-03-12T20:14:41.833733458Z',
     'engine': 'docker',
     'id': '5a46c40efc1cf41d855e35617b5b34ba146b78b9f8fd2a07dcfab9cd2a9d673b',
     'image': ('nats:latest',),
     'io': {},
     'io_rx': None,
     'io_wx': None,
     'key': 'name',
     'memory': {},
     'memory_inactive_file': None,
     'memory_limit': None,
     'memory_percent': None,
     'memory_usage': None,
     'name': 'nats-for-glances',
     'network': {},
     'network_rx': None,
     'network_tx': None,
     'ports': '4222->4222/tcp,6222->6222/tcp,8222->8222/tcp',
     'status': 'running',
     'uptime': 'yesterday'}

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
    {'pid_max': 0, 'running': 1, 'sleeping': 467, 'thread': 2674, 'total': 622}
    >>> gl.processcount.keys()
    ['total', 'running', 'sleeping', 'thread', 'pid_max']
    >>> gl.processcount.get("total")
    622

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
     'idle': 51.0,
     'interrupt': None,
     'iowait': 0.0,
     'irq': 0.0,
     'key': 'cpu_number',
     'nice': 0.0,
     'softirq': 0.0,
     'steal': 0.0,
     'system': 11.0,
     'total': 49.0,
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
     'hr_name': 'Ubuntu 24.04 64bit / Linux 6.17.0-14-generic',
     'linux_distro': 'Ubuntu 24.04',
     'os_name': 'Linux',
     'os_version': '6.17.0-14-generic',
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
    ['wlp0s20f3', 'veth65928bd', 'vethd29cb30']
    >>> gl.network.get("wlp0s20f3")
    {'alias': None,
     'bytes_all': 0,
     'bytes_all_gauge': 11321996470,
     'bytes_all_rate_per_sec': 0.0,
     'bytes_recv': 0,
     'bytes_recv_gauge': 10349570657,
     'bytes_recv_rate_per_sec': 0.0,
     'bytes_sent': 0,
     'bytes_sent_gauge': 972425813,
     'bytes_sent_rate_per_sec': 0.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.0033559799194335938}

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
     'ctx_switches': 1012144285,
     'guest': 0.0,
     'idle': 92.5,
     'interrupts': 655694940,
     'iowait': 0.3,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 280504300,
     'steal': 0.0,
     'syscalls': 0,
     'system': 5.0,
     'total': 6.4,
     'user': 2.2}
    >>> gl.cpu.keys()
    ['total', 'user', 'nice', 'system', 'idle', 'iowait', 'irq', 'steal', 'guest', 'ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls', 'cpucore']
    >>> gl.cpu.get("total")
    6.4

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
     'timer': 0.3915679454803467}

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
    [1137955, 381638, 1138611, 982326, 982671, 383172, 983323, 9438, 9549, 983933, 1432538, 983316, 143728, 983926, 5889, 983562, 1139328, 3653, 379849, 1139810, 982718, 1259998, 3064, 420486, 969622, 1393980, 9326, 1259956, 1139213, 1139809, 9172, 510020, 9525, 6528, 1293449, 1437972, 1434932, 1137956, 1436977, 1435697, 1139793, 1139772, 1139828, 1411683, 982681, 1138670, 1138610, 1138669, 1138706, 1437924, 970187, 1138830, 9491, 983309, 1293541, 6882, 1436599, 970188, 982637, 710, 9898, 382453, 2738, 14036, 14270, 6312, 1138820, 6527, 970193, 982633, 970197, 9397, 3078, 2726, 6637, 382500, 6021, 6921, 6189, 6107, 6037, 6502, 8901, 6070, 1, 6894, 6076, 2821, 509915, 430486, 6665, 7631, 382285, 6013, 3050, 970195, 6214, 5502, 970194, 6378, 3649, 6917, 5525, 5856, 5472, 2750, 5523, 6112, 2958, 6061, 6068, 6094, 6495, 970196, 20127, 3114, 9329, 45075, 382454, 1129232, 969602, 6273, 6087, 768, 1129212, 113930, 6466, 6058, 5526, 6064, 2931, 2719, 5655, 6066, 6135, 6079, 2715, 2822, 5519, 5537, 2747, 2558, 6092, 2722, 3727, 3432, 133836, 2755, 2933, 44462, 133846, 1138400, 6223, 3069, 6419, 6329, 2740, 5587, 6280, 113947, 5842, 5993, 578713, 6342, 6316, 5888, 6090, 1381018, 489460, 6352, 3659, 9328, 6250, 6081, 6022, 2559, 2745, 530485, 6059, 5853, 2714, 2855, 5591, 6210, 6082, 5635, 2557, 2751, 5160, 2748, 5161, 5803, 2713, 5902, 5812, 303250, 5520, 113966, 2733, 2718, 54481, 9925, 1437920, 3855, 2568, 370413, 2556, 6517, 6925, 1138235, 2743, 3691, 3660, 113969, 3673, 10324, 10325, 10323, 10326, 969581, 1408140, 3666, 1129171, 3669, 1129164, 1437923, 5598, 969574, 1129143, 1129177, 1129150, 1129156, 3248, 442184, 5509, 3058, 3061, 982491, 2566, 2803, 5195, 3249, 9344, 9874, 381929, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 74, 75, 76, 77, 78, 80, 81, 82, 83, 84, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96, 98, 99, 100, 101, 102, 104, 105, 106, 107, 108, 110, 111, 112, 113, 114, 115, 116, 117, 118, 121, 122, 123, 124, 125, 126, 127, 129, 132, 133, 134, 135, 136, 137, 139, 141, 142, 143, 144, 145, 146, 147, 148, 151, 152, 153, 154, 155, 156, 177, 178, 201, 221, 223, 251, 259, 260, 261, 262, 263, 264, 265, 267, 268, 352, 354, 357, 358, 359, 360, 437, 438, 439, 600, 601, 603, 605, 610, 643, 644, 742, 743, 776, 942, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 1027, 1162, 1235, 1302, 1303, 1365, 1370, 1371, 1372, 1373, 1454, 1460, 1479, 1484, 1910, 1911, 1912, 1913, 1914, 1915, 1916, 1917, 1918, 1919, 1920, 1921, 1922, 1923, 1924, 1925, 1926, 1927, 1928, 1957, 1958, 1959, 1960, 1961, 1962, 1964, 1965, 1966, 1967, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2025, 2026, 2027, 2028, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2055, 2056, 2068, 2073, 2074, 2075, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2084, 2085, 2086, 2087, 2088, 2090, 2092, 2093, 2096, 2097, 2099, 3695, 3756, 3757, 3758, 3759, 3760, 3761, 3762, 3763, 3999, 113942, 1342027, 1342403, 1374647, 1378022, 1378030, 1378914, 1379289, 1380729, 1380732, 1395230, 1396856, 1396964, 1398173, 1404106, 1404108, 1405476, 1406116, 1406626, 1406651, 1407102, 1409530, 1414861, 1416132, 1416145, 1417204, 1417417, 1418168, 1418340, 1420017, 1420556, 1421360, 1422104, 1422105, 1422820, 1425173, 1426193, 1426955, 1427314, 1428236, 1428394, 1428409, 1429509, 1429784, 1429908, 1429915, 1430153, 1430956, 1431271, 1431681, 1431690, 1431709, 1431760, 1433684, 1433911, 1434042, 1434313, 1434528, 1435154, 1435338, 1435339, 1435605, 1435826, 1435854, 1435855, 1436050, 1436103, 1436104]
    >>> gl.processlist.get("1137955")
    {'cmdline': ['/proc/self/exe',
                 '--type=utility',
                 '--utility-sub-type=node.mojom.NodeService',
                 '--lang=en-US',
                 '--service-sandbox-type=none',
                 '--no-sandbox',
                 '--dns-result-order=ipv4first',
                 '--experimental-network-inspection',
                 '--inspect-port=0',
                 '--crashpad-handler-pid=9344',
                 '--enable-crash-reporter=864d4bb7-dd20-4851-830f-29e81dd93517,no_channel',
                 '--user-data-dir=/home/nicolargo/.config/Code',
                 '--standard-schemes=vscode-webview,vscode-file',
                 '--secure-schemes=vscode-webview,vscode-file',
                 '--cors-schemes=vscode-webview,vscode-file',
                 '--fetch-schemes=vscode-webview,vscode-file',
                 '--service-worker-schemes=vscode-webview',
                 '--code-cache-schemes=vscode-webview,vscode-file',
                 '--shared-files=v8_context_snapshot_data:100',
                 '--field-trial-handle=3,i,14671767833276363776,4659770901268553168,262144',
                 '--enable-features=DocumentPolicyIncludeJSCallStacksInCrashReports,EarlyEstablishGpuChannel,EstablishGpuChannelAsync',
                 '--disable-features=CalculateNativeWinOcclusion,FontationsLinuxSystemFonts,ScreenAIOCREnabled,SpareRendererForSitePerProcess',
                 '--variations-seed-version'],
     'cpu_percent': 3.9,
     'cpu_times': {'children_system': 251.14,
                   'children_user': 203.4,
                   'iowait': 0.0,
                   'system': 278.65,
                   'user': 466.69},
     'gids': {'effective': 1000, 'real': 1000, 'saved': 1000},
     'io_counters': [713450496,
                     138059776,
                     713450496,
                     138059776,
                     1,
                     1112307712,
                     201498624,
                     1112307712,
                     201498624,
                     1,
                     220068864,
                     45056,
                     220068864,
                     45056,
                     1,
                     612137984,
                     385024,
                     612137984,
                     385024,
                     1,
                     843608064,
                     146182144,
                     843608064,
                     146182144,
                     1,
                     4399104,
                     0,
                     4399104,
                     0,
                     1,
                     1941093376,
                     489410560,
                     1941093376,
                     489410560,
                     1,
                     19957760,
                     20480,
                     19957760,
                     20480,
                     1,
                     577536,
                     0,
                     577536,
                     0,
                     1,
                     180942848,
                     3064614912,
                     180942848,
                     3064614912,
                     1,
                     3002368,
                     0,
                     3002368,
                     0,
                     1,
                     43327488,
                     0,
                     43327488,
                     0,
                     1,
                     3178496,
                     0,
                     3178496,
                     0,
                     1,
                     5967872,
                     0,
                     5967872,
                     0,
                     1,
                     5281792,
                     5287936,
                     5281792,
                     5287936,
                     1,
                     3366912,
                     0,
                     3366912,
                     0,
                     1,
                     34765824,
                     0,
                     34765824,
                     0,
                     1,
                     23663616,
                     172032,
                     23663616,
                     172032,
                     1,
                     62801920,
                     29888512,
                     62801920,
                     29888512,
                     1,
                     226957312,
                     3399680,
                     226957312,
                     3399680,
                     1,
                     1024000,
                     0,
                     1024000,
                     0,
                     1],
     'key': 'pid',
     'memory_info': {'data': 2476957696,
                     'dirty': 0,
                     'lib': 0,
                     'rss': 1244323840,
                     'shared': 26652672,
                     'text': 148733952,
                     'vms': 1498174038016},
     'memory_percent': 7.577531953019751,
     'name': 'code',
     'nice': 0,
     'num_threads': 22,
     'pid': 1137955,
     'status': 'S',
     'time_since_update': 0.8119487762451172,
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
     'min1': 0.94482421875,
     'min15': 1.20166015625,
     'min5': 1.20166015625}
    >>> gl.load.keys()
    ['min1', 'min5', 'min15', 'cpucore']
    >>> gl.load.get("min1")
    0.94482421875

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
    '20 days, 3:53:11'

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
    {'custom': '2026-03-14 15:16:31 CET', 'iso': '2026-03-14T15:16:31+01:00'}
    >>> gl.now.keys()
    ['iso', 'custom']
    >>> gl.now.get("iso")
    '2026-03-14T15:16:31+01:00'

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
     'free': 552199892992,
     'fs_type': 'ext4',
     'key': 'mnt_point',
     'mnt_point': '/',
     'options': 'rw,relatime',
     'percent': 42.0,
     'size': 1003736440832,
     'used': 400474042368}

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
    >>> gl.wifi.get("wlp0s20f3")
    {'key': 'ssid',
     'quality_level': -69.0,
     'quality_link': 41.0,
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
     'ip_public_template': ['{continent_name}/{country_name}/{city_name}']}

Glances version
---------------

Version stats:

.. code-block:: python

    >>> type(gl.version)
    <class 'glances.plugins.version.VersionPlugin'>
    >>> gl.version
    '4.5.2'

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
    {'active': 7927668736,
     'available': 3440478200,
     'buffers': 197369856,
     'cached': 3582945400,
     'free': 816148480,
     'inactive': 6096363520,
     'percent': 79.0,
     'percent_max': 79.0,
     'percent_mean': 79.0,
     'percent_min': 79.0,
     'shared': 1083338752,
     'total': 16421228544,
     'used': 12980750344}
    >>> gl.mem.keys()
    ['total', 'available', 'percent', 'used', 'free', 'active', 'inactive', 'buffers', 'cached', 'shared', 'percent_min', 'percent_max', 'percent_mean']
    >>> gl.mem.get("total")
    16421228544

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
    {'folders_disable': ['False'], 'history_size': 1200.0}

Glances quicklook
-----------------

Quicklook stats:

.. code-block:: python

    >>> type(gl.quicklook)
    <class 'glances.plugins.quicklook.QuicklookPlugin'>
    >>> gl.quicklook
    {'cpu': 6.4,
     'cpu_hz': 4475000000.0,
     'cpu_hz_current': 608588000.0000001,
     'cpu_log_core': 16,
     'cpu_name': '13th Gen Intel(R) Core(TM) i7-13620H',
     'cpu_phys_core': 10,
     'load': 7.5,
     'mem': 79.0,
     'percpu': [{'cpu_number': 0,
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
                 'system': 11.0,
                 'total': 49.0,
                 'user': 0.0},
                {'cpu_number': 1,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 35.0,
                 'user': 0.0},
                {'cpu_number': 2,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 63.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 37.0,
                 'user': 0.0},
                {'cpu_number': 3,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 35.0,
                 'user': 0.0},
                {'cpu_number': 4,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 43.0,
                 'interrupt': None,
                 'iowait': 2.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 15.0,
                 'total': 57.0,
                 'user': 3.0},
                {'cpu_number': 5,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 46.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 7.0,
                 'total': 54.0,
                 'user': 13.0},
                {'cpu_number': 6,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 56.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 6.0,
                 'total': 44.0,
                 'user': 1.0},
                {'cpu_number': 7,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 63.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 37.0,
                 'user': 1.0},
                {'cpu_number': 8,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 64.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 36.0,
                 'user': 1.0},
                {'cpu_number': 9,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 66.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 34.0,
                 'user': 0.0},
                {'cpu_number': 10,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 35.0,
                 'user': 0.0},
                {'cpu_number': 11,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 35.0,
                 'user': 0.0},
                {'cpu_number': 12,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 35.0,
                 'user': 0.0},
                {'cpu_number': 13,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 35.0,
                 'user': 0.0},
                {'cpu_number': 14,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 35.0,
                 'user': 0.0},
                {'cpu_number': 15,
                 'dpc': None,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 65.0,
                 'interrupt': None,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 35.0,
                 'user': 0.0}],
     'swap': 100.0}
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
    {'free': 200704,
     'percent': 100.0,
     'sin': 3031797760,
     'sout': 9030742016,
     'time_since_update': 0.9000914096832275,
     'total': 4294963200,
     'used': 4294762496}
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
    12980750344

    >>> gl.auto_unit(gl.mem.get("used"))
    12.1G


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
    ■■■■■■■■■■■■■■□□□□


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
    [{'nice': 0, 'io_counters': [1397760, 0, 1397760, 0, 1], 'num_threads': 31, 'memory_percent': 2.8490013566673125, 'cpu_percent': 6.5, 'status': 'S', 'cpu_times': {'user': 37.55, 'system': 3.4, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0}, 'pid': 1432538, 'name': 'Isolated Web Co', 'memory_info': {'rss': 467841024, 'vms': 3232284672, 'shared': 112439296, 'text': 659456, 'lib': 0, 'data': 484286464, 'dirty': 0}, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.8119487762451172, 'cmdline': ['/snap/firefox/7967/usr/lib/firefox/firefox', '-contentproc', '-isForBrowser', '-prefsHandle', '0:47058', '-prefMapHandle', '1:282338', '-jsInitHandle', '2:227672', '-parentBuildID', '20260309231353', '-sandboxReporter', '3', '-chrootClient', '4', '-ipcHandle', '5', '-initialChannelId', '{4175ef0a-d063-4ace-8bff-6615f6494871}', '-parentPid', '982326', '-crashReporter', '6', '-crashHelper', '7', '-greomni', '/snap/firefox/7967/usr/lib/firefox/omni.ja', '-appomni', '/snap/firefox/7967/usr/lib/firefox/browser/omni.ja', '-appDir', '/snap/firefox/7967/usr/lib/firefox/browser', '483', 'tab'], 'username': 'nicolargo'}, {'nice': 0, 'io_counters': [713450496, 138059776, 713450496, 138059776, 1, 1112307712, 201498624, 1112307712, 201498624, 1, 220068864, 45056, 220068864, 45056, 1, 612137984, 385024, 612137984, 385024, 1, 843608064, 146182144, 843608064, 146182144, 1, 4399104, 0, 4399104, 0, 1, 1941093376, 489410560, 1941093376, 489410560, 1, 19957760, 20480, 19957760, 20480, 1, 577536, 0, 577536, 0, 1, 180942848, 3064614912, 180942848, 3064614912, 1, 3002368, 0, 3002368, 0, 1, 43327488, 0, 43327488, 0, 1, 3178496, 0, 3178496, 0, 1, 5967872, 0, 5967872, 0, 1, 5281792, 5287936, 5281792, 5287936, 1, 3366912, 0, 3366912, 0, 1, 34765824, 0, 34765824, 0, 1, 23663616, 172032, 23663616, 172032, 1, 62801920, 29888512, 62801920, 29888512, 1, 226957312, 3399680, 226957312, 3399680, 1, 1024000, 0, 1024000, 0, 1], 'num_threads': 22, 'memory_percent': 7.577531953019751, 'cpu_percent': 3.9, 'status': 'S', 'cpu_times': {'user': 466.69, 'system': 278.65, 'children_user': 203.4, 'children_system': 251.14, 'iowait': 0.0}, 'pid': 1137955, 'name': 'code', 'memory_info': {'rss': 1244323840, 'vms': 1498174038016, 'shared': 26652672, 'text': 148733952, 'lib': 0, 'data': 2476957696, 'dirty': 0}, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.8119487762451172, 'cmdline': ['/proc/self/exe', '--type=utility', '--utility-sub-type=node.mojom.NodeService', '--lang=en-US', '--service-sandbox-type=none', '--no-sandbox', '--dns-result-order=ipv4first', '--experimental-network-inspection', '--inspect-port=0', '--crashpad-handler-pid=9344', '--enable-crash-reporter=864d4bb7-dd20-4851-830f-29e81dd93517,no_channel', '--user-data-dir=/home/nicolargo/.config/Code', '--standard-schemes=vscode-webview,vscode-file', '--secure-schemes=vscode-webview,vscode-file', '--cors-schemes=vscode-webview,vscode-file', '--fetch-schemes=vscode-webview,vscode-file', '--service-worker-schemes=vscode-webview', '--code-cache-schemes=vscode-webview,vscode-file', '--shared-files=v8_context_snapshot_data:100', '--field-trial-handle=3,i,14671767833276363776,4659770901268553168,262144', '--enable-features=DocumentPolicyIncludeJSCallStacksInCrashReports,EarlyEstablishGpuChannel,EstablishGpuChannelAsync', '--disable-features=CalculateNativeWinOcclusion,FontationsLinuxSystemFonts,ScreenAIOCREnabled,SpareRendererForSitePerProcess', '--variations-seed-version'], 'username': 'nicolargo'}, {'nice': 0, 'io_counters': [1769553920, 3429445632, 1769553920, 3429445632, 1], 'num_threads': 6, 'memory_percent': 0.6314651533054018, 'cpu_percent': 2.6, 'status': 'S', 'cpu_times': {'user': 791.86, 'system': 53.75, 'children_user': 1214.74, 'children_system': 437.63, 'iowait': 0.0}, 'pid': 9172, 'name': 'terminator', 'memory_info': {'rss': 103694336, 'vms': 844873728, 'shared': 40357888, 'text': 3026944, 'lib': 0, 'data': 142725120, 'dirty': 0}, 'gids': {'real': 1000, 'effective': 1000, 'saved': 1000}, 'key': 'pid', 'time_since_update': 0.8119487762451172, 'cmdline': ['/usr/bin/python3', '/usr/bin/terminator'], 'username': 'nicolargo'}]


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


