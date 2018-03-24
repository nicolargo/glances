# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2018 Nicolargo <nicolas@nicolargo.com>
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

"""Graph exporter interface class."""

from pygal import DateTimeLine
import sys
import os

from glances.logger import logger
from glances.compat import iteritems
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the Graph export module."""

    def __init__(self, config=None, args=None):
        """Init the export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Graph export folder path
        self._graph_path = args.export_graph_path

        # TODO: Test if the folder exist. Overwise, create it.
        try:
            pass
        except IOError as e:
            logger.critical("Cannot create the CSV file: {}".format(e))
            sys.exit(2)

        logger.info("Graph will be created in folder:: {}".format(self._graph_path))

        self.export_enable = True

    def exit(self):
        """Close the files."""
        logger.debug("Finalise export interface %s" % self.export_name)

    def update(self, stats):
        """Generate Graph file in the output folder."""
        plugins = stats.getPluginsList()
        for plugin_name in plugins:
            plugin = stats._plugins[plugin_name]
            if plugin_name in self.plugins_to_export():
                self.export(plugin_name, plugin.get_export_history())

    def export(self, title, data):
        """Generate one graph per item from the data.

        Example for the mem plugin:
        {'percent': [
            (datetime.datetime(2018, 3, 24, 16, 27, 47, 282070), 51.8),
            (datetime.datetime(2018, 3, 24, 16, 27, 47, 540999), 51.9),
            (datetime.datetime(2018, 3, 24, 16, 27, 50, 653390), 52.0),
            (datetime.datetime(2018, 3, 24, 16, 27, 53, 749702), 52.0),
            (datetime.datetime(2018, 3, 24, 16, 27, 56, 825660), 52.0),
            ...
            ]
        }
        """
        for k, v in iteritems(data):
            chart = DateTimeLine(x_label_rotation=20,
                                 x_value_formatter=lambda dt: dt.strftime('%d, %b %Y at %I:%M:%S %p'))
            chart.add(k, v)
            chart.render_to_file(os.path.join(self._graph_path,
                                              title + '.svg'))
