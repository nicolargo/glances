#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

# Import system libs
import sys
import os
import collections

# Import Glances libs
from ..core.glances_globals import *

class GlancesStats:
    """
    This class store, update and give stats
    """

    # Internal dictionnary with all plugins instances
    _plugins = {}


    def __init__(self):
        """
        Init the stats
        """

        # Load the plugins
        self.load_plugins()


    def __getattr__(self, item):
        """
        Overwrite the getattr in case of attribute is not found 
        The goal is to dynamicaly generate the API get'Stats'() methods
        """
        
        # print "!!! __getattr__ in the GlancesStats classe"
        # print "!!! Method: %s" % item
        header = 'get'
        # Check if the attribute starts with 'get'
        if (item.startswith(header)):
            # Get the plugin name
            plugname = item[len(header):].lower()
            # Get the plugin instance
            plugin = self._plugins[plugname]
            # !!! Debug
            # print "Check if method get_stats exist for plugin %s" % plugname
            # print self._plugins
            # print plugin
            if (hasattr(plugin, 'get_stats')):
                # The method get_stats exist, return it
                return getattr(plugin, 'get_stats')
            else:
                # The method get_stats is not found for the plugin
                raise AttributeError(item)
        else:
            # Default behavior
            raise AttributeError(item)


    def load_plugins(self):
        """
        Load all plugins in the "plugins" folder
        """

        plug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../plugins")   
        sys.path.insert(0, plug_dir)

        header = "glances_"
        for plug in os.listdir(plug_dir):
            if (plug.startswith(header) and plug.endswith(".py") and
                plug != (header + "plugin.py")):
                # Import the plugin
                m = __import__(os.path.basename(plug)[:-3])
                # Add the plugin to the dictionnary
                # The key is the plugin name
                # for example, the file glances_xxx.py
                # generate self._plugins_list["xxx"] = ...
                plugname = os.path.basename(plug)[len(header):-3].lower()
                self._plugins[plugname] = m.Plugin()


    def __update__(self, input_stats):
        """
        Update the stats
        """

        # For each plugins, call the update method
        for p in self._plugins:
            self._plugins[p].update()


    def update(self, input_stats={}):
        # Update the stats
        self.__update__(input_stats)


class GlancesStatsServer(GlancesStats):

    def __init__(self):
        # Init the stats
        GlancesStats.__init__(self)

        # Init the all_stats dict used by the server
        # all_stats is a dict of dicts filled by the server
        self.all_stats = collections.defaultdict(dict)


    def update(self, input_stats = {}):
        """
        Update the stats
        """
        
        # Update the stats
        GlancesStats.__update__(self, input_stats)

        # Build the all_stats with the get_raw() method of the plugins
        for p in self._plugins:
            self.all_stats[p] = self._plugins[p].get_raw()
            

    def getAll(self):
        return self.all_stats
        