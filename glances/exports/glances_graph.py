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

"""Graph exporter interface class."""

from pygal import DateTimeLine
import pygal.style
import sys
import os
import tempfile
import errno

from glances.logger import logger
from glances.timer import Timer
from glances.compat import iteritems, time_serie_subsample
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the Graph export module."""

    def __init__(self, config=None, args=None):
        """Init the export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Load the Graph configuration file section (is exists)
        self.export_enable = self.load_conf('graph',
                                            options=['path',
                                                     'generate_every',
                                                     'width',
                                                     'height',
                                                     'style'])

        # Manage options (command line arguments overwrite configuration file)
        self.path = args.export_graph_path or self.path
        self.generate_every = int(getattr(self, 'generate_every', 0))
        self.width = int(getattr(self, 'width', 800))
        self.height = int(getattr(self, 'height', 600))
        self.style = getattr(pygal.style,
                             getattr(self, 'style', 'DarkStyle'),
                             pygal.style.DarkStyle)

        # Create export folder
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.critical("Cannot create the Graph output folder {} ({})".format(self.path, e))
                sys.exit(2)

        # Check if output folder is writeable
        try:
            tempfile.TemporaryFile(dir=self.path)
        except OSError as e:
            logger.critical("Graph output folder {} is not writeable".format(self.path))
            sys.exit(2)

        logger.info("Graphs will be created in the {} folder".format(self.path))
        logger.info("Graphs will be created  when 'g' key is pressed (in the CLI interface)")
        if self.generate_every != 0:
            logger.info("Graphs will be created automatically every {} seconds".format(self.generate_every))
            # Start the timer
            self._timer = Timer(self.generate_every)
        else:
            self._timer = None

    def exit(self):
        """Close the files."""
        logger.debug("Finalise export interface %s" % self.export_name)

    def update(self, stats):
        """Generate Graph file in the output folder."""

        if self.generate_every != 0 and self._timer.finished():
            self.args.generate_graph = True
            self._timer.reset()

        if not self.args.generate_graph:
            return

        plugins = stats.getPluginsList()
        for plugin_name in plugins:
            plugin = stats._plugins[plugin_name]
            if plugin_name in self.plugins_to_export():
                self.export(plugin_name, plugin.get_export_history())

        logger.info("Graphs created in the folder {}".format(self.path))
        self.args.generate_graph = False

    def export(self, title, data):
        """Generate graph from the data.

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

        Return:
        * True if the graph have been generated
        * False if the graph have not been generated
        """
        if data == {}:
            return False

        chart = DateTimeLine(title=title.capitalize(),
                             width=self.width,
                             height=self.height,
                             style=self.style,
                             show_dots=False,
                             legend_at_bottom=True,
                             x_label_rotation=20,
                             x_value_formatter=lambda dt: dt.strftime('%Y/%m/%d %H:%M:%S'))
        for k, v in iteritems(time_serie_subsample(data, self.width)):
            chart.add(k, v)
        chart.render_to_file(os.path.join(self.path,
                                          title + '.svg'))
        return True
