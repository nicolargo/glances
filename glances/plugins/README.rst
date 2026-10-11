===============
Glances plugins
===============

This is the Glances plugins folder.

A Glances plugin is a Python package hosted in a folder: the foo plugin
lives in ``foo/``.

- ``foo/model.py`` implements a class named PluginModel inherited from
  GlancesPluginBase (``plugin/base.py``). Its ``_grab_stats()`` coroutine
  collects the stats; the scheduler stores them, computes the alert levels
  and serves them to the TUI, the REST API, the WebUI and the exporters.
- ``foo/render_curses.py`` (optional) implements the ``render()`` function
  that turns the stats into TUI rows.

A plugin should define the following class variables:

- plugin_name: the plugin name (foo)
- fields_description: a dict with the field description/option
- IS_COLLECTION: True when the stats are a list of items

Have a look of all Glances plugin's methods in the plugin folder (where the
GlancesPluginBase is defined).
