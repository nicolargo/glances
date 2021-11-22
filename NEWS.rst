==============================================================================
                                Glances changelog
==============================================================================

===============
Version 3.2.5
===============

Version under development, see roadmap here:

    https://github.com/nicolargo/glances/milestone/55

===============
Version 3.2.4.1
===============

Bugs corrected:

    * Missing packaging dependency when using pip install #1955

===============
Version 3.2.4
===============

Bugs corrected:

    * Failure to start on Apple M1 Max #1939
    * Influxdb2 via SSL #1934
    * Update WebUI (security patch). Thanks to @notFloran.
    * Swith from black <> white theme with the '9' hotkey - Related to issue #976
    * Fix: Docker plugin - Invalid IO stats with Arch Linux #1945
    * Bug Fix: Docker plugin - Network stats not being displayed #1944
    * Fix Grafana CPU temperature panel #1954
    * is_disabled name fix #1949
    * Fix tipo in documentation #1932
    * distutils is deprecated in Python 3.10 #1923
    * Separate battery percentages #1920
    * Update docs and correct make docs-server target in Makefile

Enhancement requests:

    * Improve --issue by displaying the second update iteration and not the first one. More relevant
    * Improve --issue option with Python version and paths
    * Correct an issue on idle display
    * Refactor Mem + MemSwap Curse
    * Refactor CPU Curses code

Contributors for this version:
    * Nicolargo
    * RazCrimson
    * Floran Brutel
    * H4ckerxx44
    * Mohamad Mansour
    * Néfix Estrada
    * Zameer Manji

===============
Version 3.2.3.1
===============

Patch to correct issue (regression) #1922:

    * Incorrect processes disk IO stats #1922
    * DSM 6 docker error crash /sys/class/power_supply #1921

===============
Version 3.2.3
===============

Bugs corrected:

    * Docker container monitoring only show half command? #1912
    * Processor name getting cut off #1917
    * batinfo not in docker image (and in requirements files...) ? #1915
    * Glances don't send hostname (tag) to influxdb2 #1913
    * Public IP address doesn't display anymore #1910
    * Debian Docker images broken with version 3.2.2 #1905

Enhancement requests:

    * Make the process sort list configurable through the command line #1903
    * [WebUI] truncates network name #1699

===============
Version 3.2.2
===============

Bugs corrected:

    * [3.2.0/3.2.1] keybinding not working anymore #1904
    * InfluxDB/InfluxDB2 Export object has no attribute hostname #1899

Documentation: The "make docs" generate RestFull/API documentation file.

===============
Version 3.2.1
===============

Bugs corrected:

    * Glances 3.2.0 and influxdb export - Missing network data bug #1893

Enhancement requests:

    * Security audit - B411 enhancement (Monkey patch XML RPC Lib) #1025
    * Also search glances.conf file in /usr/share/doc/glances/glances.conf #1862

===============
Version 3.2.0
===============

This release is a major version (but minor number because the API did not change). It focus on
*CPU consumption*. I use `Flame profiling https://github.com/nicolargo/glances/wiki/Glances-FlameGraph`_
and code optimization to *reduce CPU consumption from 20% to 50%* depending on your system.

Enhancement and development requests:

    * Improve CPU consumption
        - Make the refresh rate configurable per plugin #1870
        - Add caching for processing username and cmdline
        - Correct and improve refresh time method
        - Set refresh rate for global CPU percent
        - Set the dafault refresh rate of system stats to 60 seconds
        - Default refresh time for sensors is refresh rate * 2
        - Improve history perf
        - Change main curses loop
        - Improve Docker client connection
        - Update Flame profiling
    * Get system sensors temperatures thresholds #1864
    * Filter data exported from Docker plugin
    * Make the Docker API connection timeout configurable
    * Add --issue to Github issue template
    * Add release-note in the Makefile
    * Add some comments in cpu_percent
    * Add some comments to the processlist.py
    * Set minimal version for PSUtil to 5.3.0
    * Add comment to default glances.conf file
    * Improve code quality #820
    * Update WebUI for security vuln

Bugs corrected:

    * Quit from help should return to main screen, not exit #1874
    * AttributeError: 'NoneType' object has no attribute 'current' #1875
    * Merge pull request #1873 from metayan/fix-history-add
    * Correct filter
    * Correct Flake8 issue in plugins
    * Pressing Q to get rid of irq not working #1792
    * Spelling correction in docs #1886
    * Starting an alias with a number causes a crash #1885
    * Network interfaces not applying in web UI #1884
    * Docker containers information missing with Docker 20.10.x #1878
    * Get system sensors temperatures thresholds #1864

Contibutors for this version:

    * Nicolargo
    * Markus Pöschl
    * Clifford W. Hansen
    * Blake
    * Yan

===============
Version 3.1.7
===============

Enhancements and bug corrected:

    * Security audit - B411 #1025 (by nicolargo)
    * GPU temperature not shown in webview #1849 (by nicolargo)
    * Remove shell=True for actions (following Bandit issue report) #1851 (by nicolargo)
    * Replace Travis by Github action #1850 (by nicolargo)
    * '/api/3/processlist/pid/3936'use this api can't get right info,all messy code #1828 (by nicolargo)
    * Refactor the way importants stats are displayed #1826 (by nicolargo)
    * Re-apply the Add hide option to sensors plugin #1596 PR (by nicolargo)
    * Smart plugin error while start glances as root #1806 (by nicolargo)
    * Plugin quicklook takes more than one seconds to update #1820 (by nicolargo)
    * Replace Pystache by Chevron 2/2  See #1817 (by nicolargo)
    * Doc. No SMART screenshot. #1799 (by nicolargo)
    * Update docs following PR #1798 (by nicolargo)

Contributors for this version:

    - Nicolargo
    - Deosrc
    - dependabot[bot]
    - Michael J. Cohen
    - Rui Chen
    - Stefan Eßer
    - Tuux

===============
Version 3.1.6.2
===============

