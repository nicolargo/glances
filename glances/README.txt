You are in the main Glances source folder. This page is **ONLY** for developers.

If you are looking for the user manual, please follow this link:
https://github.com/nicolargo/glances/blob/master/docs/glances-doc.rst

===

__init__.py                 Global module init
__main__.py                 Entry point for Glances module
core/
    => Glances core folder
    glances_config.py       Manage configuration file
    glances_globals.py      Share variables upon modules
    glances_limits.py       Manage limits
    glances_logs.py         Manage logs
    glances_main.py         Main script to rule them up...
    glances_client.py       Glances client
    glances_server.py       Glances server
    glances_standalone.py   Glances standalone (with curse interface)
    glances_stats.py        The stats manager
    glances_timer.py        Manage timer
    ...
plugins/
    => Glances data providers
    glances_plugins.py      "Father class" for others plugins
    glances_cpu.py          Manage CPU stats
    glances_load.py         Manage LOAD stats
    glances_mem.py          Manage MEM (both RAM and SWAP) stats
    ...
outputs/
    => Glances UI
    glances_curse.py        The Curse interface
    glances_html.py         The HTML interface
    ...
exports/
    => Glances export interfaces
    glances_csv.py          The CSV export module
    ...
