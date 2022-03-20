.. _api:

API (Restfull/JSON) documentation
=================================

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

Note: Change request URL api/3 by api/2 if you use Glances 2.x.

GET API status
--------------

This entry point should be used to check the API status.
It will return nothing but a 200 return code if everythin is OK.

Get the Rest API status::

    # curl -I http://localhost:61208/api/3/status
    'HTTP/1.0 200 OK'

GET plugins list
----------------

Get the plugins list::

    # curl http://localhost:61208/api/3/pluginslist
    ['alert',
     'amps',
     'cloud',
     'connections',
     'core',
     'cpu',
     'diskio',
     'docker',
     'folders',
     'fs',
     'gpu',
     'help',
     'ip',
     'irq',
     'load',
     'mem',
     'memswap',
     'network',
     'now',
     'percpu',
     'ports',
     'processcount',
     'processlist',
     'psutilversion',
     'quicklook',
     'raid',
     'sensors',
     'smart',
     'system',
     'uptime',
     'wifi']

GET alert
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/alert
    [[1647162518.0,
      -1,
      'WARNING',
      'MEM',
      83.56908770208635,
      83.56908770208635,
      83.56908770208635,
      83.56908770208635,
      1,
      [],
      '',
      'memory_percent']]

GET amps
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/amps
    [{'count': 0,
      'countmax': None,
      'countmin': 1.0,
      'key': 'name',
      'name': 'Dropbox',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.21807169914245605},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.21755433082580566}]

Get a specific field::

    # curl http://localhost:61208/api/3/amps/name
    {'name': ['Dropbox', 'Python', 'Conntrack', 'Nginx', 'Systemd', 'SystemV']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/amps/name/Dropbox
    {'Dropbox': [{'count': 0,
                  'countmax': None,
                  'countmin': 1.0,
                  'key': 'name',
                  'name': 'Dropbox',
                  'refresh': 3.0,
                  'regex': True,
                  'result': None,
                  'timer': 0.21807169914245605}]}

GET core
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/core
    {'log': 4, 'phys': 2}

Fields descriptions:

* **phys**: Number of physical cores (hyper thread CPUs are excluded) (unit is *number*)
* **log**: Number of logical CPUs. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/core/phys
    {'phys': 2}

GET cpu
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/cpu
    {'cpucore': 4,
     'ctx_switches': 0,
     'guest': 0.0,
     'guest_nice': 0.0,
     'idle': 50.1,
     'interrupts': 0,
     'iowait': 0.2,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 2.1,
     'steal': 0.0,
     'syscalls': 0,
     'system': 10.5,
     'time_since_update': 1,
     'total': 47.4,
     'user': 37.1}

Fields descriptions:

* **total**: Sum of all CPU percentages (except idle) (unit is *percent*)
* **system**: percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel (unit is *percent*)
* **user**: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries) (unit is *percent*)
* **iowait**: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete (unit is *percent*)
* **idle**: percent of CPU used by any program. Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle (unit is *percent*)
* **irq**: *(Linux and BSD)*: percent time spent servicing/handling hardware/software interrupts. Time servicing interrupts (hardware + software) (unit is *percent*)
* **nice**: *(Unix)*: percent time occupied by user level processes with a positive nice value. The time the CPU has spent running users' processes that have been *niced* (unit is *percent*)
* **steal**: *(Linux)*: percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor (unit is *percent*)
* **ctx_switches**: number of context switches (voluntary + involuntary) per second. A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict (unit is *number*)
* **interrupts**: number of interrupts per second (unit is *number*)
* **soft_interrupts**: number of software interrupts per second. Always set to 0 on Windows and SunOS (unit is *number*)
* **syscalls**: number of system calls per second. Always 0 on Linux OS (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/cpu/total
    {'total': 47.4}

GET diskio
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/diskio
    [{'disk_name': 'sda',
      'key': 'disk_name',
      'read_bytes': 0,
      'read_count': 0,
      'time_since_update': 1,
      'write_bytes': 0,
      'write_count': 0},
     {'disk_name': 'sda1',
      'key': 'disk_name',
      'read_bytes': 0,
      'read_count': 0,
      'time_since_update': 1,
      'write_bytes': 0,
      'write_count': 0}]

Get a specific field::

    # curl http://localhost:61208/api/3/diskio/disk_name
    {'disk_name': ['sda', 'sda1', 'sda2', 'sda5', 'dm-0', 'dm-1']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/diskio/disk_name/sda
    {'sda': [{'disk_name': 'sda',
              'key': 'disk_name',
              'read_bytes': 0,
              'read_count': 0,
              'time_since_update': 1,
              'write_bytes': 0,
              'write_count': 0}]}

GET docker
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/docker
    [{'Command': ['/run.sh'],
      'Id': 'c5db5cb8ee2e24116afba117052906a4fe48332ead4c127c976f5830a29bde8b',
      'Image': ['grafana/grafana:latest'],
      'Names': ['grafana'],
      'Status': 'running',
      'Uptime': '2 hours',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': 26775552,
      'name': 'grafana',
      'network_rx': None,
      'network_tx': None},
     {'Command': ['/entrypoint.sh', 'telegraf'],
      'Id': '5ccd463cb46e92731f791e5f2ff8f99e892aefe1c1cefedf8b95e4543b157048',
      'Image': ['telegraf:latest'],
      'Names': ['telegraf'],
      'Status': 'running',
      'Uptime': '2 hours',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': None,
      'name': 'telegraf',
      'network_rx': None,
      'network_tx': None}]

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
      'free': 79357321216,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 65.6,
      'size': 243396149248,
      'used': 151651373056},
     {'device_name': '/dev/loop31',
      'free': 0,
      'fs_type': 'squashfs',
      'key': 'mnt_point',
      'mnt_point': '/media/nicolargo/disk',
      'percent': 100.0,
      'size': 115867648,
      'used': 115867648}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/', '/media/nicolargo/disk']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 79357321216,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 65.6,
            'size': 243396149248,
            'used': 151651373056}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {'address': '192.168.0.33',
     'gateway': '192.168.0.254',
     'mask': '255.255.255.0',
     'mask_cidr': 24,
     'public_address': '91.166.228.228'}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/address
    {'address': '192.168.0.33'}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {'cpucore': 4, 'min1': 1.09, 'min15': 0.95, 'min5': 0.82}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 1.09}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 5110333440,
     'available': 1289662464,
     'buffers': 140845056,
     'cached': 1429409792,
     'free': 1289662464,
     'inactive': 1382371328,
     'percent': 83.6,
     'shared': 616169472,
     'total': 7849000960,
     'used': 6559338496}

