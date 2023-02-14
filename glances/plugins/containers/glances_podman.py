"""Podman Extension unit for Glances' Containers plugin."""
from datetime import datetime

from glances.compat import iterkeys, itervalues, nativestr, pretty_date, string_value_to_float
from glances.logger import logger
from glances.plugins.containers.stats_fetcher import StatsFetcher

# Podman library (optional and Linux-only)
# https://pypi.org/project/podman/
try:
    import podman
except Exception as e:
    import_podman_error_tag = True
    # Display debug message if import KeyError
    logger.debug("Error loading Podman deps Lib. Podman feature in the Containers plugin is disabled ({})".format(e))
else:
    import_podman_error_tag = False


class PodmanStatsFetcher(StatsFetcher):
    @property
    def activity_stats(self):
        io_stats = self._get_io_stats()
        cpu_stats = self._get_cpu_stats()
        memory_stats = self._get_memory_stats()
        network_stats = self._get_network_stats()

        computed_stats = {
            "io": io_stats or {},
            "memory": memory_stats or {},
            "network": network_stats or {},
            "cpu": cpu_stats or {"total": 0.0},
        }
        return computed_stats

    def _get_cpu_stats(self):
        """Return the container CPU usage.

        Output: a dict {'total': 1.49}
        """
        if "cpu_percent" not in self.stats:
            logger.debug("containers plugin - Missing CPU usage fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        cpu_usage = string_value_to_float(self.stats["cpu_percent"].rstrip("%"))
        return {"total": cpu_usage}

    def _get_memory_stats(self):
        """Return the container MEMORY.

        Output: a dict {'rss': 1015808, 'cache': 356352,  'usage': ..., 'max_usage': ...}
        """
        if "mem_usage" not in self.stats or "/" not in self.stats["mem_usage"]:
            logger.debug("containers plugin - Missing MEM usage fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        memory_usage_str = self.stats["mem_usage"]
        usage_str, limit_str = memory_usage_str.split("/")

        try:
            usage = string_value_to_float(usage_str)
            limit = string_value_to_float(limit_str)
        except ValueError as e:
            logger.debug("containers plugin - Compute MEM usage failed for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        return {"usage": usage, "limit": limit}

    def _get_network_stats(self):
        """Return the container network usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'rx': 10, 'tx': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            rx: Number of bytes received
            tx: Number of bytes transmitted
        """
        if "net_io" not in self.stats or "/" not in self.stats["net_io"]:
            logger.debug("containers plugin - Missing Network usage fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        net_io_str = self.stats["net_io"]
        rx_str, tx_str = net_io_str.split("/")

        try:
            rx = string_value_to_float(rx_str)
            tx = string_value_to_float(tx_str)
        except ValueError as e:
            logger.debug("containers plugin - Compute Network usage failed for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        # Hardcode `time_since_update` to 1 as podman docs don't specify the rate calculated procedure
        return {"rx": rx, "tx": tx, "time_since_update": 1}

    def _get_io_stats(self):
        """Return the container IO usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'ior': 10, 'iow': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            ior: Number of bytes read
            iow: Number of bytes written
        """
        if "block_io" not in self.stats or "/" not in self.stats["block_io"]:
            logger.debug("containers plugin - Missing BlockIO usage fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        block_io_str = self.stats["block_io"]
        ior_str, iow_str = block_io_str.split("/")

        try:
            ior = string_value_to_float(ior_str)
            iow = string_value_to_float(iow_str)
        except ValueError as e:
            logger.debug("containers plugin - Compute BlockIO usage failed for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        # Hardcode `time_since_update` to 1 as podman docs don't specify the rate calculated procedure
        return {"ior": ior, "iow": iow, "time_since_update": 1}


class PodmanContainersExtension:
    """Glances' Containers Plugin's Docker Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['running', 'paused']

    def __init__(self, podman_sock):
        if import_podman_error_tag:
            raise Exception("Missing libs required to run Podman Extension (Containers)")

        self.client = None
        self.ext_name = "Podman (Containers)"
        self.podman_sock = podman_sock
        self.stats_fetchers = {}
        self._version = {}
        self.connect()

    def connect(self):
        """Connect to Podman."""
        try:
            self.client = podman.PodmanClient(base_url=self.podman_sock)
        except Exception as e:
            logger.error("{} plugin - Can not connect to Podman ({})".format(self.ext_name, e))

        try:
            version_podman = self.client.version()
        except Exception as e:
            logger.error("{} plugin - Cannot get Podman version ({})".format(self.ext_name, e))
        else:
            self._version = {
                'Version': version_podman['Version'],
                'ApiVersion': version_podman['ApiVersion'],
                'MinAPIVersion': version_podman['MinAPIVersion'],
            }

    def stop(self):
        # Stop all streaming threads
        for t in itervalues(self.stats_fetchers):
            t.stop()

    def update(self, all_tag):
        """Update Podman stats using the input method."""

        try:
            version_stats = self.client.version()
        except Exception as e:
            # Correct issue#649
            logger.error("{} plugin - Cannot get Podman version ({})".format(self.ext_name, e))
            return {}, []

        # Update current containers list
        try:
            # Issue #1152: Podman module doesn't export details about stopped containers
            # The Containers/all key of the configuration file should be set to True
            containers = self.client.containers.list(all=all_tag)
        except Exception as e:
            logger.error("{} plugin - Cannot get containers list ({})".format(self.ext_name, e))
            return version_stats, []

        # Start new thread for new container
        for container in containers:
            if container.id not in self.stats_fetchers:
                # StatsFetcher did not exist in the internal dict
                # Create it, add it to the internal dict
                logger.debug("{} plugin - Create thread for container {}".format(self.ext_name, container.id[:12]))
                self.stats_fetchers[container.id] = PodmanStatsFetcher(container)

        # Stop threads for non-existing containers
        absent_containers = set(iterkeys(self.stats_fetchers)) - set(c.id for c in containers)
        for container_id in absent_containers:
            # Stop the StatsFetcher
            logger.debug("{} plugin - Stop thread for old container {}".format(self.ext_name, container_id[:12]))
            self.stats_fetchers[container_id].stop()
            # Delete the StatsFetcher from the dict
            del self.stats_fetchers[container_id]

        # Get stats for all containers
        container_stats = [self.generate_stats(container) for container in containers]
        return version_stats, container_stats

    @property
    def key(self):
        """Return the key of the list."""
        return 'name'

    def generate_stats(self, container):
        # Init the stats for the current container
        stats = {
            'key': self.key,
            # Export name
            'name': nativestr(container.name),
            # Container Id
            'Id': container.id,
            # Container Image
            'Image': str(container.image.tags),
            # Container Status (from attrs)
            'Status': container.attrs['State'],
            'Created': container.attrs['Created'],
            'Command': container.attrs.get('Command') or [],
        }

        if stats['Status'] in self.CONTAINER_ACTIVE_STATUS:
            stats['StartedAt'] = datetime.fromtimestamp(container.attrs['StartedAt'])
            stats_fetcher = self.stats_fetchers[container.id]
            activity_stats = stats_fetcher.activity_stats
            stats.update(activity_stats)

            # Additional fields
            stats['cpu_percent'] = stats["cpu"]['total']
            stats['memory_usage'] = stats["memory"].get('usage')
            if stats['memory'].get('cache') is not None:
                stats['memory_usage'] -= stats['memory']['cache']
            stats['io_r'] = stats['io'].get('ior')
            stats['io_w'] = stats['io'].get('iow')
            stats['network_rx'] = stats['network'].get('rx')
            stats['network_tx'] = stats['network'].get('tx')
            stats['Uptime'] = pretty_date(stats['StartedAt'])
        else:
            stats['io'] = {}
            stats['cpu'] = {}
            stats['memory'] = {}
            stats['network'] = {}
            stats['io_r'] = None
            stats['io_w'] = None
            stats['cpu_percent'] = None
            stats['memory_percent'] = None
            stats['network_rx'] = None
            stats['network_tx'] = None
            stats['Uptime'] = None

        return stats
