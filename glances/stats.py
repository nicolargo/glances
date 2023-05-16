# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The stats manager."""

import collections
import os
import sys
import threading
import traceback
from importlib import import_module

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
        self.first_export = True
        self.load_modules(self.args)

    def __getattr__(self, item):
        """Overwrite the getattr method in case of attribute is not found.

        The goal is to dynamically generate the following methods:
        - getPlugname(): return Plugname stat in JSON format
        - getViewsPlugname(): return views of the Plugname stat in JSON format
        """
        # Check if the attribute starts with 'get'
        if item.startswith('getViews'):
            # Get the plugin name
            plugname = item[len('getViews') :].lower()
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
            plugname = item[len('get') :].lower()
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
        # Active plugins dictionary
        self._plugins = collections.defaultdict(dict)
        # Load the plugins
        self.load_plugins(args=args)

        # Init the export modules dict
        # Active exporters dictionary
        self._exports = collections.defaultdict(dict)
        # All available exporters dictionary
        self._exports_all = collections.defaultdict(dict)
        # Load the export modules
        self.load_exports(args=args)

        # Restoring system path
        sys.path = sys_path

    def _load_plugin(self, plugin_path, args=None, config=None):
        """Load the plugin, init it and add to the _plugin dict."""
        # The key is the plugin_path
        # except when it starts with glances_xxx
        # generate self._plugins_list["xxx"] = <instance of xxx Plugin>
        if plugin_path.startswith('glances_'):
            # Avoid circular loop when Glances plugin uses lib with same name
            # Example: docker should be named to glances_docker
            name = plugin_path.split('glances_')[1]
        else:
            name = plugin_path
        # Load the plugin class
        try:
            # Import the plugin
            plugin = import_module('glances.plugins.' + plugin_path + '.model')
            # Init and add the plugin to the dictionary
            self._plugins[name] = plugin.PluginModel(args=args, config=config)
        except Exception as e:
            # If a plugin can not be loaded, display a critical message
            # on the console but do not crash
            logger.critical("Error while initializing the {} plugin ({})".format(name, e))
            logger.error(traceback.format_exc())
            # An error occurred, disable the plugin
            if args is not None:
                setattr(args, 'disable_' + name, False)
        else:
            # Manage the default status of the plugin (enable or disable)
            if args is not None:
                # If the all key is set in the disable_plugin option then look in the enable_plugin option
                if getattr(args, 'disable_all', False):
                    logger.debug('%s => %s', name, getattr(args, 'enable_' + name, False))
                    setattr(args, 'disable_' + name, not getattr(args, 'enable_' + name, False))
                else:
                    setattr(args, 'disable_' + name, getattr(args, 'disable_' + name, False))

    def load_plugins(self, args=None):
        """Load all plugins in the 'plugins' folder."""
        start_duration = Counter()

        for item in os.listdir(plugins_path):
            if os.path.isdir(os.path.join(plugins_path, item)) and not item.startswith('__') and item != 'plugin':
                # Load the plugin
                start_duration.reset()
                self._load_plugin(os.path.basename(item), args=args, config=self.config)
                logger.debug("Plugin {} started in {} seconds".format(item, start_duration.get()))

        # Log plugins list
        logger.debug("Active plugins list: {}".format(self.getPluginsList()))

    def load_exports(self, args=None):
        """Load all exporters in the 'exports' folder."""
        start_duration = Counter()

        if args is None:
            return False

        for item in os.listdir(exports_path):
            if os.path.isdir(os.path.join(exports_path, item)) and not item.startswith('__'):
                # Load the exporter
                start_duration.reset()
                if item.startswith('glances_'):
                    # Avoid circular loop when Glances exporter uses lib with same name
                    # Example: influxdb should be named to glances_influxdb
                    exporter_name = os.path.basename(item).split('glances_')[1]
                else:
                    exporter_name = os.path.basename(item)
                # Set the disable_<name> to False by default
                setattr(self.args, 'export_' + exporter_name, getattr(self.args, 'export_' + exporter_name, False))
                # We should import the module
                if getattr(self.args, 'export_' + exporter_name, False):
                    # Import the export module
                    export_module = import_module(item)
                    # Add the exporter instance to the active exporters dictionary
                    self._exports[exporter_name] = export_module.Export(args=args, config=self.config)
                    # Add the exporter instance to the available exporters dictionary
                    self._exports_all[exporter_name] = self._exports[exporter_name]
                else:
                    # Add the exporter name to the available exporters dictionary
                    self._exports_all[exporter_name] = exporter_name
                logger.debug("Exporter {} started in {} seconds".format(exporter_name, start_duration.get()))

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
            return [p for p in self._plugins if self._plugins[p].is_enabled()]
        else:
            return [p for p in self._plugins]

    def getExportsList(self, enable=True):
        """Return the exports list.

        if enable is True, only return the active exporters (default)
        if enable is False, return all the exporters

        :return: list of export module names
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
            if self._plugins[p].is_disabled():
                # If current plugin is disable
                # then continue to next plugin
                continue
            # Update the stats...
            self._plugins[p].update()
            # ... the history
            self._plugins[p].update_stats_history()
            # ... and the views
            self._plugins[p].update_views()

    def export(self, input_stats=None):
        """Export all the stats.

        Each export module is ran in a dedicated thread.
        """
        if self.first_export:
            logger.debug("Do not export stats during the first iteration because some information are missing")
            self.first_export = False
            return False

        input_stats = input_stats or {}

        for e in self._exports:
            logger.debug("Export stats using the %s module" % e)
            thread = threading.Thread(target=self._exports[e].update, args=(input_stats,))
            thread.start()

        return True

    def getAll(self):
        """Return all the stats (list)."""
        return [self._plugins[p].get_raw() for p in self._plugins]

    def getAllAsDict(self):
        """Return all the stats (dict)."""
        return {p: self._plugins[p].get_raw() for p in self._plugins}

    def getAllExports(self, plugin_list=None):
        """Return all the stats to be exported (list).

        Default behavior is to export all the stat
        if plugin_list is provided, only export stats of given plugin (list)
        """
        if plugin_list is None:
            # All enabled plugins should be exported
            plugin_list = self.getPluginsList()
        return [self._plugins[p].get_export() for p in self._plugins]

    def getAllExportsAsDict(self, plugin_list=None):
        """Return all the stats to be exported (list).

        Default behavior is to export all the stat
        if plugin_list is provided, only export stats of given plugin (list)
        """
        if plugin_list is None:
            # All enabled plugins should be exported
            plugin_list = self.getPluginsList()
        return {p: self._plugins[p].get_export() for p in plugin_list}

    def getAllLimits(self, plugin_list=None):
        """Return the plugins limits list.

        Default behavior is to export all the limits
        if plugin_list is provided, only export limits of given plugin (list)
        """
        if plugin_list is None:
            # All enabled plugins should be exported
            plugin_list = self.getPluginsList()
        return [self._plugins[p].limits for p in plugin_list]

    def getAllLimitsAsDict(self, plugin_list=None):
        """Return all the stats limits (dict).

        Default behavior is to export all the limits
        if plugin_list is provided, only export limits of given plugin (list)
        """
        if plugin_list is None:
            # All enabled plugins should be exported
            plugin_list = self.getPluginsList()
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
