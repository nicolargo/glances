#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — MongoDB export module (P3-3, wave C).

Ported from the v4 module in this directory: same `[mongodb]` section, one
document per plugin and tick, `dict(zip(columns, points))`, inserted in the
collection named after the plugin, in the `db` database. An unreachable
server at startup is fatal, as in v4. `pymongo` is imported when the
exporter starts.

The credentials reach `MongoClient` as keyword arguments rather than inside
a `mongodb://user:password@...` URI: no URI with a password is ever built,
and `user`/`password` are really optional (v4 crashed without them).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Write Glances stats to a MongoDB server."""

    export_name = "mongodb"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.db: str | None = None
        self.user: str | None = None
        self.password: str | None = None
        if not self.load_conf("mongodb", mandatories=("host", "port", "db"), options=("user", "password")):
            logger.critical("Missing mongodb config")
            sys.exit(2)
        self.client = self.init()

    def init(self) -> Any:
        try:
            import pymongo
        except ImportError as e:
            logger.critical("Export mongodb needs the pymongo library (%s)", e)
            sys.exit(2)
        try:
            client = pymongo.MongoClient(
                host=self.host, port=int(self.port), username=self.user, password=self.password
            )
            client.admin.command("ping")
        except Exception as e:
            logger.critical("Cannot connect to MongoDB server %s:%s (%s)", self.host, self.port, self._redact(e))
            sys.exit(2)
        logger.info("Connected to the MongoDB server")
        return client

    def _redact(self, error: Exception) -> str:
        """The error text, with the configured credentials masked."""
        text = str(error)
        for secret in (self.password, self.user):
            if secret:
                text = text.replace(secret, "***")
        return text

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        try:
            self.client[self.db][name].insert_one(dict(zip(columns, points)))
        except Exception as e:
            logger.warning("Cannot export %s stats to MongoDB (%s)", name, self._redact(e))
        else:
            logger.debug("Export %s stats to MongoDB", name)

    def exit(self) -> None:
        # The barrier first (see the base class), then close the connection pool.
        super().exit()
        self.client.close()
