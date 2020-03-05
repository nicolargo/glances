You are in the main Glances source folder. This page is **ONLY** for developers.

If you are looking for the user manual, please follow this link:
https://glances.readthedocs.io/en/stable/

===

__init__.py                 Global module init
__main__.py                 Entry point for Glances module
config.py                   Manage the configuration file
compat.py                   Python2/3 compatibility shims module
globals.py                  Share variables upon modules
main.py                     Main script to rule them up...
client.py                   Glances client
server.py                   Glances server
webserver.py                Glances web server (Bottle-based)
autodiscover.py             Glances autodiscover module (via zeroconf)
standalone.py               Glances standalone (curses interface)
password.py                 Manage password for Glances client/server
stats.py                    The stats manager
timer.py                    The timer class
actions.py                  Manage trigger actions (via mustache)
snmp.py                     Glances SNMP client (via pysnmp)
...
plugins
    => Glances data providers
    glances_plugins.py      "Father class" for others plugins
    glances_cpu.py          Manage CPU stats
    glances_load.py         Manage load stats
    glances_mem.py          Manage RAM stats
    glances_memswap.py      Manage swap stats
    glances_network.py      Manage network stats
    glances_fs.py           Manage file system stats
    glances_diskio.py       Manage disk I/O stats
    glances_docker.py       Glances Docker plugin (via docker-py)
    glances_raid.py         Glances RAID plugin (via pymdstat)
    ...
outputs
    => Glances UI
    glances_curses.py       The curses interface
    glances_bottle.py       The web interface
    ...
exports
    => Glances export interfaces
    glances_export.py       "Father class" for exports
    glances_csv.py          The CSV export module
    glances_influxdb.py     The InfluxDB export module
    glances_mqtt.py         The MQTT export module
    glances_opentsdb.py     The OpenTSDB export module
    glances_rabbitmq.py     The RabbitMQ export module
    glances_statsd.py       The StatsD export module
    ...
amps
    => Glances Application Monitoring Processes (AMP)
    glances_amp.py          "Father class" for AMPs
    glances_default.py      Default AMP
    glances_nginx.py        Nginx AMP
    ...
