#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — RabbitMQ export module (P3-3, wave B).

Ported from the v4 module in this directory: same `[rabbitmq]` section, one
message per plugin and tick on the default exchange, routed to `queue`, whose
body is the v4 text line `hostname=<h>, name=<plugin>, dateinfo=<UTC ISO>,
<column>=<value>, ...` (numbers only). `pika` is imported when the exporter
starts, so this module stays importable without it.
"""

from __future__ import annotations

import datetime
import socket
import sys
from numbers import Number
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Send Glances stats to a RabbitMQ queue."""

    export_name = "rabbitmq"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.user: str | None = None
        self.password: str | None = None
        self.queue: str | None = None
        self.protocol: str | None = None
        if not self.load_conf(
            "rabbitmq", mandatories=("host", "port", "user", "password", "queue"), options=("protocol",)
        ):
            logger.critical("Missing rabbitmq config")
            sys.exit(2)
        # Only amqp and amqps are supported; anything else falls back to amqp (v4).
        self.protocol = "amqps" if (self.protocol or "").lower() == "amqps" else "amqp"
        self.hostname = socket.gethostname()
        self.connection: Any = None
        self.client = self.init()

    def init(self) -> Any:
        try:
            import pika
        except ImportError as e:
            logger.critical("Export rabbitmq needs the pika library (%s)", e)
            sys.exit(2)
        try:
            # The URL carries the password: it is never logged.
            parameters = pika.URLParameters(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/")
            self.connection = pika.BlockingConnection(parameters)
            channel = self.connection.channel()
        except Exception as e:
            logger.critical("Connection to the RabbitMQ server %s:%s failed (%s)", self.host, self.port, e)
            sys.exit(2)
        logger.info("Stats will be exported to the RabbitMQ server %s:%s", self.host, self.port)
        return channel

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        # Naive UTC, as v4's datetime.utcnow() (deprecated) produced: no "+00:00".
        dateinfo = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
        data = f"hostname={self.hostname}, name={name}, dateinfo={dateinfo}"
        for column, value in zip(columns, points):
            if isinstance(value, Number):
                data += f", {column}={value}"
        try:
            self.client.basic_publish(exchange="", routing_key=self.queue, body=data)
        except Exception as e:
            logger.warning("Cannot export %s stats to RabbitMQ (%s)", name, e)
        else:
            logger.debug("Export %s stats to RabbitMQ", name)

    def exit(self) -> None:
        # The barrier first (see the base class), then the connection (v4 left it open).
        super().exit()
        self.connection.close()
