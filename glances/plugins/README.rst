===============
Glances plugins
===============

This is the Glances plugins folder.

A Glances plugin is a Python module hosted in a folder.

It should be based on the MVC model.
- model: data model (where the stats will be updated)
- view: input for UI (where the stats are displayed)
- controler: output from UI (where the stats are controled)

////
TODO
////

A plugin should define the following global variables:

- fields_description: a dict twith the field description/option
- items_history_list: define items history

A plugin should implement the following methods:

- update(): update the self.stats variable (most of the time a dict or a list of dict)
- msg_curse(): return a list of messages to display in UI

Have a look of all Glances plugin's methods in the plugin.py file.
