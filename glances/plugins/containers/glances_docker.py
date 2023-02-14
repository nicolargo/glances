"""Docker Extension unit for Glances' Containers plugin."""
import threading
import time

from glances.compat import iterkeys, itervalues, nativestr, pretty_date
from glances.logger import logger
from glances.plugins.containers.stats_fetcher import StatsFetcher

# Docker-py library (optional and Linux-only)
# https://github.com/docker/docker-py
try:
    import docker
    from dateutil import parser, tz
except Exception as e:
    import_docker_error_tag = True
    # Display debug message if import KeyError
    logger.debug("Error loading Docker deps Lib. Docker plugin is disabled ({})".format(e))
else:
    import_docker_error_tag = False


class DockerStatsFetcher(StatsFetcher):
    MANDATORY_MEMORY_FIELDS = ["usage", 'limit']

    def __init__(self, container):
        super().__init__(container)
        # Lock to avoid the daemon thread updating stats when main thread reads the stats
        self._stats_lock = threading.Lock()

        # Previous computes stats are stored in the self._old_computed_stats variable
        # By storing time data we enable IoR/s and IoW/s calculations in the XML/RPC API, which would otherwise
        # be overly difficult work for users of the API
        self._old_computed_stats = {}

        # Last time when output stats (results) were computed
        self._last_stats_output_time = 0
        # Last time when the raw_stats were updated by worker thread
        self._last_raws_stats_update_time = 1

    @property
    def activity_stats(self):
        """Activity Stats

        Each successive access of activity_stats will cause computation of activity_stats from raw_stats
        """
        computed_activity_stats = self._compute_activity_stats()
        self._old_computed_stats = computed_activity_stats
        self._last_stats_output_time = time.time()
        return computed_activity_stats

    def _pre_raw_stats_update_hook(self):
        self._stats_lock.acquire()

    def _post_raw_stats_update_hook(self):
        self._last_raws_stats_update_time = time.time()
        self._stats_lock.release()

    @property
    def time_since_update(self):
        return self._last_raws_stats_update_time - self._last_stats_output_time

    def _compute_activity_stats(self):
        with self._stats_lock:
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
        stats = {'total': 0.0}

        try:
            cpu_stats = self.stats['cpu_stats']
            precpu_stats = self.stats['precpu_stats']
            cpu = {'system': cpu_stats['system_cpu_usage'], 'total': cpu_stats['cpu_usage']['total_usage']}
            precpu = {'system': precpu_stats['system_cpu_usage'], 'total': precpu_stats['cpu_usage']['total_usage']}

            # Issue #1857
            # If either precpu_stats.online_cpus or cpu_stats.online_cpus is nil
            # then for compatibility with older daemons the length of
            # the corresponding cpu_usage.percpu_usage array should be used.
            cpu['nb_core'] = cpu_stats.get('online_cpus') or len(cpu_stats['cpu_usage']['percpu_usage'] or [])
        except KeyError as e:
            logger.debug("containers plugin - Can't grab CPU stat for container {} ({})".format(self._container.id, e))
            logger.debug(self.stats)
            return None

        try:
            cpu_delta = cpu['total'] - precpu['total']
            system_cpu_delta = cpu['system'] - precpu['system']
            # CPU usage % = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
            stats['total'] = (cpu_delta / system_cpu_delta) * cpu['nb_core'] * 100.0
        except TypeError as e:
            msg = "containers plugin - Can't compute CPU usage for container {} ({})".format(self._container.id, e)
            logger.debug(msg)
            logger.debug(self.stats)
            return None

        # Return the stats
        return stats

    def _get_memory_stats(self):
        """Return the container MEMORY.

        Output: a dict {'rss': 1015808, 'cache': 356352,  'usage': ..., 'max_usage': ...}
        """
        memory_stats = self.stats.get('memory_stats')

        # Checks for memory_stats & mandatory fields
        if not memory_stats or any(field not in memory_stats for field in self.MANDATORY_MEMORY_FIELDS):
            logger.debug("containers plugin - Missing MEM usage fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        stats = {field: memory_stats[field] for field in self.MANDATORY_MEMORY_FIELDS}
        try:
            # Issue #1857 - Some stats are not always available in ['memory_stats']['stats']
            detailed_stats = memory_stats['stats']
            stats['rss'] = detailed_stats.get('rss') or detailed_stats.get('total_rss')
            stats['max_usage'] = detailed_stats.get('max_usage')
            stats['cache'] = detailed_stats.get('cache')
        except (KeyError, TypeError) as e:
            # self.stats do not have MEM information
            logger.debug("containers plugin - Can't grab MEM usage for container {} ({})".format(self._container.id, e))
            logger.debug(self.stats)
            return None

        # Return the stats
        return stats

    def _get_network_stats(self):
        """Return the container network usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'rx': 10, 'tx': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            rx: Number of bytes received
            tx: Number of bytes transmitted
        """
        eth0_stats = self.stats.get('networks', {}).get('eth0')

        # Checks for net_stats & mandatory fields
        if not eth0_stats or any(field not in eth0_stats for field in ['rx_bytes', 'tx_bytes']):
            logger.debug("containers plugin - Missing Network usage fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        # Read the rx/tx stats (in bytes)
        stats = {'cumulative_rx': eth0_stats["rx_bytes"], 'cumulative_tx': eth0_stats["tx_bytes"]}

        # Using previous stats to calculate rates
        old_network_stats = self._old_computed_stats.get("network")
        if old_network_stats:
            stats['time_since_update'] = round(self.time_since_update)
            stats['rx'] = stats['cumulative_rx'] - old_network_stats["cumulative_rx"]
            stats['tx'] = stats['cumulative_tx'] - old_network_stats['cumulative_tx']

        # Return the stats
        return stats

    def _get_io_stats(self):
        """Return the container IO usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'ior': 10, 'iow': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            ior: Number of bytes read
            iow: Number of bytes written
        """
        io_service_bytes_recursive = self.stats.get('blkio_stats', {}).get('io_service_bytes_recursive')

        # Checks for net_stats
        if not io_service_bytes_recursive:
            logger.debug("containers plugin - Missing blockIO usage fields for container {}".format(self._container.id))
            logger.debug(self.stats)
            return None

        # Read the ior/iow stats (in bytes)
        try:
            # Read IOR and IOW value in the structure list of dict
            cumulative_ior = [i for i in io_service_bytes_recursive if i['op'].lower() == 'read'][0]['value']
            cumulative_iow = [i for i in io_service_bytes_recursive if i['op'].lower() == 'write'][0]['value']
        except (TypeError, IndexError, KeyError, AttributeError) as e:
            # self.stats do not have io information
            logger.debug(
                "containers plugin - Can't grab blockIO usage for container {} ({})".format(self._container.id, e)
            )
            logger.debug(self.stats)
            return None

        stats = {'cumulative_ior': cumulative_ior, 'cumulative_iow': cumulative_iow}

        # Using previous stats to calculate difference
        old_io_stats = self._old_computed_stats.get("io")
        if old_io_stats:
            stats['time_since_update'] = round(self.time_since_update)
            stats['ior'] = stats['cumulative_ior'] - old_io_stats["cumulative_ior"]
            stats['iow'] = stats['cumulative_iow'] - old_io_stats["cumulative_iow"]

        # Return the stats
        return stats


class DockerContainersExtension:
    """Glances' Containers Plugin's Docker Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['running', 'paused']

    def __init__(self):
        if import_docker_error_tag:
            raise Exception("Missing libs required to run Docker Extension (Containers) ")

        self.client = None
        self.ext_name = "Docker Ext"
        self.stats_fetchers = {}
        self.connect()

    def connect(self):
        """Connect to the Docker server."""
        # Init the Docker API Client
        try:
            # Do not use the timeout option (see issue #1878)
            self.client = docker.from_env()
        except Exception as e:
            logger.error("docker plugin - Can not connect to Docker ({})".format(e))
            self.client = None

    def stop(self):
        # Stop all streaming threads
        for t in itervalues(self.stats_fetchers):
            t.stop()

    def update(self, all_tag):
        """Update Docker stats using the input method."""
        # Docker version
        # Example: {
        #     "KernelVersion": "3.16.4-tinycore64",
        #     "Arch": "amd64",
        #     "ApiVersion": "1.15",
        #     "Version": "1.3.0",
        #     "GitCommit": "c78088f",
        #     "Os": "linux",
        #     "GoVersion": "go1.3.3"
        # }
        try:
            version_stats = self.client.version()
        except Exception as e:
            # Correct issue#649
            logger.error("{} plugin - Cannot get Docker version ({})".format(self.ext_name, e))
            return {}, []

        # Update current containers list
        try:
            # Issue #1152: Docker module doesn't export details about stopped containers
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
                self.stats_fetchers[container.id] = DockerStatsFetcher(container)

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
            'Status': container.attrs['State']['Status'],
            'Created': container.attrs['Created'],
            'Command': [],
        }

        if container.attrs['Config'].get('Entrypoint', None):
            stats['Command'].extend(container.attrs['Config'].get('Entrypoint', []))
        if container.attrs['Config'].get('Cmd', None):
            stats['Command'].extend(container.attrs['Config'].get('Cmd', []))
        if not stats['Command']:
            stats['Command'] = None

        if stats['Status'] in self.CONTAINER_ACTIVE_STATUS:
            stats['StartedAt'] = container.attrs['State']['StartedAt']
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
            stats['Uptime'] = pretty_date(
                parser.parse(stats['StartedAt']).astimezone(tz.tzlocal()).replace(tzinfo=None)
            )
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
