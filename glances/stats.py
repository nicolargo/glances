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
import pathlib
import sys
import threading
import traceback
from importlib import import_module

from glances.globals import exports_path, plugins_path, sys_path
from glances.logger import logger
from glances.timer import Counter


class GlancesStats:
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
                # The method get_json_views exist, return it
                return getattr(plugin, 'get_json_views')
            # The method get_views is not found for the plugin
            raise AttributeError(item)
        if item.startswith('get'):
            # Get the plugin name
            plugname = item[len('get') :].lower()
            # Get the plugin instance
            plugin = self._plugins[plugname]
            if hasattr(plugin, 'get_json'):
                # The method get_json exist, return it
                return getattr(plugin, 'get_json')
            # The method get_stats is not found for the plugin
            raise AttributeError(item)
        # Default behavior
        raise AttributeError(item)

    def load_modules(self, args):
        """Wrapper to load: plugins and export modules."""

        # Init the plugins dict
        # Active plugins dictionary
        self._plugins = collections.defaultdict(dict)
        # Load the plugins
        self.load_plugins(args=args)

        # Load addititional plugins
        self.load_additional_plugins(args=args, config=self.config)

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
        # Load the plugin class
        try:
            # Import the plugin
            plugin = import_module('glances.plugins.' + plugin_path)
            # Init and add the plugin to the dictionary
            self._plugins[plugin_path] = plugin.PluginModel(args=args, config=config)
        except Exception as e:
            # If a plugin can not be loaded, display a critical message
            # on the console but do not crash
            logger.critical(f"Error while initializing the {plugin_path} plugin ({e})")
            logger.error(traceback.format_exc())
            # An error occurred, disable the plugin
            if args is not None:
                setattr(args, 'disable_' + plugin_path, False)
        else:
            # Manage the default status of the plugin (enable or disable)
            if args is not None:
                # If the all keys are set in the disable_plugin option then look in the enable_plugin option
                if getattr(args, 'disable_all', False):
                    logger.debug('%s => %s', plugin_path, getattr(args, 'enable_' + plugin_path, False))
                    setattr(args, 'disable_' + plugin_path, not getattr(args, 'enable_' + plugin_path, False))
                else:
                    setattr(args, 'disable_' + plugin_path, getattr(args, 'disable_' + plugin_path, False))

    def load_plugins(self, args=None):
        """Load all plugins in the 'plugins' folder."""
        start_duration = Counter()

        for item in os.listdir(plugins_path):
            if os.path.isdir(os.path.join(plugins_path, item)) and not item.startswith('__') and item != 'plugin':
                # Load the plugin
                start_duration.reset()
                self._load_plugin(os.path.basename(item), args=args, config=self.config)
                logger.debug(f"Plugin {item} started in {start_duration.get()} seconds")

        # Log plugins list
        logger.debug(f"Active plugins list: {self.getPluginsList()}")

    def load_additional_plugins(self, args=None, config=None):
        """Load additional plugins if defined"""

        def get_addl_plugins(self, plugin_path):
            """Get list of additional plugins"""
            _plugin_list = []
            for plugin in os.listdir(plugin_path):
                path = os.path.join(plugin_path, plugin)
                if os.path.isdir(path) and not path.startswith('__'):
                    # Poor man's walk_pkgs - can't use pkgutil as the module would be already imported here!
                    for fil in pathlib.Path(path).glob('*.py'):
                        if fil.is_file():
                            with open(fil) as fd:
                                if 'PluginModel' in fd.read():
                                    _plugin_list.append(plugin)
                                    break

            return _plugin_list

        path = None
        # Skip section check as implied by has_option
        if config and config.parser.has_option('global', 'plugin_dir'):
            path = config.parser['global']['plugin_dir']

        if args and 'plugin_dir' in args and args.plugin_dir:
            path = args.plugin_dir

        if path:
            # Get list before starting the counter
            _sys_path = sys.path
            start_duration = Counter()
            # Ensure that plugins can be found in plugin_dir
            sys.path.insert(0, path)
            for plugin in get_addl_plugins(self, path):
                if plugin in sys.modules:
                    logger.warn(f"Plugin {plugin} already in sys.modules, skipping (workaround: rename plugin)")
                else:
                    start_duration.reset()
                    try:
                        _mod_loaded = import_module(plugin + '.model')
                        self._plugins[plugin] = _mod_loaded.PluginModel(args=args, config=config)
                        logger.debug(f"Plugin {plugin} started in {start_duration.get()} seconds")
                    except Exception as e:
                        # If a plugin can not be loaded, display a critical message
                        # on the console but do not crash
                        logger.critical(f"Error while initializing the {plugin} plugin ({e})")
                        logger.error(traceback.format_exc())
                        # An error occurred, disable the plugin
                        if args:
                            setattr(args, 'disable_' + plugin, False)

            sys.path = _sys_path
            # Log plugins list
            logger.debug(f"Active additional plugins list: {self.getPluginsList()}")

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
                logger.debug(f"Exporter {exporter_name} started in {start_duration.get()} seconds")

        # Log plugins list
        logger.debug(f"Active exports modules list: {self.getExportsList()}")
        return True

    def getPluginsList(self, enable=True):
        """Return the plugins list.

        if enable is True, only return the active plugins (default)
        if enable is False, return all the plugins

        Return: list of plugin name
        """
        if enable:
            return [p for p in self._plugins if self._plugins[p].is_enabled()]
        return list(self._plugins)

    def getExportsList(self, enable=True):
        """Return the exports list.

        if enable is True, only return the active exporters (default)
        if enable is False, return all the exporters

        :return: list of export module names
        """
        if enable:
            return list(self._exports)
        return list(self._exports_all)

    def load_limits(self, config=None):
        """Load the stats limits (except the one in the exclude list)."""
        # For each plugins (enable or not), call the load_limits method
        for p in self.getPluginsList(enable=False):
            self._plugins[p].load_limits(config)

    def __update_plugin(self, p):
        """Update stats, history and views for the given plugin name p"""
        self._plugins[p].update()
        self._plugins[p].update_stats_history()
        self._plugins[p].update_views()

    def update(self):
        """Wrapper method to update all stats.

        Only called by standalone and server modes
        """
        # Start update of all enable plugins
        for p in self.getPluginsList(enable=True):
            self.__update_plugin(p)

    def export(self, input_stats=None):
        """Export all the stats.

        Each export module is ran in a dedicated thread.
        """
        if self.first_export:
            logger.debug("Do not export stats during the first iteration because some information are missing")
            self.first_export = False
            return False

        input_stats = input_stats or {}

        for e in self.getExportsList():
            logger.debug(f"Export stats using the {e} module")
            thread = threading.Thread(target=self._exports[e].update, args=(input_stats,))
            thread.start()

        return True

    def getAll(self):
        """Return all the stats (list).
        This method is called byt the XML/RPC API.
        It should return all the plugins (enable or not) because filtering can be done by the client.
        """
        return [self._plugins[p].get_raw() for p in self.getPluginsList(enable=False)]

    def getAllAsDict(self, plugin_list=None):
        """Return all the stats (as dict).
        This method is called by the RESTFul API.
        """
        if plugin_list is None:
            # All enabled plugins should be exported
            plugin_list = self.getPluginsList()
        return {p: self._plugins[p].get_raw() for p in plugin_list}

    def getAllExports(self, plugin_list=None):
        """Return all the stats to be exported as a list.

        Default behavior is to export all the stat
        if plugin_list is provided (list), only export stats of given plugins
        """
        if plugin_list is None:
            # All enabled plugins should be exported
            plugin_list = self.getPluginsList()
        return [self._plugins[p].get_export() for p in plugin_list]

    def getAllExportsAsDict(self, plugin_list=None):
        """Return all the stats to be exported as a dict.

        Default behavior is to export all the stat
        if plugin_list is provided (list), only export stats of given plugins
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

    def getAllViews(self, plugin_list=None):
        """Return the plugins views.
        This method is called byt the XML/RPC API.
        It should return all the plugins views (enable or not) because filtering can be done by the client.
        """
        if plugin_list is None:
            plugin_list = self.getPluginsList(enable=False)
        return [self._plugins[p].get_views() for p in plugin_list]

    def getAllViewsAsDict(self, plugin_list=None):
        """Return all the stats views (dict).
        This method is called by the RESTFul API.
        """
        if plugin_list is None:
            # All enabled plugins should be exported
            plugin_list = self.getPluginsList()
        return {p: self._plugins[p].get_views() for p in plugin_list}

    def get_plugin(self, plugin_name):
        """Return the plugin stats."""
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]
        return None

    def get_plugin_view(self, plugin_name):
        """Return the plugin views."""
        if plugin_name in self._plugins:
            return self._plugins[plugin_name].get_views()
        return None

    def end(self):
        """End of the Glances stats."""
        # Close export modules
        for e in self._exports:
            self._exports[e].exit()
        # Close plugins
        for p in self._plugins:
            self._plugins[p].exit()
