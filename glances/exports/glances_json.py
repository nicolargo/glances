"""JSON interface class."""

import sys

from glances.globals import json_dumps
from glances.compat import PY3, listkeys
from glances.logger import logger
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the JSON export module."""

    def __init__(self, config=None, args=None):
        """Init the JSON export IF."""
        super(Export, self).__init__(config=config, args=args)

        # JSON file name
        self.json_filename = args.export_json_file

        # Set the JSON output file
        try:
            if PY3:
                self.json_file = open(self.json_filename, 'w')
                self.json_file.close()
            else:
                self.json_file = open(self.json_filename, 'wb')
                self.json_file.close()
        except IOError as e:
            logger.critical("Cannot create the JSON file: {}".format(e))
            sys.exit(2)

        logger.info("Exporting stats to file: {}".format(self.json_filename))

        self.export_enable = True

        # Buffer for dict of stats
        self.buffer = {}

    def exit(self):
        """Close the JSON file."""
        logger.debug("Finalise export interface %s" % self.export_name)
        self.json_file.close()

    def export(self, name, columns, points):
        """Export the stats to the JSON file."""

        # Check for completion of loop for all exports
        if name == self.last_exported_list()[0] and self.buffer != {}:
            # One whole loop has been completed
            # Flush stats to file
            logger.debug("Exporting stats ({}) to JSON file ({})".format(listkeys(self.buffer), self.json_filename))

            # Export stats to JSON file
            if PY3:
                with open(self.json_filename, "w") as self.json_file:
                    self.json_file.write("{}\n".format(json_dumps(self.buffer)))
            else:
                with open(self.json_filename, "wb") as self.json_file:
                    self.json_file.write("{}\n".format(json_dumps(self.buffer)))

            # Reset buffer
            self.buffer = {}

        # Add current stat to the buffer
        self.buffer[name] = dict(zip(columns, points))
