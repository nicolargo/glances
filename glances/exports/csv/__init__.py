# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""CSV interface class."""

import os.path
import csv
import sys
import time

from glances.globals import iterkeys, itervalues
from glances.logger import logger
from glances.exports.export import GlancesExport


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
            # Header will be checked later
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
        all_stats = stats.getAllExportsAsDict(plugin_list=self.plugins_to_export(stats))

        # Init data with timestamp (issue#708)
        if self.first_line:
            csv_header = ['timestamp']
        csv_data = [time.strftime('%Y-%m-%d %H:%M:%S')]

        # Loop over plugins to export
        for plugin in self.plugins_to_export(stats):
            if isinstance(all_stats[plugin], list):
                for stat in sorted(all_stats[plugin], key=lambda x: x['key']):
                    # First line: header
                    if self.first_line:
                        csv_header += ['{}_{}_{}'.format(plugin, self.get_item_key(stat), item) for item in stat]
                    # Others lines: stats
                    csv_data += itervalues(stat)
            elif isinstance(all_stats[plugin], dict):
                # First line: header
                if self.first_line:
                    fieldnames = iterkeys(all_stats[plugin])
                    csv_header += ('{}_{}'.format(plugin, fieldname) for fieldname in fieldnames)
                # Others lines: stats
                csv_data += itervalues(all_stats[plugin])

        # Export to CSV
        # Manage header
        if self.first_line:
            if self.old_header is None:
                # New file, write the header on top on the CSV file
                self.writer.writerow(csv_header)
            # File already exist, check if header are compatible
            if self.old_header != csv_header and self.old_header is not None:
                # Header are different, log an error and do not write data
                logger.error("Cannot append data to existing CSV file. Headers are different.")
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
    return open(file_name, file_mode, newline='')
