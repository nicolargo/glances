#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""InfluxDB (for InfluxDB 3.x) interface class."""

import sys
from platform import node

from influxdb_client_3 import InfluxDBClient3

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the InfluxDB export module."""

    def __init__(self, config=None, args=None):
        """Init the InfluxDB export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.host = None
        self.port = None
        self.org = None
        self.database = None
        self.token = None

        # Optional configuration keys
        self.prefix = None
        self.tags = None
        self.hostname = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf(
            "influxdb3",
            mandatories=["host", "port", "org", "database", "token"],
            options=["prefix", "tags"],
        )
        if not self.export_enable:
            exit("Missing influxdb3 config")

        # The hostname is always add as a tag
        self.hostname = node().split(".")[0]

        # Init the InfluxDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the InfluxDB server."""
        if not self.export_enable:
            return None

        try:
            db = InfluxDBClient3(
                host=self.host,
                org=self.org,
                database=self.database,
                token=self.token,
            )
        except Exception as e:
            logger.critical(f"Cannot connect to InfluxDB database '{self.database}' ({e})")
            sys.exit(2)

        if self.database == db._database:
            logger.info(
                f"Stats will be exported to InfluxDB server {self.host}:{self.port} in {self.database} database"
            )
        else:
            logger.critical(f"InfluxDB database '{self.database}' did not exist. Please create it")
            sys.exit(2)

        return db

    def export(self, name, columns, points):
        """Write the points to the InfluxDB server."""
        # Manage prefix
        if self.prefix is not None:
            name = self.prefix + "." + name
        # Write input to the InfluxDB database
        if not points:
            logger.debug(f"Cannot export empty {name} stats to InfluxDB")
        else:
            try:
                self.client.write(
                    record=self.normalize_for_influxdb(name, columns, points),
                    time_precision="s",
                )
            except Exception as e:
                # Log level set to warning instead of error (see: issue #1561)
                logger.warning(f"Cannot export {name} stats to InfluxDB ({e})")
            else:
                logger.debug(f"Export {name} stats to InfluxDB")
