You are in the main Glances source folder. This page is **ONLY** for developers.

If you are looking for the user manual, please follow this link:
https://glances.readthedocs.io/en/stable/

===

__init__.py                 Global module init
__main__.py                 Entry point for Glances module
config.py                   Manage the configuration file
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
    => Glances plugins
    ...
outputs
    => Glances UI
    glances_curses.py       The curses interface
    glances_bottle.py       The web interface
    ...
exports
    => Glances exports
    ...
amps
    => Glances Application Monitoring Processes (AMP)
    ...