Fields descriptions:

* **total**: Total physical memory available (unit is *bytes*)
* **available**: The actual amount of available memory that can be given instantly to processes that request more memory in bytes; this is calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux) and it is supposed to be used to monitor actual memory usage in a cross platform fashion (unit is *bytes*)
* **percent**: The percentage usage calculated as (total - available) / total * 100 (unit is *percent*)
* **used**: Memory used, calculated differently depending on the platform and designed for informational purposes only (unit is *bytes*)
* **free**: Memory not being used at all (zeroed) that is readily available; note that this doesn't reflect the actual memory available (use 'available' instead) (unit is *bytes*)
* **active**: *(UNIX)*: memory currently in use or very recently used, and so it is in RAM (unit is *bytes*)
* **inactive**: *(UNIX)*: memory that is marked as not used (unit is *bytes*)
* **buffers**: *(Linux, BSD)*: cache for things like file system metadata (unit is *bytes*)
* **cached**: *(Linux, BSD)*: cache for various things (unit is *bytes*)
* **wired**: *(BSD, macOS)*: memory that is marked to always stay in RAM. It is never moved to disk (unit is *bytes*)
* **shared**: *(BSD)*: memory that may be simultaneously accessed by multiple processes (unit is *bytes*)

Get a specific field::

    # curl http://localhost:61208/api/3/mem/total
    {'total': 7849000960}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {'free': 4778168320,
     'percent': 40.9,
     'sin': 1458257920,
     'sout': 5037838336,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 3304251392}

