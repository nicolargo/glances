===============
Glances plugins
===============

This is the Glances plugins folder.

A Glances plugin is a Python module hosted in a folder.

The name of the foo Glances plugin folder is foo (glances_foo).

The plugin is a Python class named Plugin inherits the GlancesPlugin object:

.. code-block:: python

    class Plugin(GlancesPlugin):
        """Glances foo plugin."""

        def __init__(self, args=None, config=None):
            super(Plugin, self).__init__(args=args,
                                         config=config,
                                         items_history_list=items_history_list,
                                         fields_description=fields_description)
            pass

A plugin should define the following global variables:

- fields_description: a dict twith the field description/option
- items_history_list: define items history

A plugin should implement the following methods:

- update(): update the self.stats variable (most of the time a dict or a list of dict)
- msg_curse(): return a list of messages to display in UI

Have a look of all Glances plugin's methods in the plugin.py file.
