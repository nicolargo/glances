#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — CouchDB export module (P3-3, wave C).

Ported from the v4 module in this directory: same `[couchdb]` section (user
and password stay mandatory, CouchDB 3+ requires them), the `db` database is
created when missing, and one document per plugin and tick:
`dict(zip(columns, points))` plus `type` (the plugin name) and `time` (v4's
ISO string). `pycouchdb` is imported when the exporter starts.

pycouchdb takes its credentials from the server URL, so that URL is never
logged, and the user and password are percent-encoded in it (pycouchdb
decodes them) so that a password holding `@`, `:` or `/` still works.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Write Glances stats to a CouchDB server."""

    export_name = "couchdb"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.db: str | None = None
        self.user: str | None = None
        self.password: str | None = None
        if not self.load_conf("couchdb", mandatories=("host", "port", "db", "user", "password")):
            logger.critical("Missing couchdb config")
            sys.exit(2)
        self.server: Any = None
        self.client = self.init()

    def init(self) -> Any:
        try:
            import pycouchdb
        except ImportError as e:
            logger.critical("Export couchdb needs the pycouchdb library (%s)", e)
            sys.exit(2)
        # @TODO (v4): https
        server_uri = f"http://{quote(self.user, safe='')}:{quote(self.password, safe='')}@{self.host}:{self.port}/"
        try:
            self.server = pycouchdb.Server(server_uri)
            version = self.server.info()["version"]
        except Exception as e:
            logger.critical("Cannot connect to CouchDB server %s:%s (%s)", self.host, self.port, self._redact(e))
            sys.exit(2)
        logger.info("Connected to the CouchDB server version %s", version)

        try:
            self.server.database(self.db)
        except Exception:
            self.server.create(self.db)
            logger.info("Create CouchDB database %s", self.db)
        else:
            logger.info("CouchDB database %s already exist", self.db)
        return self.server.database(self.db)

    def _redact(self, error: Exception) -> str:
        """The error text, with the configured credentials masked."""
        text = str(error)
        for secret in (self.password, self.user):
            if secret:
                text = text.replace(quote(secret, safe=""), "***").replace(secret, "***")
        return text

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        data = dict(zip(columns, points))
        data["type"] = name
        data["time"] = datetime.now().isoformat()[:-3] + "Z"
        try:
            self.client.save(data)
        except Exception as e:
            logger.warning("Cannot export %s stats to CouchDB (%s)", name, self._redact(e))
        else:
            logger.debug("Export %s stats to CouchDB", name)

    def exit(self) -> None:
        # The barrier first (see the base class), then close the HTTP session.
        super().exit()
        self.server.resource.session.close()
