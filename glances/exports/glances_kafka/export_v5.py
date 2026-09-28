#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Kafka export module (P3-3, wave B).

Ported from the v4 module in this directory: same `[kafka]` section, one
message per plugin and tick on `topic`, keyed by the plugin name (bytes,
#1593), whose value is the flat `{column: value}` dict as JSON, with the
optional `tags` merged in. `kafka-python` is imported when the exporter
starts, so this module stays importable without it.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.globals import json_dumps
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Send Glances stats to a Kafka topic."""

    export_name = "kafka"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.topic: str | None = None
        self.compression: str | None = None
        self.tags: str | None = None
        if not self.load_conf("kafka", mandatories=("host", "port", "topic"), options=("compression", "tags")):
            logger.critical("Missing kafka config")
            sys.exit(2)
        # Parsed once: the tags do not change between messages.
        self._tags = self.parse_tags(self.tags)
        self.client = self.init()

    def init(self) -> Any:
        try:
            from kafka import KafkaProducer
        except ImportError as e:
            logger.critical("Export kafka needs the kafka-python library (%s)", e)
            sys.exit(2)
        server_uri = f"{self.host}:{self.port}"
        try:
            client = KafkaProducer(
                bootstrap_servers=server_uri,
                value_serializer=json_dumps,
                compression_type=self.compression,
            )
        except Exception as e:
            logger.critical("Cannot connect to the Kafka server %s (%s)", server_uri, e)
            sys.exit(2)
        logger.info("Stats will be exported to the Kafka server %s", server_uri)
        return client

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        data = dict(zip(columns, points))
        data.update(self._tags)
        try:
            self.client.send(self.topic, key=name.encode("utf-8"), value=data)
        except Exception as e:
            logger.warning("Cannot export %s stats to Kafka (%s)", name, e)
        else:
            logger.debug("Export %s stats to Kafka", name)

    def exit(self) -> None:
        # The barrier first (see the base class), then drain the producer's buffer.
        super().exit()
        self.client.flush()
        self.client.close()
