"""Podman Extension unit for Glances' Containers plugin."""
from datetime import datetime

from glances.compat import iterkeys, itervalues, nativestr, pretty_date
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
    MANDATORY_FIELDS = ["CPU", "MemUsage", "MemLimit", "NetInput", "NetOutput", "BlockInput", "BlockOutput"]

    @property
    def stats(self):
        if self._raw_stats["Error"]:
            logger.error("containers plugin - Stats fetching failed: {}".format(self._raw_stats["Error"]))
            logger.error(self._raw_stats)

        return self._raw_stats["Stats"][0]

    @property
    def activity_stats(self):
        result_stats = {"cpu": {}, "memory": {}, "io": {}, "network": {}}

        if any(field not in self.stats for field in self.MANDATORY_FIELDS):
            logger.debug("containers plugin - Missing mandatory fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return result_stats

        try:
            cpu_usage = float(self.stats.get("CPU", 0))

            mem_usage = float(self.stats["MemUsage"])
            mem_limit = float(self.stats["MemLimit"])

            rx = float(self.stats["NetInput"])
            tx = float(self.stats["NetOutput"])

            ior = float(self.stats["BlockInput"])
            iow = float(self.stats["BlockOutput"])

            # Hardcode `time_since_update` to 1 as podman already sends the calculated rate
            result_stats = {
                "cpu": {"total": cpu_usage},
                "memory": {"usage": mem_usage, "limit": mem_limit},
                "io": {"ior": ior, "iow": iow, "time_since_update": 1},
                "network": {"rx": rx, "tx": tx, "time_since_update": 1},
            }
        except ValueError:
            logger.debug("containers plugin - Non float stats values found for container {}".format(self._container.id))
            logger.debug(self.stats)
            return result_stats

        return result_stats


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
