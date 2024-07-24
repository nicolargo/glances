#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only

import threading
import time

from glances.logger import logger


class ThreadedIterableStreamer:
    """
    Utility class to stream an iterable using a background / daemon Thread

    Use `ThreadedIterableStreamer.stats` to access the latest streamed results
    """

    def __init__(self, iterable, initial_stream_value=None, sleep_duration=0.1):
        """
        iterable: an Iterable instance that needs to be streamed
        """
        self._iterable = iterable
        # Iterable results are stored here
        self._raw_result = initial_stream_value
        # Use a Thread to stream iterable (daemon=True to automatically kill thread when main process dies)
        self._thread = threading.Thread(target=self._stream_results, daemon=True)
        # Event needed to stop the thread manually
        self._stopper = threading.Event()
        # Lock to avoid the daemon thread updating stats when main thread reads the stats
        self.result_lock = threading.Lock()
        # Last result streamed time (initial val 0)
        self._last_update_time = 0
        # Time to sleep before next iteration
        self._sleep_duration = sleep_duration

        self._thread.start()

    def stop(self):
        """Stop the thread."""
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.is_set()

    def _stream_results(self):
        """Grab the stats.

        Infinite loop, should be stopped by calling the stop() method
        """
        try:
            for res in self._iterable:
                self._pre_update_hook()
                self._raw_result = res
                self._post_update_hook()

                time.sleep(self._sleep_duration)
                if self.stopped():
                    break

        except Exception as e:
            logger.debug(f"docker plugin - Exception thrown during run ({e})")
            self.stop()

    def _pre_update_hook(self):
        """Hook that runs before worker thread updates the raw_stats"""
        self.result_lock.acquire()

    def _post_update_hook(self):
        """Hook that runs after worker thread updates the raw_stats"""
        self._last_update_time = time.time()
        self.result_lock.release()

    @property
    def stats(self):
        """Raw Stats getter."""
        return self._raw_result

    @property
    def last_update_time(self):
        """Raw Stats getter."""
        return self._last_update_time