Fields descriptions:

* **total**: Total swap memory (unit is *bytes*)
* **used**: Used swap memory (unit is *bytes*)
* **free**: Free swap memory (unit is *bytes*)
* **percent**: Used swap memory in percentage (unit is *percent*)
* **sin**: The number of bytes the system has swapped in from disk (cumulative) (unit is *bytes*)
* **sout**: The number of bytes the system has swapped out from disk (cumulative) (unit is *bytes*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/memswap/total
    {'total': 8082419712}

GET network
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/network
    [{'alias': None,
      'cumulative_cx': 0,
      'cumulative_rx': 0,
      'cumulative_tx': 0,
      'cx': 0,
      'interface_name': 'mpqemubr0',
      'is_up': False,
      'key': 'interface_name',
      'rx': 0,
      'speed': 0,
      'time_since_update': 1,
      'tx': 0},
     {'alias': None,
      'cumulative_cx': 9913133,
      'cumulative_rx': 6761848,
      'cumulative_tx': 3151285,
      'cx': 0,
      'interface_name': 'veth8c6e5a5',
      'is_up': True,
      'key': 'interface_name',
      'rx': 0,
      'speed': 10485760000,
      'time_since_update': 1,
      'tx': 0}]

Fields descriptions:

* **interface_name**: Interface name (unit is *string*)
* **alias**: Interface alias name (optional) (unit is *string*)
* **rx**: The received/input rate (in bit per second) (unit is *bps*)
* **tx**: The sent/output rate (in bit per second) (unit is *bps*)
* **cumulative_rx**: The number of bytes received through the interface (cumulative) (unit is *bytes*)
* **cumulative_tx**: The number of bytes sent through the interface (cumulative) (unit is *bytes*)
* **speed**: Maximum interface speed (in bit per second). Can return 0 on some operating-system (unit is *bps*)
* **is_up**: Is the interface up ? (unit is *bool*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/network/interface_name
    {'interface_name': ['mpqemubr0',
                        'veth8c6e5a5',
                        'veth7a2d408',
                        'lo',
                        'br-119e6ee04e05',
                        'wlp2s0',
                        'veth363497d',
                        'br-87386b77b676',
                        'docker0',
                        'br_grafana']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/mpqemubr0
    {'mpqemubr0': [{'alias': None,
                    'cumulative_cx': 0,
                    'cumulative_rx': 0,
                    'cumulative_tx': 0,
                    'cx': 0,
                    'interface_name': 'mpqemubr0',
                    'is_up': False,
                    'key': 'interface_name',
                    'rx': 0,
                    'speed': 0,
                    'time_since_update': 1,
                    'tx': 0}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    '2022-03-13 10:08:38 CET'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 66.4,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 6.5,
      'total': 33.6,
      'user': 27.1},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 22.5,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 9.0,
      'total': 77.5,
      'user': 68.5}]

Get a specific field::

    # curl http://localhost:61208/api/3/percpu/cpu_number
    {'cpu_number': [0, 1, 2, 3]}

GET ports
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/ports
    [{'description': 'DefaultGateway',
      'host': '192.168.0.254',
      'indice': 'port_0',
      'port': 0,
      'refresh': 30,
      'rtt_warning': None,
      'status': 0.008873,
      'timeout': 3}]

Get a specific field::

    # curl http://localhost:61208/api/3/ports/host
    {'host': ['192.168.0.254']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/ports/host/192.168.0.254
    {'192.168.0.254': [{'description': 'DefaultGateway',
                        'host': '192.168.0.254',
                        'indice': 'port_0',
                        'port': 0,
                        'refresh': 30,
                        'rtt_warning': None,
                        'status': 0.008873,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 290, 'thread': 1581, 'total': 348}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 348}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/usr/share/code/code',
                  '--ms-enable-electron-run-as-node',
                  '--inspect-port=0',
                  '/usr/share/code/resources/app/out/bootstrap-fork',
                  '--type=extensionHost',
                  '--skipWorkspaceStorageLock'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=2002.32, system=1061.65, children_user=641.32, children_system=1247.82, iowait=1.97),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [2013077504, 40714240, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=609710080, vms=49765212160, shared=21921792, text=125038592, lib=0, data=3049295872, dirty=0),
      'memory_percent': 7.767995992193126,
      'name': 'code',
      'nice': 0,
      'num_threads': 14,
      'pid': 224688,
      'ppid': 224567,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/share/code/code',
                  '--type=renderer',
                  '--disable-color-correct-rendering',
                  '--field-trial-handle=13126869943429715366,5011544368131150611,131072',
                  '--disable-features=CookiesWithoutSameSiteMustBeSecure,SameSiteByDefaultCookies,SpareRendererForSitePerProcess',
                  '--lang=en-US',
                  '--enable-crash-reporter=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel',
                  '--global-crash-keys=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel,_companyName=Microsoft,_productName=VSCode,_version=1.63.2',
                  '--user-data-dir=/home/nicolargo/.config/Code',
                  '--standard-schemes=vscode-webview,vscode-file',
                  '--secure-schemes=vscode-webview,vscode-file',
                  '--bypasscsp-schemes',
                  '--cors-schemes=vscode-webview,vscode-file',
                  '--fetch-schemes=vscode-webview,vscode-file',
                  '--service-worker-schemes=vscode-webview',
                  '--streaming-schemes',
                  '--app-path=/usr/share/code/resources/app',
                  '--no-sandbox',
                  '--no-zygote',
                  '--num-raster-threads=2',
                  '--enable-main-frame-before-activation',
                  '--renderer-client-id=5',
                  '--no-v8-untrusted-code-mitigations',
                  '--shared-files=v8_context_snapshot_data:100',
                  '--vscode-window-config=vscode:955bffb8-751b-45c3-a3c6-d5f7e223b9f9'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=5910.05, system=517.86, children_user=0.0, children_system=0.0, iowait=5.43),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [669085696, 3588096, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=557174784, vms=54381596672, shared=60043264, text=125038592, lib=0, data=862715904, dirty=0),
      'memory_percent': 7.098671370273345,
      'name': 'code',
      'nice': 0,
      'num_threads': 20,
      'pid': 224633,
      'ppid': 224567,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [224688,
             224633,
             221818,
             221861,
             221571,
             221865,
             225097,
             387438,
             3912,
             411872,
             387437,
             585767,
             431380,
             425921,
             224601,
             507794,
             224567,
             522296,
             429894,
             224696,
             587068,
             221653,
             387461,
             406478,
             225045,
             585026,
             223803,
             1863,
             597605,
             586935,
             585163,
             579379,
             585656,
             3729,
             585202,
             1812,
             3754,
             224770,
             368467,
             3674,
             408027,
             296602,
             224733,
             242690,
             224619,
             368421,
             583455,
             2115,
             1261,
             4004,
             4200,
             348,
             3672,
             4748,
             4084,
             1,
             583459,
             222129,
             4058,
             3972,
             1114,
             4925,
             3978,
             221247,
             1155,
             3942,
             583481,
             4077,
             1132,
             583482,
             3947,
             221222,
             4085,
             1239,
             1822,
             3658,
             3684,
             4083,
             1110,
             3302,
             3989,
             223820,
             3677,
             4112,
             585813,
             3707,
             1818,
             221629,
             585176,
             4107,
             1156,
             2063,
             341631,
             4081,
             2025,
             4097,
             3986,
             3898,
             1119,
             3642,
             4104,
             1096,
             224571,
             341616,
             1129,
             1493,
             4076,
             994,
             1150,
             260255,
             585005,
             3954,
             3951,
             224835,
             3779,
             4091,
             3695,
             224572,
             3963,
             4106,
             4157,
             585125,
             4108,
             1104,
             381,
             3752,
             1105,
             260268,
             1147,
             260265,
             4080,
             4020,
             1140,
             3870,
             3746,
             1157,
             597592,
             1121,
             4087,
             3702,
             995,
             4203,
             4231,
             1106,
             1153,
             224971,
             227435,
             221232,
             993,
             301112,
             4164,
             4976,
             1160,
             3310,
             584991,
             4088,
             3892,
             3946,
             1138,
             584954,
             1247,
             3721,
             1108,
             260277,
             3740,
             3875,
             1291,
             1255,
             4069,
             2062,
             2061,
             1368,
             584966,
             4103,
             3883,
             584978,
             3967,
             3725,
             585151,
             1097,
             597604,
             2304,
             3716,
             1835,
             1864,
             1849,
             509862,
             3662,
             2265,
             1164,
             1295,
             3849,
             965,
             224574,
             375,
             2,
             3,
             4,
             6,
             9,
             10,
             11,
             12,
             13,
             14,
             15,
             16,
             17,
             18,
             20,
             21,
             22,
             23,
             24,
             27,
             28,
             29,
             30,
             33,
             34,
             35,
             36,
             37,
             38,
             39,
             40,
             41,
             42,
             90,
             91,
             92,
             94,
             95,
             96,
             97,
             98,
             99,
             102,
             103,
             105,
             106,
             108,
             110,
             119,
             136,
             181,
             190,
             191,
             192,
             193,
             194,
             195,
             196,
             197,
             202,
             203,
             204,
             207,
             208,
             237,
             257,
             288,
             290,
             363,
             365,
             392,
             396,
             397,
             399,
             400,
             401,
             468,
             491,
             519,
             724,
             725,
             726,
             727,
             728,
             729,
             730,
             731,
             732,
             733,
             735,
             736,
             832,
             849,
             861,
             863,
             864,
             867,
             876,
             877,
             882,
             887,
             889,
             893,
             897,
             901,
             905,
             908,
             911,
             913,
             918,
             923,
             926,
             931,
             1303,
             1388,
             1390,
             1391,
             1392,
             1393,
             1394,
             1395,
             1396,
             1911,
             1917,
             2069,
             3732,
             4442,
             4619,
             7988,
             22299,
             198660,
             242630,
             243136,
             304416,
             310251,
             353156,
             438092,
             503067,
             516417,
             516662,
             579203,
             579204,
             579241,
             583317,
             583319,
             588492,
             592386,
             594712,
             594934,
             595021,
             595228,
             595330,
             597538]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/224688
    {'224688': [{'cmdline': ['/usr/share/code/code',
                             '--ms-enable-electron-run-as-node',
                             '--inspect-port=0',
                             '/usr/share/code/resources/app/out/bootstrap-fork',
                             '--type=extensionHost',
                             '--skipWorkspaceStorageLock'],
                 'cpu_percent': 0.0,
                 'cpu_times': [2002.32, 1061.65, 641.32, 1247.82, 1.97],
                 'gids': [1000, 1000, 1000],
                 'io_counters': [2013077504, 40714240, 0, 0, 0],
                 'key': 'pid',
                 'memory_info': [609710080,
                                 49765212160,
                                 21921792,
                                 125038592,
                                 0,
                                 3049295872,
                                 0],
                 'memory_percent': 7.767995992193126,
                 'name': 'code',
                 'nice': 0,
                 'num_threads': 14,
                 'pid': 224688,
                 'ppid': 224567,
                 'status': 'S',
                 'time_since_update': 1,
                 'username': 'nicolargo'}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    (5, 8, 0)

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {'cpu': 47.4,
     'cpu_hz': 3000000000.0,
     'cpu_hz_current': 2412950500.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz',
     'mem': 83.6,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 66.4,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 6.5,
                 'total': 33.6,
                 'user': 27.1},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 22.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 9.0,
                 'total': 77.5,
                 'user': 68.5},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 54.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 3.6,
                 'steal': 0.0,
                 'system': 2.7,
                 'total': 45.5,
                 'user': 39.1},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 67.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 6.8,
                 'steal': 0.0,
                 'system': 6.8,
                 'total': 32.5,
                 'user': 18.8}],
     'swap': 40.9}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 47.4}

