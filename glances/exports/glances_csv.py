# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""CSV interface class."""

# Import sys libs
import csv
import sys

# Import Glances lib
from glances.core.glances_globals import is_py3
from glances.core.glances_logging import logger
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the CSV export module."""

    def __init__(self, config=None, args=None):
        """Init the CSV export IF."""
        GlancesExport.__init__(self, config=config, args=args)

        # CSV file name
        self.csv_filename = args.export_csv

        # Set the CSV output file
        try:
            if is_py3:
                self.csv_file = open(self.csv_filename, 'w', newline='')
            else:
                self.csv_file = open(self.csv_filename, 'wb')
            self.writer = csv.writer(self.csv_file)
        except IOError as e:
            logger.critical("Cannot create the CSV file: {0}".format(e))
            sys.exit(2)

        logger.info("Stats exported to CSV file: {0}".format(self.csv_filename))

        self.export_enable = True

        self.first_line = True

    def exit(self):
        """Close the CSV file."""
        logger.debug("Finalise export interface %s" % self.export_name)
        self.csv_file.close()

    def update(self, stats):
        """Update stats in the CSV output file."""
        csv_header = []
        csv_data = []

        # Get the stats
        all_stats = stats.getAllExports()
        plugins = stats.getAllPlugins()

        # Loop over available plugin
        for i, plugin in enumerate(plugins):
            if plugin in self.plugins_to_export():
                if isinstance(all_stats[i], list):
                    for stat in all_stats[i]:
                        # First line: header
                        if self.first_line:
                            csv_header += ('{0}_{1}_{2}'.format(
                                plugin, self.get_item_key(stat), item) for item in stat)
                        # Others lines: stats
                        fieldvalues = stat.values()
                        csv_data += fieldvalues
                elif isinstance(all_stats[i], dict):
                    # First line: header
                    if self.first_line:
                        fieldnames = all_stats[i].keys()
                        csv_header += ('{0}_{1}'.format(plugin, fieldname)
                                       for fieldname in fieldnames)
                    # Others lines: stats
                    fieldvalues = all_stats[i].values()
                    csv_data += fieldvalues

        # Export to CSV
        if self.first_line:
            self.writer.writerow(csv_header)
            self.first_line = False
        self.writer.writerow(csv_data)
        self.csv_file.flush()
