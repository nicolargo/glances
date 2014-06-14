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

"""CSV interface class."""

# Import sys libs
import csv
import sys

# Import Glances libs
from glances.core.glances_globals import is_py3

# List of stats enabled in the CSV output
csv_stats_list = ['cpu', 'load', 'mem', 'memswap']


class GlancesCSV(object):

    """This class manages the CSV output."""

    def __init__(self, args=None):
        # CSV file name
        self.csv_filename = args.output_csv

        # Set the CSV output file
        try:
            if is_py3:
                self.csv_file = open(self.csv_filename, 'w', newline='')
            else:
                self.csv_file = open(self.csv_filename, 'wb')
            self.writer = csv.writer(self.csv_file)
        except IOError as e:
            print(_("Error: Cannot create the CSV file: {0}").format(e))
            sys.exit(2)

        print(_("Stats dumped to CSV file: {0}").format(self.csv_filename))

    def exit(self):
        """Close the CSV file."""
        self.csv_file.close()

    def update(self, stats):
        """Update stats in the CSV output file."""
        all_stats = stats.getAll()
        plugins = stats.getAllPlugins()

        # Loop over available plugin
        i = 0
        for plugin in plugins:
            if plugin in csv_stats_list:
                fieldnames = all_stats[i].keys()
                fieldvalues = all_stats[i].values()
                # First line: header
                csv_header = ['# ' + plugin + ': ' + '|'.join(fieldnames)]
                self.writer.writerow(csv_header)
                # Second line: stats
                self.writer.writerow(list(fieldvalues))
            i += 1

        self.csv_file.flush()
