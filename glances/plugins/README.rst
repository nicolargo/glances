===============
Glances plugins
===============

This is the Glances plugins folder.

A Glances plugin is a Python module hosted in a folder.

It should implement a Class named PluginModel (inherited from GlancesPluginModel).

This class should be based on the MVC model.
- model: where the stats are updated (update method)
- view: where the stats are prepare to be displayed (update_views)
- controller: where the stats are displayed (msg_curse method)

A plugin should define the following global variables:

- fields_description: a dict twith the field description/option
- items_history_list (optional): define items history

Have a look of all Glances plugin's methods in the plugin folder (where the GlancesPluginModel is defined).
