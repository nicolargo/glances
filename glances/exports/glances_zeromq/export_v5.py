#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — ZeroMQ export module (P3-3, wave B).

Ported from the v4 module in this directory: same `[zeromq]` section, a PUB
socket bound on `tcp://<host>:<port>`, one three-frame message per plugin
and tick — `prefix`, plugin name, the flat `{column: value}` dict as JSON.
`pyzmq` is imported when the exporter starts, so this module stays
importable without it.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.globals import b, json_dumps
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Publish Glances stats on a ZeroMQ PUB socket."""

    export_name = "zeromq"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.prefix: str | None = None
        if not self.load_conf("zeromq", mandatories=("host", "port", "prefix")):
            logger.critical("Missing zeromq config")
            sys.exit(2)
        self.context: Any = None
        self.client = self.init()

    def init(self) -> Any:
        try:
            import zmq
        except ImportError as e:
            logger.critical("Export zeromq needs the pyzmq library (%s)", e)
            sys.exit(2)
        server_uri = f"tcp://{self.host}:{self.port}"
        try:
            self.context = zmq.Context()
            publisher = self.context.socket(zmq.PUB)
            publisher.bind(server_uri)
        except Exception as e:
            logger.critical("Cannot bind the ZeroMQ socket %s (%s)", server_uri, e)
            sys.exit(2)
        logger.info("Stats will be published on the ZeroMQ socket %s", server_uri)
        return publisher

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        data = dict(zip(columns, points))
        if not data:
            return
        message = [b(self.prefix), b(name), json_dumps(data)]
        try:
            self.client.send_multipart(message)
        except Exception as e:
            logger.warning("Cannot export %s stats to ZeroMQ (%s)", name, e)
        else:
            logger.debug("Export %s stats to ZeroMQ", name)

    def exit(self) -> None:
        # The barrier first (see the base class), then the socket and its context.
        super().exit()
        self.client.close()
        self.context.destroy()
