# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

from glances.core.glances_globals import plugins_path, sys_path


class GlancesStats(object):

    """This class stores, updates and gives stats."""

    def __init__(self, config=None):
        # Init the plugin list dict
        self._plugins = collections.defaultdict(dict)

        # Load the plugins
        self.load_plugins()

        # Load the limits
        self.load_limits(config)

    def __getattr__(self, item):
        """Overwrite the getattr method in case of attribute is not found.

        The goal is to dynamically generate the following methods:
        - getPlugname(): return Plugname stat in JSON format
        """
        # Check if the attribute starts with 'get'
        if item.startswith('get'):
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

    def load_plugins(self, args=None):
        """Load all plugins in the 'plugins' folder."""
        header = "glances_"
        for item in os.listdir(plugins_path):
            if (item.startswith(header) and
                    item.endswith(".py") and
                    item != (header + "plugin.py")):
                # Import the plugin
                plugin = __import__(os.path.basename(item)[:-3])
                # Add the plugin to the dictionary
                # The key is the plugin name
                # for example, the file glances_xxx.py
                # generate self._plugins_list["xxx"] = ...
                plugin_name = os.path.basename(item)[len(header):-3].lower()
                self._plugins[plugin_name] = plugin.Plugin(args=args)
        # Restoring system path
        sys.path = sys_path

    def getAllPlugins(self):
        """Return the plugins list."""
        return [p for p in self._plugins]

    def load_limits(self, config=None):
        """Load the stats limits."""
        # For each plugins, call the init_limits method
        for p in self._plugins:
            # print "DEBUG: Load limits for %s" % p
            self._plugins[p].load_limits(config)

    def __update__(self, input_stats):
        """Update all the stats."""
        if input_stats == {}:
            # For standalone and server modes
            # For each plugins, call the update method
            for p in self._plugins:
                # print "DEBUG: Update %s stats" % p
                self._plugins[p].update()
        else:
            # For Glances client mode
            # Update plugin stats with items sent by the server
            for p in input_stats:
                self._plugins[p].set_stats(input_stats[p])

    def update(self, input_stats={}):
        """Wrapper method to update the stats."""
        self.__update__(input_stats)

    def getAll(self):
        """Return all the stats."""
        return [self._plugins[p].get_raw() for p in self._plugins]

    def get_plugin_list(self):
        """Return the plugin list."""
        self._plugins

    def get_plugin(self, plugin_name):
        """Return the plugin name."""
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]
        else:
            return None


class GlancesStatsServer(GlancesStats):

    """This class stores, updates and gives stats for the server."""

    def __init__(self, config=None):
        # Init the stats
        GlancesStats.__init__(self, config)

        # Init the all_stats dict used by the server
        # all_stats is a dict of dicts filled by the server
        self.all_stats = collections.defaultdict(dict)

    def update(self, input_stats={}):
        """Update the stats."""
        GlancesStats.update(self)

        # Build the all_stats with the get_raw() method of the plugins
        for p in self._plugins:
            self.all_stats[p] = self._plugins[p].get_raw()

    def getAll(self):
        """Return the stats as a dict."""
        return self.all_stats

    def getAllPlugins(self):
        """Return the plugins list."""
        return [p for p in self._plugins]

    def getAllLimits(self):
        """Return the plugins limits list."""
        return [self._plugins[p].get_limits() for p in self._plugins]


class GlancesStatsClient(GlancesStats):

    """This class stores, updates and gives stats for the client."""

    def __init__(self):
        """Init the GlancesStatsClient class."""
        # Init the plugin list dict
        self._plugins = collections.defaultdict(dict)

    def set_plugins(self, input_plugins):
        """Set the plugin list according to the Glances server."""
        header = "glances_"
        for item in input_plugins:
            # Import the plugin
            plugin = __import__(header + item)
            # Add the plugin to the dictionary
            # The key is the plugin name
            # for example, the file glances_xxx.py
            # generate self._plugins_list["xxx"] = ...
            # print "DEBUG: Init %s plugin" % item
            self._plugins[item] = plugin.Plugin()
        # Restoring system path
        sys.path = sys_path


class GlancesStatsClientSNMP(GlancesStats):

    """This class stores, updates and gives stats for the SNMP client."""

    def __init__(self, config=None, args=None):
        # Init the plugin list dict
        self._plugins = collections.defaultdict(dict)

        # Init the configuration
        self.config = config

        # Init the arguments
        self.args = args

        # Load plugins
        self.load_plugins(args=self.args)

    def check_snmp(self):
        """Chek if SNMP is available on the server."""
        # Import the SNMP client class
        from glances.core.glances_snmp import GlancesSNMPClient

        # Create an instance of the SNMP client
        clientsnmp = GlancesSNMPClient(host=self.args.client,
                                       port=self.args.snmp_port,
                                       version=self.args.snmp_version,
                                       community=self.args.snmp_community,
                                       user=self.args.snmp_user,
                                       auth=self.args.snmp_auth)

        return clientsnmp.get_by_oid("1.3.6.1.2.1.1.5.0") != {}

    def update(self):
        """Update the stats using SNMP."""
        # For each plugins, call the update method
        for p in self._plugins:
            # Set the input method to SNMP
            self._plugins[p].set_input('snmp')
            # print "DEBUG: Update %s stats using SNMP request" % p
            try:
                self._plugins[p].update()
            except Exception as e:
                print(_("Error: Update {0} failed: {1}").format(p, e))
                # pass
