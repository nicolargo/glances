#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""InfluxDB (up to InfluxDB 1.7.x) interface class."""

import sys
from platform import node

from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the InfluxDB export module."""

    def __init__(self, config=None, args=None):
        """Init the InfluxDB export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.user = None
        self.password = None
        self.db = None

        # Optional configuration keys
        self.protocol = "http"
        self.prefix = None
        self.tags = None
        self.hostname = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf(
            "influxdb",
            mandatories=["host", "port", "user", "password", "db"],
            options=["protocol", "prefix", "tags"],
        )
        if not self.export_enable:
            exit("Missing influxdb config")

        # The hostname is always add as a tag
        self.hostname = node().split(".")[0]

        # Init the InfluxDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the InfluxDB server."""
        if not self.export_enable:
            return None

        # Correct issue #1530
        if self.protocol is not None and (self.protocol.lower() == "https"):
            ssl = True
        else:
            ssl = False

        try:
            db = InfluxDBClient(
                host=self.host,
                port=self.port,
                ssl=ssl,
                verify_ssl=False,
                username=self.user,
                password=self.password,
                database=self.db,
            )
            get_all_db = [i["name"] for i in db.get_list_database()]
        except InfluxDBClientError as e:
            logger.critical(f"Cannot connect to InfluxDB database '{self.db}' ({e})")
            sys.exit(2)

        if self.db in get_all_db:
            logger.info(f"Stats will be exported to InfluxDB server: {db._baseurl}")
        else:
            logger.critical(f"InfluxDB database '{self.db}' did not exist. Please create it")
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
                self.client.write_points(
                    self.normalize_for_influxdb(name, columns, points),
                    time_precision="s",
                )
            except Exception as e:
                # Log level set to warning instead of error (see: issue #1561)
                logger.warning(f"Cannot export {name} stats to InfluxDB ({e})")
            else:
                logger.debug(f"Export {name} stats to InfluxDB")
