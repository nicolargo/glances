You are in the main Glances's source folder.
This page is for developpers and contributors.

If you are lookink for user manual, please follow this link: https://github.com/nicolargo/glances/blob/master/docs/glances-doc.rst

===

__init__.py             Global module init
__main__.py             Entry point for module
core/
    glances_core.py     Main script to rule them up...
    glances_globals.py  Share variables uppon modules
    glances_config.py   Manage configuration file
    glances_timer.py    Manage timer
    glances_stats.py    Inteface to grab stats
    glances_client.py   Glances client
    glances_server.py   Glances_server    
plugins/
    glances_plugins.py  "Father class" for others plugins
    glances_cpu.py      Manage CPU stats
    glances_load.py     Manage LOAD stats
    glances_mem.py      Manage MEM (both RAM and SWAP) stats
    ...
outputs/
    glances_curse.py    The Curse (console) interface
    glances_csv.py      The CSV interface
    glances_html.py     The HTML interface
    ...