#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
I am your son...
...abstract class for AsyncIO-based Glances exports.
"""

import asyncio
import threading
import time
from abc import abstractmethod

from glances.exports.export import GlancesExport
from glances.logger import logger


class GlancesExportAsyncio(GlancesExport):
    """Abstract class for AsyncIO-based export modules.

    This class manages a persistent event loop in a background thread,
    allowing child classes to use AsyncIO operations for exporting data.

    Child classes must implement:
    - async _async_init(): AsyncIO initialization (e.g., connection setup)
    - async _async_exit(): AsyncIO cleanup (e.g., disconnection)
    - async _async_export(name, columns, points): AsyncIO export operation
    """

    def __init__(self, config=None, args=None):
        """Init the AsyncIO export interface."""
        super().__init__(config=config, args=args)

        # AsyncIO event loop management
        self.loop = None
        self._loop_ready = threading.Event()
        self._loop_exception = None
        self._shutdown = False

        # Start the background event loop thread
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()

        # Wait for the loop to be ready
        if not self._loop_ready.wait(timeout=10):
            raise RuntimeError("AsyncIO event loop failed to start within timeout")

        if self._loop_exception:
            raise RuntimeError(f"AsyncIO event loop creation failed: {self._loop_exception}")

        if self.loop is None:
            raise RuntimeError("AsyncIO event loop is None after initialization")

        # Call child class AsyncIO initialization
        future = asyncio.run_coroutine_threadsafe(self._async_init(), self.loop)
        try:
            future.result(timeout=10)
            logger.debug(f"{self.export_name} AsyncIO export initialized successfully")
        except Exception as e:
            logger.warning(f"{self.export_name} AsyncIO initialization failed: {e}. Will retry in background.")

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
            logger.error(f"{self.export_name} AsyncIO event loop thread error: {e}")
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    @abstractmethod
    async def _async_init(self):
        """AsyncIO initialization method.

        Child classes should implement this method to perform AsyncIO-based
        initialization such as connecting to servers, setting up clients, etc.

        This method is called once during __init__ after the event loop is ready.
        """
        pass

    @abstractmethod
    async def _async_exit(self):
        """AsyncIO cleanup method.

        Child classes should implement this method to perform AsyncIO-based
        cleanup such as disconnecting from servers, closing clients, etc.

        This method is called during exit() before stopping the event loop.
        """
        pass

    @abstractmethod
    async def _async_export(self, name, columns, points):
        """AsyncIO export method.

        Child classes must implement this method to perform the actual
        export operation using AsyncIO.

        :param name: plugin name
        :param columns: list of column names
        :param points: list of values corresponding to columns
        """
        pass

    def exit(self):
        """Close the AsyncIO export module."""
        super().exit()
        self._shutdown = True
        logger.info(f"{self.export_name} AsyncIO export shutting down")

        # Call child class cleanup
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(self._async_exit(), self.loop)
            try:
                future.result(timeout=5)
            except Exception as e:
                logger.error(f"{self.export_name} Error in AsyncIO cleanup: {e}")

        # Stop the event loop
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            time.sleep(0.5)

        logger.debug(f"{self.export_name} AsyncIO export shutdown complete")

    def export(self, name, columns, points):
        """Export data using AsyncIO.

        This method bridges the synchronous export() interface with
        the AsyncIO _async_export() implementation.
        """
        if self._shutdown:
            logger.debug(f"{self.export_name} Export called during shutdown, skipping")
            return

        if not self.loop or not self.loop.is_running():
            logger.error(f"{self.export_name} AsyncIO event loop is not running")
            return

        # Submit the export operation to the background event loop
        try:
            future = asyncio.run_coroutine_threadsafe(self._async_export(name, columns, points), self.loop)
            # Don't block forever - use a short timeout
            future.result(timeout=1)
        except asyncio.TimeoutError:
            logger.warning(f"{self.export_name} AsyncIO export timeout for {name}")
        except Exception as e:
            logger.error(f"{self.export_name} AsyncIO export error for {name}: {e}", exc_info=True)
