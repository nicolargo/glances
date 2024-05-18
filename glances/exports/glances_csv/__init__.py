#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""CSV interface class."""

import csv
import os.path
import sys
import time

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the CSV export module."""

    def __init__(self, config=None, args=None):
        """Init the CSV export IF."""
        super().__init__(config=config, args=args)

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
            except OSError as e:
                logger.critical(f"Cannot open existing CSV file: {e}")
                sys.exit(2)
            self.old_header = next(reader, None)
            self.csv_file.close()

        try:
            self.csv_file = open_csv_file(self.csv_filename, file_mode)
            self.writer = csv.writer(self.csv_file)
        except OSError as e:
            logger.critical(f"Cannot create the CSV file: {e}")
            sys.exit(2)

        logger.info(f"Stats exported to CSV file: {self.csv_filename}")

        self.export_enable = True

        self.first_line = True

    def exit(self):
        """Close the CSV file."""
        logger.debug(f"Finalise export interface {self.export_name}")
        self.csv_file.close()

    def update(self, stats):
        """Update stats in the CSV output file.
        Note: This class overwrite the one in the parent class because we need to manage the header.
        """
        # Get the stats
        all_stats = stats.getAllExportsAsDict(plugin_list=self.plugins_to_export(stats))

        # Init data with timestamp (issue#708)
        if self.first_line:
            csv_header = ['timestamp']
        csv_data = [time.strftime('%Y-%m-%d %H:%M:%S')]

        # Loop over plugins to export
        for plugin in self.plugins_to_export(stats):
            export_names, export_values = self.build_export(all_stats[plugin])
            if self.first_line:
                csv_header += export_names
            csv_data += export_values

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
                logger.debug(f"Old header: {self.old_header}")
                logger.debug(f"New header: {csv_header}")
            else:
                # Header are equals, ready to write data
                self.old_header = None
            # Only do this once
            self.first_line = False
        # Manage data
        if self.old_header is None:
            self.writer.writerow(csv_data)
            self.csv_file.flush()

    def export(self, name, columns, points):
        """Export the stats to the CSV file.
        For the moment everything is done in the update method."""


def open_csv_file(file_name, file_mode):
    return open(file_name, file_mode, newline='')
