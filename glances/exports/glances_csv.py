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

"""CSV interface class."""

import os.path
import csv
import sys
import time

from glances.compat import PY3, iterkeys, itervalues
from glances.logger import logger
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the CSV export module."""

    def __init__(self, config=None, args=None):
        """Init the CSV export IF."""
        super(Export, self).__init__(config=config, args=args)

        # CSV file name
        self.csv_filename = args.export_csv_file

        # Set the CSV output file
        # (see https://github.com/nicolargo/glances/issues/1525)
        if not os.path.isfile(self.csv_filename) or args.export_csv_overwrite:
            # File did not exist, create it
            file_mode = 'w'
            self.old_header = None
        else:
            # A CSV file already exit, append new data
            file_mode = 'a'
            # Header will be check later
            # Get the existing one
            try:
                self.csv_file = open_csv_file(self.csv_filename, 'r')
                reader = csv.reader(self.csv_file)
            except IOError as e:
                logger.critical("Cannot open existing CSV file: {}".format(e))
                sys.exit(2)
            self.old_header = next(reader, None)
            self.csv_file.close()

        try:
            self.csv_file = open_csv_file(self.csv_filename, file_mode)
            self.writer = csv.writer(self.csv_file)
        except IOError as e:
            logger.critical("Cannot create the CSV file: {}".format(e))
            sys.exit(2)

        logger.info("Stats exported to CSV file: {}".format(self.csv_filename))

        self.export_enable = True

        self.first_line = True

    def exit(self):
        """Close the CSV file."""
        logger.debug("Finalise export interface %s" % self.export_name)
        self.csv_file.close()

    def update(self, stats):
        """Update stats in the CSV output file."""
        # Get the stats
        all_stats = stats.getAllExportsAsDict(plugin_list=self.plugins_to_export())

        # Init data with timestamp (issue#708)
        if self.first_line:
            csv_header = ['timestamp']
        csv_data = [time.strftime('%Y-%m-%d %H:%M:%S')]

        # Loop over plugins to export
        for plugin in self.plugins_to_export():
            if isinstance(all_stats[plugin], list):
                for stat in all_stats[plugin]:
                    # First line: header
                    if self.first_line:
                        csv_header += ('{}_{}_{}'.format(
                            plugin, self.get_item_key(stat), item) for item in stat)
                    # Others lines: stats
                    csv_data += itervalues(stat)
            elif isinstance(all_stats[plugin], dict):
                # First line: header
                if self.first_line:
                    fieldnames = iterkeys(all_stats[plugin])
                    csv_header += ('{}_{}'.format(plugin, fieldname)
                                   for fieldname in fieldnames)
                # Others lines: stats
                csv_data += itervalues(all_stats[plugin])

        # Export to CSV
        # Manage header
        if self.first_line:
            if self.old_header is None:
                # New file, write the header on top on the CSV file
                self.writer.writerow(csv_header)
            # File already exist, check if header are compatible
            if self.old_header != csv_header:
                # Header are differents, log an error and do not write data
                logger.error("Cannot append data to existing CSV file. Headers are differents.")
                logger.debug("Old header: {}".format(self.old_header))
                logger.debug("New header: {}".format(csv_header))
            else:
                # Header are equals, ready to write data
                self.old_header = None
            # Only do this once
            self.first_line = False
        # Manage data
        if self.old_header is None:
            self.writer.writerow(csv_data)
            self.csv_file.flush()


def open_csv_file(file_name, file_mode):
    if PY3:
        csv_file = open(file_name, file_mode, newline='')
    else:
        csv_file = open(file_name, file_mode + 'b')
    return csv_file