GET sensors
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/sensors
    [{'critical': 105,
      'key': 'label',
      'label': 'acpitz 1',
      'type': 'temperature_core',
      'unit': 'C',
      'value': 27,
      'warning': 105},
     {'critical': 105,
      'key': 'label',
      'label': 'acpitz 2',
      'type': 'temperature_core',
      'unit': 'C',
      'value': 29,
      'warning': 105}]

Get a specific field::

    # curl http://localhost:61208/api/3/sensors/label
    {'label': ['acpitz 1',
               'acpitz 2',
               'CPU',
               'Ambient',
               'SODIMM',
               'Package id 0',
               'Core 0',
               'Core 1',
               'BAT BAT0']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/sensors/label/acpitz 1
    {'acpitz 1': [{'critical': 105,
                   'key': 'label',
                   'label': 'acpitz 1',
                   'type': 'temperature_core',
                   'unit': 'C',
                   'value': 27,
                   'warning': 105}]}

GET system
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/system
    {'hostname': 'XPS13-9333',
     'hr_name': 'Ubuntu 20.04 64bit',
     'linux_distro': 'Ubuntu 20.04',
     'os_name': 'Linux',
     'os_version': '5.4.0-91-generic',
     'platform': '64bit'}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {'os_name': 'Linux'}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {'seconds': 2655317}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2022-03-13T10:08:38.665608', 10.5],
                ['2022-03-13T10:08:39.754416', 10.5],
                ['2022-03-13T10:08:40.870300', 4.4]],
     'user': [['2022-03-13T10:08:38.665598', 37.1],
              ['2022-03-13T10:08:39.754413', 37.1],
              ['2022-03-13T10:08:40.870295', 12.4]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2022-03-13T10:08:39.754416', 10.5],
                ['2022-03-13T10:08:40.870300', 4.4]],
     'user': [['2022-03-13T10:08:39.754413', 37.1],
              ['2022-03-13T10:08:40.870295', 12.4]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2022-03-13T10:08:38.665608', 10.5],
                ['2022-03-13T10:08:39.754416', 10.5],
                ['2022-03-13T10:08:40.870300', 4.4]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2022-03-13T10:08:39.754416', 10.5],
                ['2022-03-13T10:08:40.870300', 4.4]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {'alert': {'history_size': 3600.0},
     'amps': {'amps_disable': ['False'], 'history_size': 3600.0},
     'cloud': {'history_size': 3600.0},
     'connections': {'connections_disable': ['True'],
                     'connections_nf_conntrack_percent_careful': 70.0,
                     'connections_nf_conntrack_percent_critical': 90.0,
                     'connections_nf_conntrack_percent_warning': 80.0,
                     'history_size': 3600.0},
     'core': {'history_size': 3600.0},
     'cpu': {'cpu_ctx_switches_careful': 160000.0,
             'cpu_ctx_switches_critical': 200000.0,
             'cpu_ctx_switches_warning': 180000.0,
             'cpu_disable': ['False'],
             'cpu_iowait_careful': 20.0,
             'cpu_iowait_critical': 25.0,
             'cpu_iowait_warning': 22.5,
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
             'history_size': 3600.0},
     'diskio': {'diskio_disable': ['False'],
                'diskio_hide': ['loop.*', '/dev/loop*'],
                'history_size': 3600.0},
     'docker': {'docker_all': ['False'],
                'docker_disable': ['False'],
                'docker_max_name_size': 20.0,
                'history_size': 3600.0},
     'folders': {'folders_disable': ['False'], 'history_size': 3600.0},
     'fs': {'fs_careful': 50.0,
            'fs_critical': 90.0,
            'fs_disable': ['False'],
            'fs_hide': ['/boot.*', '/snap.*'],
            'fs_warning': 70.0,
            'history_size': 3600.0},
     'gpu': {'gpu_disable': ['False'],
             'gpu_mem_careful': 50.0,
             'gpu_mem_critical': 90.0,
             'gpu_mem_warning': 70.0,
             'gpu_proc_careful': 50.0,
             'gpu_proc_critical': 90.0,
             'gpu_proc_warning': 70.0,
             'history_size': 3600.0},
     'help': {'history_size': 3600.0},
     'ip': {'history_size': 3600.0, 'ip_disable': ['False']},
     'irq': {'history_size': 3600.0, 'irq_disable': ['True']},
     'load': {'history_size': 3600.0,
              'load_careful': 0.7,
              'load_critical': 5.0,
              'load_disable': ['False'],
              'load_warning': 1.0},
     'mem': {'history_size': 3600.0,
             'mem_careful': 50.0,
             'mem_critical': 90.0,
             'mem_disable': ['False'],
             'mem_warning': 70.0},
     'memswap': {'history_size': 3600.0,
                 'memswap_careful': 50.0,
                 'memswap_critical': 90.0,
                 'memswap_disable': ['False'],
                 'memswap_warning': 70.0},
     'network': {'history_size': 3600.0,
                 'network_disable': ['False'],
                 'network_rx_careful': 70.0,
                 'network_rx_critical': 90.0,
                 'network_rx_warning': 80.0,
                 'network_tx_careful': 70.0,
                 'network_tx_critical': 90.0,
                 'network_tx_warning': 80.0},
     'now': {'history_size': 3600.0},
     'percpu': {'history_size': 3600.0,
                'percpu_disable': ['False'],
                'percpu_iowait_careful': 50.0,
                'percpu_iowait_critical': 90.0,
                'percpu_iowait_warning': 70.0,
                'percpu_system_careful': 50.0,
                'percpu_system_critical': 90.0,
                'percpu_system_warning': 70.0,
                'percpu_user_careful': 50.0,
                'percpu_user_critical': 90.0,
                'percpu_user_warning': 70.0},
     'ports': {'history_size': 3600.0,
               'ports_disable': ['False'],
               'ports_port_default_gateway': ['True'],
               'ports_refresh': 30.0,
               'ports_timeout': 3.0},
     'processcount': {'history_size': 3600.0, 'processcount_disable': ['False']},
     'processlist': {'history_size': 3600.0,
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
                                                  '19']},
     'psutilversion': {'history_size': 3600.0},
     'quicklook': {'history_size': 3600.0,
                   'quicklook_cpu_careful': 50.0,
                   'quicklook_cpu_critical': 90.0,
                   'quicklook_cpu_warning': 70.0,
                   'quicklook_disable': ['False'],
                   'quicklook_mem_careful': 50.0,
                   'quicklook_mem_critical': 90.0,
                   'quicklook_mem_warning': 70.0,
                   'quicklook_percentage_char': ['|'],
                   'quicklook_swap_careful': 50.0,
                   'quicklook_swap_critical': 90.0,
                   'quicklook_swap_warning': 70.0},
     'raid': {'history_size': 3600.0, 'raid_disable': ['True']},
     'sensors': {'history_size': 3600.0,
                 'sensors_battery_careful': 80.0,
                 'sensors_battery_critical': 95.0,
                 'sensors_battery_warning': 90.0,
                 'sensors_disable': ['False'],
                 'sensors_refresh': 4.0,
                 'sensors_temperature_core_careful': 60.0,
                 'sensors_temperature_core_critical': 80.0,
                 'sensors_temperature_core_warning': 70.0,
                 'sensors_temperature_hdd_careful': 45.0,
                 'sensors_temperature_hdd_critical': 60.0,
                 'sensors_temperature_hdd_warning': 52.0},
     'smart': {'history_size': 3600.0, 'smart_disable': ['True']},
     'system': {'history_size': 3600.0,
                'system_disable': ['False'],
                'system_refresh': 60},
     'uptime': {'history_size': 3600.0},
     'wifi': {'history_size': 3600.0,
              'wifi_careful': -65.0,
              'wifi_critical': -85.0,
              'wifi_disable': ['True'],
              'wifi_hide': ['lo', 'docker.*'],
              'wifi_warning': -75.0}}

Limits/thresholds for the cpu plugin::

    # curl http://localhost:61208/api/3/cpu/limits
    {'cpu_ctx_switches_careful': 160000.0,
     'cpu_ctx_switches_critical': 200000.0,
     'cpu_ctx_switches_warning': 180000.0,
     'cpu_disable': ['False'],
     'cpu_iowait_careful': 20.0,
     'cpu_iowait_critical': 25.0,
     'cpu_iowait_warning': 22.5,
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
     'history_size': 3600.0}

