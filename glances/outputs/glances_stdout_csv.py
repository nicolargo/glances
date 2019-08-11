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

"""StdoutCsv interface class."""

import time

from glances.logger import logger
from glances.compat import printandflush


class GlancesStdoutCsv(object):

    """
    This class manages the StdoutCsv display.
    """

    separator = ','
    na = 'N/A'

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Display the header only on the first line
        self.header = True

        # Build the list of plugin and/or plugin.attribute to display
        self.plugins_list = self.build_list()

    def build_list(self):
        """Return a list of tuples taken from self.args.stdout
        [(plugin, attribute), ... ]"""
        ret = []
        for p in self.args.stdout_csv.split(','):
            if '.' in p:
                p, a = p.split('.')
            else:
                a = None
            ret.append((p, a))
        return ret

    def end(self):
        pass

    def build_header(self, plugin, attribute, stat):
        """Build and return the header line"""
        line = ''

        if attribute is not None:
            line += '{}.{}{}'.format(plugin, attribute, self.separator)
        else:
            if isinstance(stat, dict):
                for k in stat.keys():
                    line += '{}.{}{}'.format(plugin,
                                             str(k),
                                             self.separator)
            elif isinstance(stat, list):
                for i in stat:
                    if isinstance(i, dict) and 'key' in i:
                        for k in i.keys():
                            line += '{}.{}.{}{}'.format(plugin,
                                                        str(i['key']),
                                                        str(k),
                                                        self.separator)
            else:
                line += '{}{}'.format(plugin, self.separator)

        return line

    def build_data(self, plugin, attribute, stat):
        """Build and return the data line"""
        line = ''

        if attribute is not None:
            line += '{}{}'.format(str(stat.get(attribute, self.na)),
                                  self.separator)
        else:
            if isinstance(stat, dict):
                for v in stat.values():
                    line += '{}{}'.format(str(v), self.separator)
            elif isinstance(stat, list):
                for i in stat:
                    if isinstance(i, dict) and 'key' in i:
                        for v in i.values():
                            line += '{}{}'.format(str(v), self.separator)
            else:
                line += '{}{}'.format(str(stat), self.separator)

        return line

    def update(self,
               stats,
               duration=3):
        """Display stats to stdout.
        Refresh every duration second.
        """
        # Build the stats list
        line = ''
        for plugin, attribute in self.plugins_list:
            # Check if the plugin exist and is enable
            if plugin in stats.getPluginsList() and \
               stats.get_plugin(plugin).is_enable():
                stat = stats.get_plugin(plugin).get_export()
            else:
                continue

            # Build the line to display (header or data)
            if self.header:
                line += self.build_header(plugin, attribute, stat)
            else:
                line += self.build_data(plugin, attribute, stat)

        # Display the line (without the last 'separator')
        printandflush(line[:-1])

        # Display header one time
        self.header = False

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)
