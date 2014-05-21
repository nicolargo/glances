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

# Import sys libs
import sys
try:
    import csv
except ImportError:
    print('CSV module not found. Glances cannot extract to .csv file.')
    sys.exit(1)

# Import Glances libs
from glances.core.glances_globals import is_py3

# List of stats enable in the CSV output
csv_stats_list = [ 'cpu', 'load', 'mem', 'memswap' ]


class glancesCsv:
    """
    This class manages the CSV output
    """

    def __init__(self, args=None):

        # Init refresh time
        self.__refresh_time = args.time

        # CSV file name
        self.__csvfile_name = args.output_csv

        # Set the CSV output file
        try:
            if is_py3:
                self.__csvfile_fd = open(self.__csvfile_name, 'w', newline='')
            else:
                self.__csvfile_fd = open(self.__csvfile_name, 'wb')
            self.__csvfile = csv.writer(self.__csvfile_fd, quoting=csv.QUOTE_NONE)
        except IOError as error:
            print(_("Cannot create the CSV output file: %s") % error)
            sys.exit(2)

        print("{0}: {1}".format(_("Stats dumped in the CSV file"), self.__csvfile_name)) 

    def exit(self):
        self.__csvfile_fd.close()

    def update(self, stats):
        """
        Update stats in the CSV output file
        """

        all_stats = stats.getAll()

        # Loop over available plugin
        i = 0
        for p in stats.getAllPlugins():
            if p in csv_stats_list:
                # First line for comment: csv_comment 
                csv_comment = [ '# ' + str(p) + ': ' + '|'.join(all_stats[i].keys()) ]
                self.__csvfile.writerow(csv_comment)
                # Second line for stats (CSV): csv_stats
                self.__csvfile.writerow(all_stats[i].values())
            i += 1
        self.__csvfile_fd.flush()
