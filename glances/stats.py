# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""The stats manager."""

import collections
import os
import sys
import threading
import traceback

from glances.logger import logger
from glances.globals import exports_path, plugins_path, sys_path
from glances.timer import Counter


class GlancesStats(object):

    """This class stores, updates and gives stats."""

    # Script header constant
    header = "glances_"

    def __init__(self, config=None, args=None):
        # Set the config instance
        self.config = config

        # Set the argument instance
        self.args = args

        # Load plugins and exports modules
        self.load_modules(self.args)

        # Load the limits (for plugins)
        # Not necessary anymore, configuration file is loaded on init
        # self.load_limits(self.config)

    def __getattr__(self, item):
        """Overwrite the getattr method in case of attribute is not found.

        The goal is to dynamically generate the following methods:
        - getPlugname(): return Plugname stat in JSON format
        - getViewsPlugname(): return views of the Plugname stat in JSON format
        """
        # Check if the attribute starts with 'get'
        if item.startswith('getViews'):
            # Get the plugin name
            plugname = item[len('getViews'):].lower()
            # Get the plugin instance
            plugin = self._plugins[plugname]
            if hasattr(plugin, 'get_json_views'):
                # The method get_views exist, return it
                return getattr(plugin, 'get_json_views')
            else:
                # The method get_views is not found for the plugin
                raise AttributeError(item)
        elif item.startswith('get'):
            # Get the plugin name
            plugname = item[len('get'):].lower()
            # Get the plugin instance
            plugin = self._plugins[plugname]
            if hasattr(plugin, 'get_stats'):
                # The method get_stats exist, return it
                return getattr(plugin, 'get_stats')
            else:
                # The method get_stats is not found for the plugin
                raise AttributeError(item)
        else:
            # Default behavior
            raise AttributeError(item)

    def load_modules(self, args):
        """Wrapper to load: plugins and export modules."""

        # Init the plugins dict
        # Active plugins dictionnary
        self._plugins = collections.defaultdict(dict)
        # Load the plugins
        self.load_plugins(args=args)

        # Init the export modules dict
        # Active exporters dictionnary
        self._exports = collections.defaultdict(dict)
        # All available exporters dictionnary
        self._exports_all = collections.defaultdict(dict)
        # Load the export modules
        self.load_exports(args=args)

        # Restoring system path
        sys.path = sys_path

    def _load_plugin(self, plugin_script, args=None, config=None):
        """Load the plugin (script), init it and add to the _plugin dict."""
        # The key is the plugin name
        # for example, the file glances_xxx.py
        # generate self._plugins_list["xxx"] = ...
        name = plugin_script[len(self.header):-3].lower()

        # Loaf the plugin class
        try:
            # Import the plugin
            plugin = __import__(plugin_script[:-3])
            # Init and add the plugin to the dictionary
            self._plugins[name] = plugin.Plugin(args=args, config=config)
        except Exception as e:
            # If a plugin can not be loaded, display a critical message
            # on the console but do not crash
            logger.critical("Error while initializing the {} plugin ({})".format(name, e))
            logger.error(traceback.format_exc())
            # Disable the plugin
            if args is not None:
                setattr(args,
                        'disable_' + name,
                        False)
        else:
            # Set the disable_<name> to False by default
            if args is not None:
                setattr(args,
                        'disable_' + name,
                        getattr(args, 'disable_' + name, False))

    def load_plugins(self, args=None):
        """Load all plugins in the 'plugins' folder."""
        start_duration = Counter()
        for item in os.listdir(plugins_path):
            if (item.startswith(self.header) and
                    item.endswith(".py") and
                    item != (self.header + "plugin.py")):
                # Load the plugin
                start_duration.reset()
                self._load_plugin(os.path.basename(item),
                                  args=args, config=self.config)
                logger.debug("Plugin {} started in {} seconds".format(item,
                                                                      start_duration.get()))

        # Log plugins list
        logger.debug("Active plugins list: {}".format(self.getPluginsList()))

    def load_exports(self, args=None):
        """Load all export modules in the 'exports' folder."""
        if args is None:
            return False
        header = "glances_"
        # Build the export module available list
        args_var = vars(locals()['args'])
        for item in os.listdir(exports_path):
            export_name = os.path.basename(item)[len(header):-3].lower()
            if (item.startswith(header) and
                    item.endswith(".py") and
                    item != (header + "export.py") and
                    item != (header + "history.py")):
                self._exports_all[export_name] = os.path.basename(item)[:-3]
                # Set the disable_<name> to False by default
                setattr(self.args,
                        'export_' + export_name,
                        getattr(self.args, 'export_' + export_name, False))

        # Aim is to check if the export module should be loaded
        for export_name in self._exports_all:
            if getattr(self.args, 'export_' + export_name, False):
                # Import the export module
                export_module = __import__(self._exports_all[export_name])
                # Add the export to the dictionary
                # The key is the module name
                # for example, the file glances_xxx.py
                # generate self._exports_list["xxx"] = ...
                self._exports[export_name] = export_module.Export(args=args,
                                                                  config=self.config)
                self._exports_all[export_name] = self._exports[export_name]

        # Log plugins list
        logger.debug("Active exports modules list: {}".format(self.getExportsList()))
        return True

    def getPluginsList(self, enable=True):
        """Return the plugins list.

        if enable is True, only return the active plugins (default)
        if enable is False, return all the plugins

        Return: list of plugin name
        """
        if enable:
            return [p for p in self._plugins if self._plugins[p].is_enable()]
        else:
            return [p for p in self._plugins]

    def getExportsList(self, enable=True):
        """Return the exports list.

        if enable is True, only return the active exporters (default)
        if enable is False, return all the exporters

        Return: list of export module name
        """
        if enable:
            return [e for e in self._exports]
        else:
            return [e for e in self._exports_all]

    def load_limits(self, config=None):
        """Load the stats limits (except the one in the exclude list)."""
        # For each plugins, call the load_limits method
        for p in self._plugins:
            self._plugins[p].load_limits(config)

    def update(self):
        """Wrapper method to update the stats."""
        # For standalone and server modes
        # For each plugins, call the update method
        for p in self._plugins:
            if self._plugins[p].is_disable():
                # If current plugin is disable
                # then continue to next plugin
                continue
            start_duration = Counter()
            # Update the stats...
            self._plugins[p].update()
            # ... the history
            self._plugins[p].update_stats_history()
            # ... and the views
            self._plugins[p].update_views()
            # logger.debug("Plugin {} update duration: {} seconds".format(p,
            #                                                             start_duration.get()))

    def export(self, input_stats=None):
        """Export all the stats.

        Each export module is ran in a dedicated thread.
        """
        # threads = []
        input_stats = input_stats or {}

        for e in self._exports:
            logger.debug("Export stats using the %s module" % e)
            thread = threading.Thread(target=self._exports[e].update,
                                      args=(input_stats,))
            # threads.append(thread)
            thread.start()

    def getAll(self):
        """Return all the stats (list)."""
        return [self._plugins[p].get_raw() for p in self._plugins]

    def getAllAsDict(self):
        """Return all the stats (dict)."""
        return {p: self._plugins[p].get_raw() for p in self._plugins}

    def getAllExports(self, plugin_list=None):
        """
        Return all the stats to be exported (list).
        Default behavor is to export all the stat
        if plugin_list is provided, only export stats of given plugin (list)
        """
        if plugin_list is None:
            # All plugins should be exported
            plugin_list = self._plugins
        return [self._plugins[p].get_export() for p in self._plugins]

    def getAllExportsAsDict(self, plugin_list=None):
        """
        Return all the stats to be exported (list).
        Default behavor is to export all the stat
        if plugin_list is provided, only export stats of given plugin (list)
        """
        if plugin_list is None:
            # All plugins should be exported
            plugin_list = self._plugins
        return {p: self._plugins[p].get_export() for p in plugin_list}

    def getAllLimits(self):
        """Return the plugins limits list."""
        return [self._plugins[p].limits for p in self._plugins]

    def getAllLimitsAsDict(self, plugin_list=None):
        """
        Return all the stats limits (dict).
        Default behavor is to export all the limits
        if plugin_list is provided, only export limits of given plugin (list)
        """
        if plugin_list is None:
            # All plugins should be exported
            plugin_list = self._plugins
        return {p: self._plugins[p].limits for p in plugin_list}

    def getAllViews(self):
        """Return the plugins views."""
        return [self._plugins[p].get_views() for p in self._plugins]

    def getAllViewsAsDict(self):
        """Return all the stats views (dict)."""
        return {p: self._plugins[p].get_views() for p in self._plugins}

    def get_plugin_list(self):
        """Return the plugin list."""
        return self._plugins

    def get_plugin(self, plugin_name):
        """Return the plugin name."""
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]
        else:
            return None

    def end(self):
        """End of the Glances stats."""
        # Close export modules
        for e in self._exports:
            self._exports[e].exit()
        # Close plugins
        for p in self._plugins:
            self._plugins[p].exit()
