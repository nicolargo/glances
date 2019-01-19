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

"""Stdout interface class."""

import time

from glances.logger import logger
from glances.compat import printandflush


class GlancesStdout(object):

    """
    This class manages the Stdout display.
    """

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Build the list of plugin and/or plugin.attribute to display
        self.plugins_list = self.build_list()

    def build_list(self):
        """Return a list of tuples taken from self.args.stdout
        [(plugin, attribute), ... ]"""
        ret = []
        for p in self.args.stdout.split(','):
            if '.' in p:
                p, a = p.split('.')
            else:
                a = None
            ret.append((p, a))
        return ret

    def end(self):
        pass

    def update(self,
               stats,
               duration=3):
        """Display stats to stdout.
        Refresh every duration second.
        """
        for plugin, attribute in self.plugins_list:
            # Check if the plugin exist and is enable
            if plugin in stats.getPluginsList() and \
               stats.get_plugin(plugin).is_enable():
                stat = stats.get_plugin(plugin).get_export()
            else:
                continue
            # Display stats
            if attribute is not None:
                # With attribute
                try:
                    printandflush("{}.{}: {}".format(plugin, attribute,
                                                     stat[attribute]))
                except KeyError as err:
                    logger.error("Can not display stat {}.{} ({})".format(plugin, attribute, err))
            else:
                # Without attribute
                printandflush("{}: {}".format(plugin, stat))

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)