Bugs corrected:

    * Remove bad merge for a non tested feature (see https://github.com/nicolargo/glances/issues/1787#issuecomment-774682954)

Version 3.1.6.1
===============

Bugs corrected:

    * Glances crash after installing module for shown GPU informations on Windows 10 #1800

Version 3.1.6
=============

Enhancements and new features:

    * Kill a process from the Curses interface #1444
    * Manual refresh on F5 in the Curses interface #1753
    * Hide function in sensors section #1590
    * Enhancement Request: .conf parameter for AMP #1690
    * Password for Web/Browser mode  #1674
    * Unable to connect to Influxdb 2.0 #1776
    * ci: fix release process and improve build speeds #1782
    * Cache cpuinfo output #1700
    * sort by clicking improvements and bug #1578
    * Allow embedded AMP python script to be placed in a configurable location #1734
    * Add attributes to stdout/stdout-csv plugins #1733
    * Do not shorten container names #1723

Bugs corrected:

    * Version tag for docker image packaging #1754
    * Unusual characters in cmdline cause lines to disappear and corrupt the display #1692
    * UnicodeDecodeError on any command with a utf8 character in its name #1676
    * Docker image is not up to date install #1662
    * Add option to set the strftime format #1785
    * fix: docker dev build contains all optional requirements #1779
    * GPU information is incomplete via web #1697
    * [WebUI] Fix display of null values for GPU plugin #1773
    * crash on startup on Illumos when no swap is configured #1767
    * Glances crashes with 2 GPUS bug #1683
    * [Feature Request] Filter Docker containers#1748
    * Error with IP Plugin : object has no attribute #1528
    * docker-compose #1760
    * [WebUI] Fix sort by disk io #1759
    * Connection to MQTT server failst #1705
    * Misleading image tag latest-arm needs contributor packaging #1419
    * Docker nicolargo/glances:latest missing arm builds? #1746
    * Alpine image is broken packaging #1744
    * RIP Alpine? needs contributor packaging #1741
    * Manpage improvement documentation #1743
    * Make build reproducible packaging #1740
    * Automated multiarch builds for docker #1716
    * web ui of glances is not coming #1721
    * fixing command in json.rst #1724
    * Fix container rss value #1722
    * Alpine Image is broken needs test packaging #1720
    * Fix gpu plugin to handle multiple gpus with different reporting capabilities bug #1634

Version 3.1.5
=============

Enhancements and new features:

    * Enhancement: RSS for containers enhancement #1694
    * exports: support rabbitmq amqps enhancement #1687
    * Quick Look missing CPU Infos enhancement #1685
    * Add amqps protocol suppport for rabbitmq export #1688
    * Select host in Grafana json #1684
    * Value for free disk space is counterintuative on ext file systems enhancement #644

Bugs corrected:

    * Can't start server: unexpected keyword argument 'address' bug enhancement #1693
    * class AmpsList method _build_amps_list() Windows fail (glances/amps_list.py) bug #1689
    * Fix grammar in sensors documentation #1681
    * Reflect "used percent" user disk space for [fs] alert #1680
    * Bug: [fs] plugin needs to reflect user disk space usage needs test #1658
    * Fixed formatting on FS example #1673
    * Missing temperature documentation #1664
    * Wiki page for starting as a service documentation #1661
    * How to start glances with --username option on syetemd? documentation #1657
    * tests using /etc/glances/glances.conf from already installed version bug #1654
    * Unittests: Use sys.executable instead of hardcoding the python interpreter #1655
    * Glances should not phone home install #1646
    * Add lighttpd reverse proxy config to the wiki documentation #1643
    * Undefined name 'i' in plugins/glances_gpu.py bug #1635

Version 3.1.4
=============

Enhancements and new features:

    * FS filtering can be done on device name documentation enhancement #1606
    * Feature request: Include hostname in all (e.g. kafka) exports #1594
    * Threading.isAlive was removed in Python 3.9. Use is_alive. #1585
    * log file under public/shared tmp/ folders must not have deterministic name #1575
    * Install / Systemd Debian documentation #1560
    * Display load as percentage when Irix mode is disable #1554
    * [WebUI] Add a new TCP connections status plugin new feature #1547
    * Make processes.sort_key configurable enhancement #1536
    * NVIDIA GPU temperature #1523
    * Feature request: HDD S.M.A.R.T. #1288

Bugs corrected:

    * Glances 3.1.3: when no network interface with Public address #1615
    * NameError: name 'logger' is not defined #1602
    * Disk IO stats missing after upgrade to 5.5.x kernel #1601
    * Glances don't want to run on Crostini (LXC Container, Debian 10, python 3.7.3) #1600
    * Kafka key name needs to be bytes #1593
    * Cant start glances with glances --export mqtt #1581
    * [WEBUI] AMP plugins is not displayed correctly in the Web Interface #1574
    * Unhandled AttributeError when no config files found #1569
    * Glances writing lots of Docker Error message in logs file enhancement #1561
    * GPU stats not showing on mobile web view bug needs test #1555
    * KeyError: b'Rss:' in memory_maps #1551
    * CPU usage is always 100% #1550
    * IP plugin still exporting data when disabled #1544
    * Quicklook plugin not working on Systemd #1537

Version 3.1.3
=============

Enhancements and new features:

  * Add a new TCP connections status plugin enhancement #1526
  * Add --enable-plugin option from the command line

Bugs corrected:

  * Fix custom refresh time in the web UI #1548 by notFloran
  * Fix issue in WebUI with empty docker stats #1546 by notFloran
  * Glances fails without network interface bug #1535
  * Disable option in the configuration file is now take into account

Others:

  * Sensors plugin is disable by default (high CPU consumption on some Liux distribution).

Version 3.1.2
=============

Enhancements and new features:

  * Make CSV export append instead of replace #1525
  * HDDTEMP config IP and Port #1508
  * [Feature Request] Option in config to change character used to display percentage in Quicklook #1508

Bugs corrected:
  * Cannot restart glances with --export influxdb after update to 3.1.1 bug #1530
  * ip plugin empty interface bug #1509
  * Glances Snap doesn't run on Orange Pi Zero running Ubuntu Core 16 bug #1517
  * Error with IP Plugin : object has no attribute bug #1528
  * repair the problem that when running 'glances --stdout-csv amps' #1520
  * Possible typo in glances_influxdb.py #1514

Others:

      * In debug mode (-d) all duration (init, update are now logged). Grep duration in log file.

Version 3.1.1
=============

Enhancements and new features:

    * Please add some sparklines! #1446
    * Add Load Average (similar to Linux) on Windows #344
    * Add authprovider for cassandra export (thanks to @EmilienMottet) #1395
    * Curses's browser server list sorting added (thanks to @limfreee) #1396
    * ElasticSearch: add date to index, unbreak object push (thanks to @genevera) #1438
    * Performance issue with large folder #1491
    * Can't connect to influxdb with https enabled #1497

Bugs corrected:

    * Fix Cassandra table name export #1402
    * 500 Internal Server Error /api/3/network/interface_name #1401
    * Connection to MQTT server failed : getaddrinfo() argument 2 must be integer or string #1450
    * `l` keypress (hide alert log) not working after some time #1449
    * Too less data using prometheus exporter #1462
    * Getting an error when running with prometheus exporter #1469
    * Stack trace when starts Glances on CentOS #1470
    * UnicodeEncodeError: 'ascii' codec can't encode character u'\u25cf' - Raspbian stretch #1483
    * Prometheus integration broken with latest prometheus_client #1397
    * "sorted by ?" is displayed when setting the sort criterion to "USER" #1407
    * IP plugin displays incorrect subnet mask #1417
    * Glances PsUtil ValueError on IoCounter with TASK kernel options #1440
    * Per CPU in Web UI have some display issues. #1494
    * Fan speed and voltages section? #1398

Others:

    * Documentation is unclear how to get Docker information #1386
    * Add 'all' target to the Pip install (install all dependencies)
    * Allow comma separated commands in AMP

Version 3.1
===========

Enhancements and new features:

    * Add a CSV output format to the STDOUT output mode #1363
    * Feature request: HDD S.M.A.R.T. reports (thanks to @tnibert) #1288
    * Sort docker stats #1276
    * Prohibit some plug-in data from being exported to influxdb #1368
    * Disable plugin from Glances configuration file #1378
    * Curses-browser's server list paging added (thanks to @limfreee) #1385
    * Client Browser's thread management added (thanks to @limfreee) #1391

Bugs corrected:

    * TypeError: '<' not supported between instances of 'float' and 'str' #1315
    * GPU plugin not exported to influxdb #1333
    * Crash after running fine for several hours #1335
    * Timezone listed doesn’t match system timezone, outputs wrong time #1337
    * Compare issue with Process.cpu_times() #1339
    * ERROR -- Can not grab extended stats (invalid attr name 'num_fds') #1351
    * Action on port/web plugins is not working #1358
    * Support for monochrome (serial) terminals e.g. vt220 #1362
    * TypeError on opening (Wifi plugin) #1373
    * Some field name are incorrect in CSV export #1372
    * Standard output misbehaviour (need to flush) #1376
    * Create an option to set the username to use in Web or RPC Server mode #1381
    * Missing kernel task names when the webui is switched to long process names #1371
    * Drive name with special characters causes crash #1383
    * Cannot get stats in Cloud plugin (404) #1384

Others:

    * Add Docker documentation (thanks to @rgarrigue)
    * Refactor Glances logs (now called Glances events)
    * "chart" extra dep replace by "graph" #1389

Version 3.0.2
=============

Bug corrected:

    * Glances IO Errorno 22 - Invalid argument #1326

Version 3.0.1
=============

Bug corrected:

    *  AMPs error if no output are provided by the system call #1314

Version 3.0
===========

See the release note here: https://github.com/nicolargo/glances/wiki/Glances-3.0-Release-Note

Enhancements and new features:

    * Make the left side bar width dynamic in the Curse UI #1177
    * Add threads number in the process list #1259
    * A way to have only REST API available and disable WEB GUI access #1149
    * Refactor graph export plugin (& replace Matplolib by Pygal) #697
    * Docker module doesn't export details about stopped containers #1152
    * Add dynamic fields in all sections of the configuration file #1204
    * Make plugins and export CLI option dynamical #1173
    * Add a light mode for the console UI #1165
    * Refactor InfluxDB (API is now stable) #1166
    * Add deflate compression support to the RestAPI #1182
    * Add a code of conduct for Glances project's participants #1211
    * Context switches bottleneck identification #1212
    * Take advantage of the psutil issue #1025 (Add process_iter(attrs, ad_value)) #1105
    * Nice Process Priority Configuration #1218
    * Display debug message if dep lib is not found #1224
    * Add a new output mode to stdout #1168
    * Huge refactor of the WebUI packaging thanks to @spike008t #1239
    * Add time zone to the current time #1249
    * Use HTTPs URLs to check public IP address #1253
    * Add labels support to Promotheus exporter #1255
    * Overlap in Web UI when monitoring a machine with 16 cpu threads #1265
    * Support for exporting data to a MQTT server #1305

    One more thing ! A new Grafana Dash is available with:
    * Network interface variable
    * Disk variable
    * Container CPU

Bugs corrected:

    * Crash in the Wifi plugin on my Laptop #1151
    * Failed to connect to bus: No such file or directory #1156
    * glances_plugin.py has a problem with specific docker output #1160
    * Key error 'address' in the IP plugin #1176
    * NameError: name 'mode' is not defined in case of interrupt shortly after starting the server mode #1175
    * Crash on startup: KeyError: 'hz_actual_raw' on Raspbian 9.1 #1170
    * Add missing mount-observe and system-observe interfaces #1179
    * OS specific arguments should be documented and reported #1180
    * 'ascii' codec can't encode character u'\U0001f4a9' in position 4: ordinal not in range(128) #1185
    * KeyError: 'memory_info' on stats sum #1188
    * Electron/Atom processes displayed wrong in process list #1192
    * Another encoding issue... With both Python 2 and Python 3 #1197
    * Glances do not exit when eating 'q' #1207
    * FreeBSD blackhole bug #1202
    * Glances crashes when mountpoint with non ASCII characters exists #1201
    * [WEB UI] Minor issue on the Web UI #1240
    * [Glances 3.0 RC1] Client/Server is broken #1244
    * Fixing horizontal scrolling #1248
    * Stats updated during export (thread issue) #1250
    * Glances --browser crashed when more than 40 glances servers on screen 78x45 #1256
    * OSX - Python 3 and empty percent and res #1251
    * Crashes when influxdb option set #1260
    * AMP for kernel process is not working #1261
    * Arch linux package (2.11.1-2) psutil (v5.4.1): RuntimeWarning: ignoring OSError #1203
    * Glances crash with extended process stats #1283
    * Terminal window stuck at the last accessed *protected* server #1275
    * Glances shows mdadm RAID0 as degraded when chunksize=128k and the array isn't degraded. #1299
    * Never starts in a server on Google Cloud and FreeBSD #1292

Backward-incompatible changes:

    * Support for Python 3.3 has been dropped (EOL 2017-09-29)
    * Support for psutil < 5.3.0 has been dropped
    * Minimum supported Docker API version is now 1.21 (Docker plugins)
    * Support for InfluxDB < 0.9 is deprecated (InfluxDB exporter)
    * Zeroconf lib should be pinned to 0.19.1 for Python 2.x
    * --disable-<plugin> no longer available (use --disable-plugin <plugin>)
    * --export-<exporter> no longer available (use --export <exporter>)

News command line options:

    --disable-webui  Disable the WebUI (only RESTful API will respond)
    --enable-light   Enable the light mode for the UI interface
    --modules-list   Display plugins and exporters list
    --disable-plugin plugin1,plugin2
                     Disable a list of comma separated plugins
    --export exporter1,exporter2
                     Export stats to a comma separated exporters
    --stdout plugin1,plugin2.attribute
                     Display stats to stdout

News configuration keys in the glances.conf file:

Graph:

    [graph]
    # Configuration for the --export graph option
    # Set the path where the graph (.svg files) will be created
    # Can be overwrite by the --graph-path command line option
    path=/tmp
    # It is possible to generate the graphs automatically by setting the
    # generate_every to a non zero value corresponding to the seconds between
    # two generation. Set it to 0 to disable graph auto generation.
    generate_every=60
    # See followings configuration keys definitions in the Pygal lib documentation
    # http://pygal.org/en/stable/documentation/index.html
    width=800
    height=600
    style=DarkStyle

Processes list Nice value:

    [processlist]
    # Nice priorities range from -20 to 19.
    # Configure nice levels using a comma separated list.
    #
    # Nice: Example 1, non-zero is warning (default behavior)
    nice_warning=-20,-19,-18,-17,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19
    #
    # Nice: Example 2, low priority processes escalate from careful to critical
    #nice_careful=1,2,3,4,5,6,7,8,9
    #nice_warning=10,11,12,13,14
    #nice_critical=15,16,17,18,19

Docker plugin (related to #1152)

    [docker]
    # By default, Glances only display running containers
    # Set the following key to True to display all containers
    all=False

All configuration file values (related to #1204)

    [influxdb]
    # It is possible to use dynamic system command
    prefix=`hostname`
    tags=foo:bar,spam:eggs,system:`uname -a`

==============================================================================
Glances Version 2
==============================================================================

Version 2.11.1
==============

    * [WebUI] Sensors not showing on Web (issue #1142)
    * Client and Quiet mode don't work together (issue #1139)

Version 2.11
============

Enhancements and new features:

    * New export plugin: standard and configurable RESTful exporter (issue #1129)
    * Add a JSON export module (issue #1130)
    * [WIP] Refactoring of the WebUI

Bugs corrected:

    * Installing GPU plugin crashes entire Glances (issue #1102)
    * Potential memory leak in Windows WebUI (issue #1056)
    * glances_network `OSError: [Errno 19] No such device` (issue #1106)
    * GPU plugin. <class 'TypeError'>: ... not JSON serializable"> (issue #1112)
    * PermissionError on macOS (issue #1120)
    * Cant move up or down in glances --browser (issue #1113)
    * Unable to give aliases to or hide network interfaces and disks (issue #1126)
    * `UnicodeDecodeError` on mountpoints with non-breaking spaces (issue #1128)

Installation:

    * Create a Snap of Glances (issue #1101)

Version 2.10
============

Enhancements and new features:

    * New plugin to scan remote Web sites (URL) (issue #981)
    * Add trends in the Curses interface (issue #1077)
    * Add new repeat function to the action (issue #952)
    * Use -> and <- arrows keys to switch between processing sort (issue #1075)
    * Refactor __init__ and main scripts (issue #1050)
    * [WebUI] Improve WebUI for Windows 10 (issue #1052)

Bugs corrected:

    * StatsD export prefix option is ignored (issue #1074)
    * Some FS and LAN metrics fail to export correctly to StatsD (issue #1068)
    * Problem with non breaking space in file system name (issue #1065)
    * TypeError: string indices must be integers (Network plugin) (issue #1054)
    * No Offline status for timeouted ports? (issue #1084)
    * When exporting, uptime values loop after 1 day (issue #1092)

Installation:

  * Create a package.sh script to generate .DEB, .RPM and others... (issue #722)
  ==> https://github.com/nicolargo/glancesautopkg
  * OSX: can't python setup.py install due to python 3.5 constraint (issue #1064)

Version 2.9.1
=============

Bugs corrected:

    * Glances PerCPU issues with Curses UI on Android (issue #1071)
    * Remove extra } in format string (issue #1073)

Version 2.9.0
=============

Enhancements and new features:

    * Add a Prometheus export module (issue #930)
    * Add a Kafka export module (issue #858)
    * Port in the -c URI (-c hostname:port) (issue #996)

Bugs corrected:

    * On Windows --export-statsd terminates immediately and does not export (issue #1067)
    * Glances v2.8.7 issues with Curses UI on Android (issue #1053)
    * Fails to start, OSError in sensors_temperatures (issue #1057)
    * Crashs after long time running the glances --browser (issue #1059)
    * Sensor values don't refresh since psutil backend (issue #1061)
    * glances-version.db Permission denied (issue #1066)

Version 2.8.8
=============

Bugs corrected:

    * Drop requests to check for outdated Glances version
    * Glances cannot load "Powersupply" (issue #1051)

Version 2.8.7
=============

Bugs corrected:

    * Windows OS - Global name standalone not defined again (issue #1030)

Version 2.8.6
=============

Bugs corrected:

    * Windows OS - Global name standalone not defined (issue #1030)

Version 2.8.5
=============

Bugs corrected:

    * Cloud plugin error: Name 'requests' is not defined (issue #1047)

Version 2.8.4
=============

Bugs corrected:

    * Correct issue on Travis CI test

Version 2.8.3
=============

Enhancements and new features:

    * Use new sensors-related APIs of psutil 5.1.0 (issue #1018)
    * Add a "Cloud" plugin to grab stats inside the AWS EC2 API (issue #1029)

Bugs corrected:

    * Unable to launch Glances on Windows (issue #1021)
    * Glances --export-influxdb starts Webserver (issue #1038)
    * Cut mount point name if it is too long (issue #1045)
    * TypeError: string indices must be integers in per cpu (issue #1027)
    * Glances crash on RPi 1 running ArchLinuxARM (issue #1046)

Version 2.8.2
=============

Bugs corrected:

    * InfluxDB export in 2.8.1 is broken (issue #1026)

Version 2.8.1
=============

Enhancements and new features:

    * Enable docker plugin on Windows (issue #1009) - Thanks to @fraoustin

Bugs corrected:

    * Glances export issue with CPU and SENSORS (issue #1024)
    * Can't export data to a CSV file in Client/Server mode (issue #1023)
    * Autodiscover error while binding on IPv6 addresses (issue #1002)
    * GPU plugin is display when hitting '4' or '5' shortkeys (issue #1012)
    * Interrupts and usb_fiq (issue #1007)
    * Docker image does not work in web server mode! (issue #1017)
    * IRQ plugin is not display anymore (issue #1013)
    * Autodiscover error while binding on IPv6 addresses (issue #1002)

Version 2.8
===========

Changes:

    * The curses interface on Windows is no more. The web-based interface is now
      the default. (issue #946)
    * The name of the log file now contains the name of the current user logged in,
      i.e., 'glances-USERNAME.log'.
    * IRQ plugin off by default. '--disable-irq' option replaced by '--enable-irq'.

Enhancements and new features:

    * GPU monitoring (limited to NVidia) (issue #170)
    * WebUI CPU consumption optimization (issue #836)
    * Not compatible with the new Docker API 2.0 (Docker 1.13) (issue #1000)
    * Add ZeroMQ exporter (issue #939)
    * Add CouchDB exporter (issue #928)
    * Add hotspot Wifi informations (issue #937)
    * Add default interface speed and automatic rate thresolds (issue #718)
    * Highlight max stats in the processes list (issue #878)
    * Docker alerts and actions (issue #875)
    * Glances API returns the processes PPID (issue #926)
    * Configure server cached time from the command line --cached-time (issue #901)
    * Make the log logger configurable (issue #900)
    * System uptime in export (issue #890)
    * Refactor the --disable-* options (issue #948)
    * PID column too small if kernel.pid_max is > 99999 (issue #959)

Bugs corrected:

    * Glances RAID plugin Traceback (issue #927)
    * Default AMP crashes when 'command' given (issue #933)
    * Default AMP ignores `enable` setting (issue #932)
    * /proc/interrupts not found in an OpenVZ container (issue #947)

Version 2.7.1
=============

Bugs corrected:

    * AMP plugin crashs on start with Python 3 (issue #917)
    * Ports plugin crashs on start with Python 3 (issue #918)

Version 2.7
===========

Backward-incompatible changes:

    * Drop support for Python 2.6 (issue #300)

Deprecated:

    * Monitoring process list module is replaced by AMP (see issue #780)
    * Use --export-graph instead of --enable-history (issue #696)
    * Use --path-graph instead of --path-history (issue #696)

Enhancements and new features:

    * Add Application Monitoring Process plugin (issue #780)
    * Add a new "Ports scanner" plugin (issue #734)
    * Add a new IRQ monitoring plugin (issue #911)
    * Improve IP plugin to display public IP address (issue #646)
    * CPU additionnal stats monitoring: Context switch, Interrupts... (issue #810)
    * Filter processes by others stats (username) (issue #748)
    * [Folders] Differentiate permission issue and non-existence of a directory (issue #828)
    * [Web UI] Add cpu name in quicklook plugin (issue #825)
    * Allow theme to be set in configuration file (issue #862)
    * Display a warning message when Glances is outdated (issue #865)
    * Refactor stats history and export to graph. History available through API (issue #696)
    * Add Cassandra/Scylla export plugin (issue #857)
    * Huge pull request by Nicolas Hart to optimize the WebUI (issue #906)
    * Improve documentation: http://glances.readthedocs.io (issue #872)

Bugs corrected:

    * Crash on launch when viewing temperature of laptop HDD in sleep mode (issue #824)
    * [Web UI] Fix folders plugin never displayed (issue #829)
    * Correct issue IP plugin: VPN with no internet access (issue #842)
    * Idle process is back on FreeBSD and Windows (issue #844)
    * On Windows, Glances try to display unexisting Load stats (issue #871)
    * Check CPU info (issue #881)
    * Unicode error on processlist on Windows server 2008 (french) (issue #886)
    * PermissionError/OSError when starting glances (issue #885)
    * Zeroconf problem with zeroconf_type = "_%s._tcp." % __appname__ (issue #888)
    * Zeroconf problem with zeroconf service name (issue #889)
    * [WebUI] Glances will not get past loading screen - Windows OS (issue #815)
    * Improper bytes/unicode in glances_hddtemp.py (issue #887)
    * Top 3 processes are back in the alert summary

Code quality follow up: from 5.93 to 6.24 (source: https://scrutinizer-ci.com/g/nicolargo/glances)

Version 2.6.2
=============

Bugs corrected:

    * Crash with Docker 1.11 (issue #848)

Version 2.6.1
=============

Enhancements and new features:

    * Add a connector to Riemann (issue #822 by Greogo Nagy)

Bugs corrected:

    * Browsing for servers which are in the [serverlist] is broken (issue #819)
    * [WebUI] Glances will not get past loading screen (issue #815) opened 9 days ago
    * Python error after upgrading from 2.5.1 to 2.6 bug (issue #813)

Version 2.6
===========

Deprecations:

    * Add deprecation warning for Python 2.6.
      Python 2.6 support will be dropped in future releases.
      Please switch to at least Python 2.7 or 3.3+ as soon as possible.
      See http://www.snarky.ca/stop-using-python-2-6 for more information.

Enhancements and new features:

    * Add a connector to ElasticSearch (welcome to Kibana dashboard) (issue #311)
    * New folders' monitoring plugins (issue #721)
    * Use wildcard (regexp) to the hide configuration option for network, diskio and fs sections (issue #799 )
    * Command line arguments are now take into account in the WebUI (#789 by  @notFloran)
    * Change username for server and web server authentication (issue #693)
    * Add an option to disable top menu (issue #766)
    * Add IOps in the DiskIO plugin (issue #763)
    * Add hide configuration key for FS Plugin (issue #736)
    * Add process summary min/max stats (issue #703)
    * Add timestamp to the CSV export module (issue #708)
    * Add a shortcut 'E' to delete process filter (issue #699)
    * By default, hide disk I/O ram1-** (issue #714)
    * When Glances is starting the notifications should be delayed (issue #732)
    * Add option (--disable-bg) to disable ANSI background colours (issue #738 by okdana)
    * [WebUI] add "pointer" cursor for sortable columns (issue #704 by @notFloran)
    * [WebUI] Make web page title configurable (issue #724)
    * Do not show interface in down state (issue #765)
    * InfluxDB > 0.9.3 needs float and not int for numerical value (issue#749 and issue#750 by nicolargo)

Bugs corrected:

    * Can't read sensors on a Thinkpad (issue #711)
    * InfluxDB/OpenTSDB: tag parsing broken (issue #713)
    * Grafana Dashboard outdated for InfluxDB 0.9.x (issue #648)
    * '--tree' breaks process filter on Debian 8 (issue #768)
    * Fix highlighting of process when it contains whitespaces (issue #546 by Alessio Sergi)
    * Fix RAID support in Python 3 (issue #793 by Alessio Sergi)
    * Use dict view objects to avoid issue (issue #758 by Alessio Sergi)
    * System exit if Cpu not supported by the Cpuinfo lib (issue #754 by nicolargo)
    * KeyError: 'cpucore' when exporting data to InfluxDB (issue #729 by nicolargo)

Others:
    * A new Glances docker container to monitor your Docker infrastructure is available here (issue #728): https://hub.docker.com/r/nicolargo/glances/
    * Documentation is now generated automatically thanks to Sphinx and the Alessio Sergi patch (https://glances.readthedocs.io/en/latest/)

Contributors summary:
    * Nicolas Hennion: 112 commits
    * Alessio Sergi: 55 commits
    * Floran Brutel: 19 commits
    * Nicolas Hart: 8 commits
    * @desbma: 4 commits
    * @dana: 2 commits
    * Damien Martin, Raju Kadam, @georgewhewell: 1 commit

Version 2.5.1
=============

Bugs corrected:

    * Unable to unlock password protected servers in browser mode bug (issue #694)
    * Correct issue when Glances is started in console on Windows OS
    * [WebUI] when alert is ongoing hide level enhancement (issue #692)

Version 2.5
===========

Enhancements and new features:

    * Allow export of Docker and sensors plugins stats to InfluxDB, StatsD... (issue #600)
    * Docker plugin shows IO and network bitrate (issue #520)
    * Server password configuration for the browser mode (issue #500)
    * Add support for OpenTSDB export (issue #638)
    * Add additional stats (iowait, steal) to the perCPU plugin (issue #672)
    * Support Fahrenheit unit in the sensor plugin using the --fahrenheit command line option (issue #620)
    * When a process filter is set, display sum of CPU, MEM... (issue #681)
    * Improve the QuickLookplugin by adding hardware CPU info (issue #673)
    * WebUI display a message if server is not available (issue #564)
    * Display an error if export is not used in the standalone/client mode (issue #614)
    * New --disable-quicklook, --disable-cpu, --disable-mem, --disable-swap, --disable-load tags (issue #631)
    * Complete refactoring of the WebUI thanks to the (awesome) Floran pull (issue #656)
    * Network cumulative /combination feature available in the WebUI (issue #552)
    * IRIX mode off implementation (issue#628)
    * Short process name displays arguments (issue #609)
    * Server password configuration for the browser mode (issue #500)
    * Display an error if export is not used in the standalone/client mode (issue #614)

Bugs corrected:

    * The WebUI displays bad sensors stats (issue #632)
    * Filter processes crashs with a bad regular expression pattern (issue #665)
    * Error with IP plugin (issue #651)
    * Crach with Docker plugin (issue #649)
    * Docker plugin crashs with webserver mode (issue #654)
    * Infrequently crashing due to assert (issue #623)
    * Value for free disk space is counterintuative on ext file systems (issue #644)
    * Try/catch for unexpected psutil.NoSuchProcess: process no longer exists (issue #432)
    * Fatal error using Python 3.4 and Docker plugin bug (issue #602)
    * Add missing new line before g man option (issue #595)
    * Remove unnecessary type="text/css" for link (HTML5) (issue #595)
    * Correct server mode issue when no network interface is available (issue #528)
    * Avoid crach on olds kernels (issue #554)
    * Avoid crashing if LC_ALL is not defined by user (issue #517)
    * Add a disable HDD temperature option on the command line (issue #515)


Version 2.4.2
=============

Bugs corrected:

    * Process no longer exists (again) (issue #613)
    * Crash when "top extended stats" is enabled on OS X (issue #612)
    * Graphical percentage bar displays "?" (issue #608)
    * Quick look doesn't work (issue #605)
    * [Web UI] Display empty Battery sensors enhancement (issue #601)
    * [Web UI] Per CPU plugin has to be improved (issue #566)

Version 2.4.1
=============

Bugs corrected:

    * Fatal error using Python 3.4 and Docker plugin bug (issue #602)

Version 2.4
===========

Changes:

    * Glances doesn't provide a system-wide configuration file by default anymore.
      Just copy it in any of the supported locations. See glances-doc.html for
      more information. (issue #541)
    * The default key bindings have been changed to:
      - 'u': sort processes by USER
      - 'U': show cumulative network I/O
    * No more translations

Enhancements and new features:

    * The Web user interface is now based on AngularJS (issue #473, #508, #468)
    * Implement a 'quick look' plugin (issue #505)
    * Add sort processes by USER (issue #531)
    * Add a new IP information plugin (issue #509)
    * Add RabbitMQ export module (issue #540 Thk to @Katyucha)
    * Add a quiet mode (-q), can be useful using with export module
    * Grab FAN speed in the Glances sensors plugin (issue #501)
    * Allow logical mounts points in the FS plugin (issue #448)
    * Add a --disable-hddtemp to disable HDD temperature module at startup (issue #515)
    * Increase alert minimal delay to 6 seconds (issue #522)
    * If the Curses application raises an exception, restore the terminal correctly (issue #537)

Bugs corrected:

    * Monitor list, all processes are take into account (issue #507)
    * Duplicated --enable-history in the doc (issue #511)
    * Sensors title is displayed if no sensors are detected (issue #510)
    * Server mode issue when no network interface is available (issue #528)
    * DEBUG mode activated by default with Python 2.6 (issue #512)
    * Glances display of time trims the hours showing only minutes and seconds (issue #543)
    * Process list header not decorating when sorting by command (issue #551)

Version 2.3
===========

Enhancements and new features:

    * Add the Docker plugin (issue #440) with per container CPU and memory monitoring (issue #490)
    * Add the RAID plugin (issue #447)
    * Add actions on alerts (issue #132). It is now possible to run action (command line) by triggers. Action could contain {{tag}} (Mustache) with stat value.
    * Add InfluxDB export module (--export-influxdb) (issue #455)
    * Add StatsD export module (--export-statsd) (issue #465)
    * Refactor export module (CSV export option is now --export-csv). It is now possible to export stats from the Glances client mode (issue #463)
    * The Web inteface is now based on Bootstrap / RWD grid (issue #417, #366 and #461) Thanks to Nicolas Hart @nclsHart
    * It is now possible, through the configuration file, to define if an alarm should be logged or not (using the _log option) (issue #437)
    * You can now set alarm for Disk IO
    * API: add getAllLimits and getAllViews methods (issue #481) and allow CORS request (issue #479)
    * SNMP client support NetApp appliance (issue #394)

Bugs corrected:

    *  R/W error with the glances.log file (issue #474)

Other enhancement:

    * Alert < 3 seconds are no longer displayed

Version 2.2.1
=============

    * Fix incorrect kernel thread detection with --hide-kernel-threads (issue #457)
    * Handle IOError exception if no /etc/os-release to use Glances on Synology DSM (issue #458)
    * Check issue error in client/server mode (issue #459)

Version 2.2
===========

Enhancements and new features:

    * Add centralized curse interface with a Glances servers list to monitor (issue #418)
    * Add processes tree view (--tree) (issue #444)
    * Improve graph history feature (issue #69)
    * Extended stats is disable by default (use --enable-process-extended to enable it - issue #430)
    * Add a short key ('F') and a command line option (--fs-free-space) to display FS free space instead of used space (issue #411)
    * Add a short key ('2') and a command line option (--disable-left-sidebar) to disable/enable the side bar (issue #429)
    * Add CPU times sort short key ('t') in the curse interface (issue #449)
    * Refactor operating system detection for GNU/Linux operating system
    * Code optimization

Bugs corrected:

    * Correct a bug with Glances pip install --user (issue #383)
    * Correct issue on battery stat update (issue #433)
    * Correct issue on process no longer exist (issues #414 and #432)

Version 2.1.2
=============

    Maintenance version (only needed for Mac OS X).

Bugs corrected:

    * Mac OS X: Error if Glances is not ran with sudo (issue #426)

Version 2.1.1
=============

Enhancement:

    * Automaticaly compute top processes number for the current screen (issue #408)
    * CPU and Memory footprint optimization (issue #401)

Bugs corrected:

    * Mac OS X 10.9: Exception at start (issue #423)
    * Process no longer exists (issue #421)
    * Error with Glances Client with Python 3.4.1 (issue #419)
    * TypeError: memory_maps() takes exactly 2 arguments (issue #413)
    * No filesystem informations since Glances 2.0 bug enhancement (issue #381)

Version 2.1
===========

    * Add user process filter feature
      User can define a process filter pattern (as a regular expression).
      The pattern could be defined from the command line (-f <pattern>)
      or by pressing the ENTER key in the curse interface.
      For the moment, process filter feature is only available in standalone mode.
    * Add extended processes informations for top process
      Top process stats availables: CPU affinity, extended memory information (shared, text, lib, datat, dirty, swap), open threads/files and TCP/UDP network sessions, IO nice level
      For the moment, extended processes stats are only available in standalone mode.
    * Add --process-short-name tag and '/' key to switch between short/command line
    * Create a max_processes key in the configuration file
      The goal is to reduce the number of displayed processes in the curses UI and
      so limit the CPU footprint of the Glances standalone mode.
      The API always return all the processes, the key is only active in the curses UI.
      If the key is not define, all the processes will be displayed.
      The default value is 20 (processes displayed).
      For the moment, this feature is only available in standalone mode.
    * Alias for network interfaces, disks and sensors
      Users can configure alias from the Glances configuration file.
    * Add Glances log message (in the /tmp/glances.log file)
      The default log level is INFO, you can switch to the DEBUG mode using the -d option on the command line.
    * Add RESTful API to the Web server mode
      RESTful API doc: https://github.com/nicolargo/glances/wiki/The-Glances-RESTFULL-JSON-API
    * Improve SNMP fallback mode for Cisco IOS, VMware ESXi
    * Add --theme-white feature to optimize display for white background
    * Experimental history feature (--enable-history option on the command line)
      This feature allows users to generate graphs within the curse interface.
      Graphs are available for CPU, LOAD and MEM.
      To generate graph, click on the 'g' key.
      To reset the history, press the 'r' key.
      Note: This feature uses the matplotlib library.
    * CI: Improve Travis coverage

Bugs corrected:

    * Quitting glances leaves a column layout to the current terminal (issue #392)
    * Glances crashes with malformed UTF-8 sequences in process command lines (issue #391)
    * SNMP fallback mode is not Python 3 compliant (issue #386)
    * Trouble using batinfo, hddtemp, pysensors w/ Python (issue #324)


Version 2.0.1
=============

Maintenance version.

Bugs corrected:

    * Error when displaying numeric process user names (#380)
    * Display users without username correctly (#379)
    * Bug when parsing configuration file (#378)
    * The sda2 partition is not seen by glances (#376)
    * Client crash if server is ended during XML request (#375)
    * Error with the Sensors module on Debian/Ubuntu (#373)
    * Windows don't view all processes (#319)

Version 2.0
===========

    Glances v2.0 is not a simple upgrade of the version 1.x but a complete code refactoring.
    Based on a plugins system, it aims at providing an easy way to add new features.
    - Core defines the basics and commons functions.
    - all stats are grabbed through plugins (see the glances/plugins source folder).
    - also outputs methods (Curse, Web mode, CSV) are managed as plugins.

    The Curse interface is almost the same than the version 1.7. Some improvements have been made:
    - space optimisation for the CPU, LOAD and MEM stats (justified alignment)
    - CPU:
        . CPU stats are displayed as soon as Glances is started
        . steal CPU alerts are no more logged
    - LOAD:
        . 5 min LOAD alerts are no more logged
    - File System:
        . Display the device name (if space is available)
    - Sensors:
        . Sensors and HDD temperature are displayed in the same block
    - Process list:
        . Refactor columns: CPU%, MEM%, VIRT, RES, PID, USER, NICE, STATUS, TIME, IO, Command/name
        . The running processes status is highlighted
        . The process name is highlighted in the command line

    Glances 2.0 brings a brand new Web Interface. You can run Glances in Web server mode and
    consult the stats directly from a standard Web Browser.

    The client mode can now fallback to a simple SNMP mode if Glances server is not found on the remote machine.

    Complete release notes:
    * Cut ifName and DiskName if they are too long in the curses interface (by Nicolargo)
    * Windows CLI is OK but early experimental (by Nicolargo)
    * Add bitrate limits to the networks interfaces (by Nicolargo)
    * Batteries % stats are now in the sensors list (by Nicolargo)
    * Refactor the client/server password security: using SHA256 (by Nicolargo,
      based on Alessio Sergi's example script)
    * Refactor the CSV output (by Nicolargo)
    * Glances client fallback to SNMP server if Glances one not found (by Nicolargo)
    * Process list: Highlight running/basename processes (by Alessio Sergi)
    * New Web server mode thk to the Bottle library (by Nicolargo)
    * Responsive design for Bottle interface (by Nicolargo)
    * Remove HTML output (by Nicolargo)
    * Enable/disable for optional plugins through the command line (by Nicolargo)
    * Refactor the API (by Nicolargo)
    * Load-5 alert are no longer logged (by Nicolargo)
    * Rename In/Out by Read/Write for DiskIO according to #339 (by Nicolargo)
    * Migrate from pysensors to py3sensors (by Alessio Sergi)
    * Migration to psutil 2.x (by Nicolargo)
    * New plugins system (by Nicolargo)
    * Python 2.x and 3.x compatibility (by Alessio Sergi)
    * Code quality improvements (by Alessio Sergi)
    * Refactor unitaries tests (by Nicolargo)
    * Development now follow the git flow workflow (by Nicolargo)


==============================================================================
Glances Version 1
==============================================================================

Version 1.7.7
=============

    * Fix CVS export [issue #348]
    * Adapt to psutil 2.1.1
    * Compatibility with Python 3.4
    * Improve German update

Version 1.7.6
=============

    * Adapt to psutil 2.0.0 API
    * Fixed psutil 0.5.x support on Windows
    * Fix help screen in 80x24 terminal size
    * Implement toggle of process list display ('z' key)

Version 1.7.5
=============

    * Force the PyPI installer to use the psutil branch 1.x (#333)

Version 1.7.4
=============

    * Add threads number in the task summary line (#308)
    * Add system uptime (#276)
    * Add CPU steal % to cpu extended stats (#309)
    * You can hide disk from the IOdisk view using the conf file (#304)
    * You can hide network interface from the Network view using the conf file
    * Optimisation of CPU consumption (around ~10%)
    * Correct issue #314: Client/server mode always asks for password
    * Correct issue #315: Defining password in client/server mode doesn't work as intended
    * Correct issue #316: Crash in client server mode
    * Correct issue #318: Argument parser, try-except blocks never get triggered

Version 1.7.3
=============

    * Add --password argument to enter the client/server password from the prompt
    * Fix an issue with the configuration file path (#296)
    * Fix an issue with the HTML template (#301)

Version 1.7.2
=============

    * Console interface is now Microsoft Windows compatible (thk to @fraoustin)
    * Update documentation and Wiki regarding the API
    * Added package name for python sources/headers in openSUSE/SLES/SLED
    * Add FreeBSD packager
    * Bugs corrected

Version 1.7.1
=============

    * Fix IoWait error on FreeBSD / Mac OS
    * HDDTemp module is now Python v3 compatible
    * Don't warn a process is not running if countmin=0
    * Add PyPI badge on the README.rst
    * Update documentation
    * Add document structure for http://readthedocs.org

Version 1.7
===========

    * Add monitored processes list
    * Add hard disk temperature monitoring (thanks to the HDDtemp daemon)
    * Add batteries capacities information (thanks to the Batinfo lib)
    * Add command line argument -r toggles processes (reduce CPU usage)
    * Add command line argument -1 to run Glances in per CPU mode
    * Platform/architecture is more specific now
    * XML-RPC server: Add IPv6 support for the client/server mode
    * Add support for local conf file
    * Add a uninstall script
    * Add getNetTimeSinceLastUpdate() getDiskTimeSinceLastUpdate() and getProcessDiskTimeSinceLastUpdate() in the API
    * Add more translation: Italien, Chinese
    * and last but not least... up to 100 hundred bugs corrected / software and
    * docs improvements

Version 1.6.1
=============

    * Add per-user settings (configuration file) support
    * Add -z/--nobold option for better appearance under Solarized terminal
    * Key 'u' shows cumulative net traffic
    * Work in improving autoUnit
    * Take into account the number of core in the CPU process limit
    * API improvment add time_since_update for disk, process_disk and network
    * Improve help display
    * Add more dummy FS to the ignore list
    * Code refactory: psutil < 0.4.1 is deprecated (Thk to Alessio)
    * Correct a bug on the CPU process limit
    * Fix crash bug when specifying custom server port
    * Add Debian style init script for the Glances server

Version 1.6
===========

    * Configuration file: user can defines limits
    * In client/server mode, limits are set by the server side
    * Display limits in the help screen
    * Add per process IO (read and write) rate in B per second
      IO rate only available on Linux from a root account
    * If CPU iowait alert then sort by processes by IO rate
    * Per CPU display IOwait (if data is available)
    * Add password for the client/server mode (-P password)
    * Process column style auto (underline) or manual (bold)
    * Display a sort indicator (is space is available)
    * Change the table key in the help screen

Version 1.5.2
=============

    * Add sensors module (enable it with -e option)
    * Improve CPU stats (IO wait, Nice, IRQ)
    * More stats in lower space (yes it's possible)
    * Refactor processes list and count (lower CPU/MEM footprint)
    * Add functions to the RCP method
    * Completed unit test
    * and fixes...

Version 1.5.1
=============

    * Patch for psutil 0.4 compatibility
    * Test psutil version before running Glances

Version 1.5
===========

    * Add a client/server mode (XMLRPC) for remote monitoring
    * Correct a bug on process IO with non root users
    * Add 'w' shortkey to delete finished warning message
    * Add 'x' shortkey to delete finished warning/critical message
    * Bugs correction
    * Code optimization

Version 1.4.2.2
===============

    * Add switch between bit/sec and byte/sec for network IO
    * Add Changelog (generated with gitchangelog)

Version 1.4.2.1
===============

    * Minor patch to solve memomy issue (#94) on Mac OS X

Version 1.4.2
=============

    * Use the new virtual_memory() and virtual_swap() fct (psutil)
    * Display "Top process" in logs
    * Minor patch on man page for Debian packaging
    * Code optimization (less try and except)

Version 1.4.1.1
===============

    * Minor patch to disable Process IO for OS X (not available in psutil)

Version 1.4.1
=============

    * Per core CPU stats (if space is available)
    * Add Process IO Read/Write information (if space is available)
    * Uniformize units

Version 1.4
===========

    * Goodby StatGrab... Welcome to the psutil library !
    * No more autotools, use setup.py to install (or package)
    * Only major stats (CPU, Load and memory) use background colors
    * Improve operating system name detection
    * New system info: one-line layout and add Arch Linux support
    * No decimal places for values < GB
    * New memory and swap layout
    * Add percentage of usage for both memory and swap
    * Add MEM% usage, NICE, STATUS, UID, PID and running TIME per process
    * Add sort by MEM% ('m' key)
    * Add sort by Process name ('p' key)
    * Multiple minor fixes, changes and improvements
    * Disable Disk IO module from the command line (-d)
    * Disable Mount module from the command line (-m)
    * Disable Net rate module from the command line (-n)
    * Improved FreeBSD support
    * Cleaning code and style
    * Code is now checked with pep8
    * CSV and HTML output (experimental functions, no yet documentation)

Version 1.3.7
=============

    * Display (if terminal space is available) an alerts history (logs)
    * Add a limits classe to manage stats limits
    * Manage black and white console (issue #31)

Version 1.3.6
=============

    * Add control before libs import
    * Change static Python path (issue #20)
    * Correct a bug with a network interface disaippear (issue #27)
    * Add French and Spanish translation (thx to Jean Bob)

Version 1.3.5
=============

    * Add an help panel when Glances is running (key: 'h')
    * Add keys descriptions in the syntax (--help | -h)

Version 1.3.4
=============

    * New key: 'n' to enable/disable network stats
    * New key: 'd' to enable/disable disk IO stats
    * New key: 'f' to enable/disable FS stats
    * Reorganised the screen when stat are not available|disable
    * Force Glances to use the enmbeded fs stats (issue #16)

Version 1.3.3
=============

    * Automatically swith between process short and long name
    * Center the host / system information
    * Always put the hour/date in the bottom/right
    * Correct a bug if there is a lot of Disk/IO
    * Add control about available libstatgrab functions

Version 1.3.2
=============

    * Add alert for network bit rate°
    * Change the caption
    * Optimised net, disk IO and fs display (share the space)
      Disable on Ubuntu because the libstatgrab return a zero value
      for the network interface speed.

Version 1.3.1
=============

    * Add alert on load (depend on number of CPU core)
    * Fix bug when the FS list is very long

Version 1.3
===========

    * Add file system stats (total and used space)
    * Adapt unit dynamically (K, M, G)
    * Add man page (Thanks to Edouard Bourguignon)

Version 1.2
===========

    * Resize the terminal and the windows are adapted dynamically
    * Refresh screen instantanetly when a key is pressed

Version 1.1.3
=============

    * Add disk IO monitoring
    * Add caption
    * Correct a bug when computing the bitrate with the option -t
    * Catch CTRL-C before init the screen (Bug #2)
    * Check if mem.total = 0 before division (Bug #1)
