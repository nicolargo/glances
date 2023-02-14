import threading
import time

from glances.logger import logger


class StatsFetcher:
    # Should be an Abstract Base Class
    # Inherit from abc.ABC by Glancesv4 (not inheriting for compatibility with py2)
    """
    Streams the container stats through threading

    Use `StatsFetcher.stats` to access the streamed results
    """

    def __init__(self, container):
        """Init the class.

        container: instance of Container returned by Docker or Podman client
        """
        # The docker-py return stats as a stream
        self._container = container
        # Container stats are maintained as dicts
        self._raw_stats = {}
        # Use a Thread to stream stats
        self._thread = threading.Thread(target=self._fetch_stats, daemon=True)
        # Event needed to stop properly the thread
        self._stopper = threading.Event()

        self._thread.start()
        logger.debug("docker plugin - Create thread for container {}".format(self._container.name))

    def _fetch_stats(self):
        """Grab the stats.

        Infinite loop, should be stopped by calling the stop() method
        """
        try:
            for new_stats in self._container.stats(decode=True):
                self._pre_raw_stats_update_hook()
                self._raw_stats = new_stats
                self._post_raw_stats_update_hook()

                time.sleep(0.1)
                if self.stopped():
                    break

        except Exception as e:
            logger.debug("docker plugin - Exception thrown during run ({})".format(e))
            self.stop()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.is_set()

    def stop(self, timeout=None):
        """Stop the thread."""
        logger.debug("docker plugin - Close thread for container {}".format(self._container.name))
        self._stopper.set()

    @property
    def stats(self):
        """Raw Stats getter."""
        return self._raw_stats

    def _pre_raw_stats_update_hook(self):
        """Hook that runs before worker thread updates the raw_stats"""
        pass

    def _post_raw_stats_update_hook(self):
        """Hook that runs after worker thread updates the raw_stats"""
        pass
