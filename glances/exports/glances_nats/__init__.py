#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""NATS interface class."""

from nats.aio.client import Client as NATS
from nats.errors import ConnectionClosedError
from nats.errors import TimeoutError as NatsTimeoutError

from glances.exports.export_asyncio import GlancesExportAsyncio
from glances.globals import json_dumps
from glances.logger import logger


class Export(GlancesExportAsyncio):
    """This class manages the NATS export module."""

    def __init__(self, config=None, args=None):
        """Init the NATS export IF."""
        # Load the NATS configuration file before calling super().__init__
        # because super().__init__ will call _async_init() which needs config
        self.config = config
        self.args = args
        self.export_name = self.__class__.__module__

        export_enable = self.load_conf(
            'nats',
            mandatories=['host'],
            options=['prefix'],
        )
        if not export_enable:
            exit('Missing NATS config')

        self.prefix = self.prefix or 'glances'
        # Host is a comma-separated list of NATS servers
        self.hosts = self.host

        # NATS-specific attributes
        self.client = None
        self._connected = False
        self._publish_count = 0

        # Call parent __init__ which will start event loop and call _async_init()
        super().__init__(config=config, args=args)

        # Restore export_enable after super().__init__() resets it to False
        self.export_enable = export_enable

    async def _async_init(self):
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
            logger.info(f"NATS Successfully connected to servers: {self.hosts}")
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

    async def _async_exit(self):
        """Disconnect from NATS."""
        try:
            if self.client and self._connected:
                await self.client.drain()
                await self.client.close()
                self._connected = False
                logger.debug(f"NATS disconnected cleanly. Total messages published: {self._publish_count}")
        except Exception as e:
            logger.error(f"NATS Error in disconnect: {e}")

    async def _async_export(self, name, columns, points):
        """Write the points to NATS using AsyncIO."""
        if not self._connected:
            logger.warning("NATS not connected, skipping export")
            return

        subject_name = f"{self.prefix}.{name}"
        subject_data = dict(zip(columns, points))

        # Publish data to NATS
        try:
            if not self._connected:
                raise ConnectionClosedError("NATS Not connected to server")
            await self.client.publish(subject_name, json_dumps(subject_data))
            await self.client.flush(timeout=2.0)
            self._publish_count += 1
        except (ConnectionClosedError, NatsTimeoutError) as e:
            self._connected = False
            logger.error(f"NATS publish failed for {subject_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"NATS Unexpected error publishing {subject_name}: {e}", exc_info=True)
            raise


# End of glances/exports/glances_nats/__init__.py
