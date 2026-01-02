#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""NATS interface class."""

import asyncio
import threading
import time

from nats.aio.client import Client as NATS
from nats.errors import ConnectionClosedError
from nats.errors import TimeoutError as NatsTimeoutError

from glances.exports.export import GlancesExport
from glances.globals import json_dumps
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the NATS export module."""

    def __init__(self, config=None, args=None):
        """Init the NATS export IF."""
        super().__init__(config=config, args=args)

        # Load the NATS configuration file
        self.export_enable = self.load_conf(
            'nats',
            mandatories=['host'],
            options=['prefix'],
        )
        if not self.export_enable:
            exit('Missing NATS config')

        self.prefix = self.prefix or 'glances'
        # Host is a comma-separated list of NATS servers
        self.hosts = self.host

        # Create a persistent event loop in a background thread
        self.loop = None
        self.client = None
        self._connected = False
        self._shutdown = False
        self._loop_ready = threading.Event()
        self._loop_exception = None
        self._publish_count = 0

        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()

        # Wait for the loop to be ready
        if not self._loop_ready.wait(timeout=10):
            exit("NATS event loop failed to start within timeout")

        if self._loop_exception:
            exit(f"NATS event loop creation failed: {self._loop_exception}")

        if self.loop is None:
            exit("NATS event loop is None after initialization")

        # Initial connection attempt
        future = asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
        try:
            future.result(timeout=10)
            logger.info("NATS export initialized successfully")
        except Exception as e:
            logger.warning(f"NATS Initial connection failed: {e}. Will retry in background.")

    def _run_event_loop(self):
        """Run event loop in background thread."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self._loop_ready.set()
            self.loop.run_forever()
        except Exception as e:
            self._loop_exception = e
            self._loop_ready.set()
            logger.error(f"NATS Export Event loop thread error: {e}")
        finally:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    async def _connect(self):
        """Connect to NATS with error handling."""
        try:
            if self.client:
                try:
                    await self.client.close()
                except Exception as e:
                    logger.debug(f"NATS Error closing existing client: {e}")

            self.client = NATS()

            logger.debug(f"NATS Connecting to servers: {self.hosts}")

            # Configure with reconnection callbacks
            await self.client.connect(
                servers=[s.strip() for s in self.hosts.split(',')],
                reconnect_time_wait=2,
                max_reconnect_attempts=60,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback,
            )

            self._connected = True
            logger.debug(f"NATS Successfully connected to servers: {self.hosts}")
        except Exception as e:
            self._connected = False
            logger.error(f"NATS connection error: {e}")
            raise

    async def _error_callback(self, e):
        """Called when NATS client encounters an error."""
        logger.error(f"NATS error callback: {e}")

    async def _disconnected_callback(self):
        """Called when disconnected from NATS."""
        self._connected = False
        logger.debug("NATS disconnected callback")

    async def _reconnected_callback(self):
        """Called when reconnected to NATS."""
        self._connected = True
        logger.debug("NATS reconnected callback")

    def exit(self):
        """Close the NATS connection."""
        super().exit()
        self._shutdown = True
        logger.info("NATS export shutting down")

        if self.loop and self.client:
            future = asyncio.run_coroutine_threadsafe(self._disconnect(), self.loop)
            try:
                future.result(timeout=5)
            except Exception as e:
                logger.error(f"NATS Error disconnecting from server: {e}")

        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            time.sleep(0.5)

        logger.debug(f"NATS export shutdown complete. Total messages published: {self._publish_count}")

    async def _disconnect(self):
        """Disconnect from NATS."""
        try:
            if self.client and self._connected:
                await self.client.drain()
                await self.client.close()
                self._connected = False
                logger.debug("NATS disconnected cleanly")
        except Exception as e:
            logger.error(f"NATS Error in disconnect: {e}")

    def export(self, name, columns, points):
        """Write the points in NATS."""
        if self._shutdown:
            logger.debug("NATS Export called during shutdown, skipping")
            return

        if not self.loop or not self.loop.is_running():
            logger.error("NATS event loop is not running")
            return

        if not self._connected:
            logger.warning("NATS not connected, skipping export")
            return

        subject_name = f"{self.prefix}.{name}"
        subject_data = dict(zip(columns, points))

        # Submit the publish operation to the background event loop
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._publish(subject_name, json_dumps(subject_data)),
                self.loop
            )
            # Don't block forever - use a short timeout
            future.result(timeout=1)
            self._publish_count += 1
        except asyncio.TimeoutError:
            logger.warning(f"NATS publish timeout for {subject_name}")
        except Exception as e:
            logger.error(f"NATS publish error for {subject_name}: {e}", exc_info=True)

    async def _publish(self, subject, data):
        """Publish data to NATS."""
        try:
            if not self._connected:
                raise ConnectionClosedError("NATS Not connected to server")
            await self.client.publish(subject, data)
            await asyncio.wait_for(self.client.flush(), timeout=2.0)
        except (ConnectionClosedError, NatsTimeoutError) as e:
            self._connected = False
            logger.error(f"NATS publish failed: {e}")
            raise
        except Exception as e:
            logger.error(f"NATS Unexpected error in _publish: {e}", exc_info=True)
            raise

# End of glances/exports/glances_nats/__init__.py
