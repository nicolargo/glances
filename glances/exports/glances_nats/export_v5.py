#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — NATS export module (P3-3, wave B).

Ported from the v4 module in this directory: same `[nats]` section (`host` is
a comma-separated list of servers), one message per plugin and tick on the
subject `<prefix>.<plugin>`, whose payload is the flat `{column: value}` dict
as JSON. A server unreachable at start-up is not fatal (v4). `nats-py` is
imported when the exporter starts, so this module stays importable without it.

nats-py is asyncio-only, while `update()` runs in a worker thread. As v4 did
(`GlancesExportAsyncio`), the exporter owns a private event loop running
forever in a daemon thread, and `export()` submits each publish to it with
`run_coroutine_threadsafe`, waiting for the result. The loop must keep
running BETWEEN ticks — the client's reader, pinger and reconnect tasks live
on it — which is why a loop driven only from `export()` would not do.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import re
import sys
import threading
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.globals import json_dumps
from glances.logger import logger

if TYPE_CHECKING:
    import argparse
    from collections.abc import Coroutine

    from glances.config_v5 import GlancesConfigV5

# Seconds. The flush timeout is v4's; the others bound how long a tick or
# the shutdown may wait on the loop thread.
_CONNECT_TIMEOUT = 10.0
_FLUSH_TIMEOUT = 2.0
_EXPORT_TIMEOUT = 5.0
_EXIT_TIMEOUT = 5.0


def redact(server: str) -> str:
    """Drop `user:password@` from a server URL before it is logged."""
    return re.sub(r"//[^@/]*@", "//", server)


class Export(GlancesExportBase):
    """Publish Glances stats to NATS."""

    export_name = "nats"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.prefix: str | None = None
        if not self.load_conf("nats", mandatories=("host",), options=("prefix",)):
            logger.critical("Missing nats config")
            sys.exit(2)
        self.prefix = self.prefix or "glances"
        self.servers = [s.strip() for s in self.host.split(",")]
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self.client = self.init()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run(self, coro: Coroutine[Any, Any, Any], timeout: float) -> Any:
        """Run `coro` on the private loop and wait for its result.

        On timeout the coroutine is cancelled, so it cannot complete later
        behind the exporter's back.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise

    def init(self) -> Any:
        try:
            from nats.aio.client import Client
        except ImportError as e:
            logger.critical("Export nats needs the nats-py library (%s)", e)
            sys.exit(2)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="glances-export-nats", daemon=True)
        self._thread.start()

        async def new_client() -> Any:
            # Built on the loop it will run on, as v4 did.
            return Client()

        client = self._run(new_client(), _CONNECT_TIMEOUT)
        servers = ", ".join(redact(s) for s in self.servers)
        try:
            self._run(
                client.connect(
                    servers=self.servers,
                    reconnect_time_wait=2,
                    max_reconnect_attempts=60,
                    error_cb=self._error_callback,
                    disconnected_cb=self._disconnected_callback,
                    reconnected_cb=self._reconnected_callback,
                ),
                _CONNECT_TIMEOUT,
            )
        except Exception as e:
            logger.error("Cannot connect to the NATS servers %s (%s)", servers, e)
        else:
            self._connected = True
            logger.info("Stats will be exported to the NATS servers %s", servers)
        return client

    async def _error_callback(self, e: Exception) -> None:
        logger.error("NATS error (%s)", e)

    async def _disconnected_callback(self) -> None:
        self._connected = False
        logger.debug("NATS disconnected")

    async def _reconnected_callback(self) -> None:
        self._connected = True
        logger.debug("NATS reconnected")

    async def _publish(self, subject: str, payload: bytes) -> None:
        await self.client.publish(subject, payload)
        await self.client.flush(timeout=_FLUSH_TIMEOUT)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        if not self._connected:
            logger.warning("Cannot export %s stats to NATS (not connected)", name)
            return
        subject = f"{self.prefix}.{name}"
        try:
            self._run(self._publish(subject, json_dumps(dict(zip(columns, points)))), _EXPORT_TIMEOUT)
        except Exception as e:
            logger.warning("Cannot export %s stats to NATS (%s)", name, e)
        else:
            logger.debug("Export %s stats to NATS", name)

    async def _close(self) -> None:
        # drain() flushes what is pending, then closes; close() alone stops a
        # client that is still trying to reconnect.
        if self._connected:
            await self.client.drain()
        await self.client.close()

    def exit(self) -> None:
        # The barrier first (see the base class), then the client, then the loop.
        super().exit()
        try:
            self._run(self._close(), _EXIT_TIMEOUT)
        except Exception as e:
            logger.warning("Cannot close the NATS connection (%s)", e)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=_EXIT_TIMEOUT)
        if not self._thread.is_alive():
            self._loop.close()
