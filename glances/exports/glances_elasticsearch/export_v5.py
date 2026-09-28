#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Elasticsearch export module (P3-3, wave C).

Ported from the v4 module in this directory: same `[elasticsearch]` section,
a daily index `<index>-YYYY.MM.DD` (UTC), one bulk action per plugin and
tick with `_id` `<plugin>.<timestamp>`, `_type` `glances-<plugin>`, and a
`_source` of `plugin`, `timestamp` and every field as a string. A server
that does not answer the startup ping is fatal, as in v4. `elasticsearch`
is imported when the exporter starts.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


def _utcnow() -> datetime:
    """Naive UTC now — v4's `datetime.utcnow()`, which is deprecated."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Export(GlancesExportBase):
    """Write Glances stats to an Elasticsearch server."""

    export_name = "elasticsearch"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.scheme: str | None = None
        self.index: str | None = None
        if not self.load_conf("elasticsearch", mandatories=("scheme", "host", "port", "index")):
            logger.critical("Missing elasticsearch config")
            sys.exit(2)
        self.client = self.init()

    def init(self) -> Any:
        try:
            from elasticsearch import Elasticsearch, helpers
        except ImportError as e:
            logger.critical("Export elasticsearch needs the elasticsearch library (%s)", e)
            sys.exit(2)
        self._helpers = helpers
        url = f"{self.scheme}://{self.host}:{self.port}"
        try:
            es = Elasticsearch(hosts=[url])
        except Exception as e:
            logger.critical("Cannot connect to ElasticSearch server %s (%s)", url, e)
            sys.exit(2)
        if not es.ping():
            logger.critical("Cannot ping the ElasticSearch server %s", url)
            sys.exit(2)
        logger.info("Connected to the ElasticSearch server %s", url)
        return es

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        now = _utcnow()
        dt_now = now.isoformat("T")
        action = {
            "_index": "{}-{}".format(self.index, now.strftime("%Y.%m.%d")),
            "_id": f"{name}.{dt_now}",
            "_type": f"glances-{name}",
            "_source": {"plugin": name, "timestamp": dt_now},
        }
        action["_source"].update(zip(columns, [str(p) for p in points]))
        logger.debug("Exporting the following object to elasticsearch: %s", action)
        try:
            self._helpers.bulk(self.client, [action])
        except Exception as e:
            logger.warning("Cannot export %s stats to ElasticSearch (%s)", name, e)

    def exit(self) -> None:
        # The barrier first (see the base class), then close the transport.
        super().exit()
        self.client.close()
