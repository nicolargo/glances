#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Docker Extension unit for Glances' Containers plugin."""

import time
from typing import Any, Optional

from glances.globals import iterkeys, itervalues, nativestr, pretty_date, replace_special_chars
from glances.logger import logger
from glances.stats_streamer import ThreadedIterableStreamer

# Docker-py library (optional and Linux-only)
# https://github.com/docker/docker-py
try:
    import docker
    import requests
    from dateutil import parser, tz
except Exception as e:
    disable_plugin_docker = True
    # Display debug message if import KeyError
    logger.warning(f"Error loading Docker deps Lib. Docker plugin is disabled ({e})")
else:
    disable_plugin_docker = False


class DockerStatsFetcher:
    MANDATORY_MEMORY_FIELDS = ['usage', 'limit']

    def __init__(self, container):
        self._container = container

        # Previous computes stats are stored in the self._old_computed_stats variable
        # We store time data to enable IoR/s & IoW/s calculations to avoid complexity for consumers of the APIs exposed.
        self._old_computed_stats = {}

        # Last time when output stats (results) were computed
        self._last_stats_computed_time = 0

        # Threaded Streamer
        stats_iterable = container.stats(decode=True)
        self._streamer = ThreadedIterableStreamer(stats_iterable, initial_stream_value={})

    def _log_debug(self, msg, exception=None):
        logger.debug(f"containers (Docker) ID: {self._container.id} - {msg} ({exception}) ")
        logger.debug(self._streamer.stats)

    def stop(self):
        self._streamer.stop()

    @property
    def activity_stats(self) -> dict[str, dict[str, Any]]:
        """Activity Stats

        Each successive access of activity_stats will cause computation of activity_stats
        """
        computed_activity_stats = self._compute_activity_stats()
        self._old_computed_stats = computed_activity_stats
        self._last_stats_computed_time = time.time()
        return computed_activity_stats

    def _compute_activity_stats(self) -> dict[str, dict[str, Any]]:
        with self._streamer.result_lock:
            io_stats = self._get_io_stats()
            cpu_stats = self._get_cpu_stats()
            memory_stats = self._get_memory_stats()
            network_stats = self._get_network_stats()

        return {
            "io": io_stats or {},
            "memory": memory_stats or {},
            "network": network_stats or {},
            "cpu": cpu_stats or {"total": 0.0},
        }

    @property
    def time_since_update(self) -> float:
        # In case no update, default to 1
        return max(1, self._streamer.last_update_time - self._last_stats_computed_time)

    def _get_cpu_stats(self) -> Optional[dict[str, float]]:
        """Return the container CPU usage.

        Output: a dict {'total': 1.49}
        """
        stats = {'total': 0.0}

        try:
            cpu_stats = self._streamer.stats['cpu_stats']
            precpu_stats = self._streamer.stats['precpu_stats']
            cpu = {'system': cpu_stats['system_cpu_usage'], 'total': cpu_stats['cpu_usage']['total_usage']}
            precpu = {'system': precpu_stats['system_cpu_usage'], 'total': precpu_stats['cpu_usage']['total_usage']}

            # Issue #1857
            # If either precpu_stats.online_cpus or cpu_stats.online_cpus is nil
            # then for compatibility with older daemons the length of
            # the corresponding cpu_usage.percpu_usage array should be used.
            cpu['nb_core'] = cpu_stats.get('online_cpus') or len(cpu_stats['cpu_usage']['percpu_usage'] or [])
        except KeyError as e:
            self._log_debug("Can't grab CPU stats", e)
            return None

        try:
            cpu_delta = cpu['total'] - precpu['total']
            system_cpu_delta = cpu['system'] - precpu['system']
            # CPU usage % = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
            stats['total'] = (cpu_delta / system_cpu_delta) * cpu['nb_core'] * 100.0
        except TypeError as e:
            self._log_debug("Can't compute CPU usage", e)
            return None

        # Return the stats
        return stats

    def _get_memory_stats(self) -> Optional[dict[str, float]]:
        """Return the container MEMORY.

        Output: a dict {'usage': ..., 'limit': ..., 'inactive_file': ...}

        Note:the displayed memory usage is 'usage - inactive_file'
        """
        memory_stats = self._streamer.stats.get('memory_stats')

        # Checks for memory_stats & mandatory fields
        if not memory_stats or any(field not in memory_stats for field in self.MANDATORY_MEMORY_FIELDS):
            self._log_debug("Missing MEM usage fields")
            return None

        stats = {field: memory_stats[field] for field in self.MANDATORY_MEMORY_FIELDS}

        # Optional field stats: inactive_file
        if memory_stats.get('stats', {}).get('inactive_file') is not None:
            stats['inactive_file'] = memory_stats['stats']['inactive_file']

        # Return the stats
        return stats

    def _get_network_stats(self) -> Optional[dict[str, float]]:
        """Return the container network usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'rx': 10, 'tx': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            rx: Number of bytes received
            tx: Number of bytes transmitted
        """
        eth0_stats = self._streamer.stats.get('networks', {}).get('eth0')

        # Checks for net_stats & mandatory fields
        if not eth0_stats or any(field not in eth0_stats for field in ['rx_bytes', 'tx_bytes']):
            self._log_debug("Missing Network usage fields")
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

    def _get_io_stats(self) -> Optional[dict[str, float]]:
        """Return the container IO usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'ior': 10, 'iow': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            ior: Number of bytes read
            iow: Number of bytes written
        """
        io_service_bytes_recursive = self._streamer.stats.get('blkio_stats', {}).get('io_service_bytes_recursive')

        # Checks for net_stats
        if not io_service_bytes_recursive:
            self._log_debug("Missing blockIO usage fields")
            return None

        # Read the ior/iow stats (in bytes)
        try:
            # Read IOR and IOW value in the structure list of dict
            cumulative_ior = [i for i in io_service_bytes_recursive if i['op'].lower() == 'read'][0]['value']
            cumulative_iow = [i for i in io_service_bytes_recursive if i['op'].lower() == 'write'][0]['value']
        except (TypeError, IndexError, KeyError, AttributeError) as e:
            self._log_debug("Can't grab blockIO usage", e)  # stats do not have io information
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


class DockerExtension:
    """Glances' Containers Plugin's Docker Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['running', 'paused']

    def __init__(self):
        self.disable = disable_plugin_docker
        if self.disable:
            raise Exception("Missing libs required to run Docker Extension (Containers) ")

        self.display_error = True

        self.client = None
        self.ext_name = "containers (Docker)"
        self.stats_fetchers = {}

        self.connect()

    def connect(self) -> None:
        """Connect to the Docker server."""
        # Init the Docker API Client
        try:
            # Do not use the timeout option (see issue #1878)
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"{self.ext_name} plugin - Can't connect to Docker ({e})")
            self.client = None

    def update_version(self):
        # Long and not useful anymore because the information is no more displayed in UIs
        # return self.client.version()
        return {}

    def stop(self) -> None:
        # Stop all streaming threads
        for t in itervalues(self.stats_fetchers):
            t.stop()

    def update(self, all_tag) -> tuple[dict, list[dict]]:
        """Update Docker stats using the input method."""

        if not self.client or self.disable:
            return {}, []

        version_stats = self.update_version()

        # Update current containers list
        try:
            # Issue #1152: Docker module doesn't export details about stopped containers
            # The Containers/all key of the configuration file should be set to True
            containers = self.client.containers.list(all=all_tag)
            self.display_error = True
        except Exception as e:
            if self.display_error:
                logger.error(f"{self.ext_name} plugin - Can't get containers list ({e})")
                self.display_error = False
            else:
                logger.debug(f"{self.ext_name} plugin - Can't get containers list ({e})")
            return version_stats, []

        # Start new thread for new container
        for container in containers:
            if container.id not in self.stats_fetchers:
                # StatsFetcher did not exist in the internal dict
                # Create it, add it to the internal dict
                logger.debug(f"{self.ext_name} plugin - Create thread for container {container.id[:12]}")
                self.stats_fetchers[container.id] = DockerStatsFetcher(container)

        # Stop threads for non-existing containers
        absent_containers = set(iterkeys(self.stats_fetchers)) - {c.id for c in containers}
        for container_id in absent_containers:
            # Stop the StatsFetcher
            logger.debug(f"{self.ext_name} plugin - Stop thread for old container {container_id[:12]}")
            self.stats_fetchers[container_id].stop()
            # Delete the StatsFetcher from the dict
            del self.stats_fetchers[container_id]

        # Get stats for all containers
        container_stats = [self.generate_stats(container) for container in containers]
        return version_stats, container_stats

    @property
    def key(self) -> str:
        """Return the key of the list."""
        return 'name'

    def generate_stats(self, container) -> dict[str, Any]:
        # Init the stats for the current container
        stats = {
            'key': self.key,
            'name': nativestr(container.name),
            'id': container.id,
            'status': container.attrs['State']['Status'],
            'created': container.attrs['Created'],
            'command': [],
            'io': {},
            'cpu': {},
            'memory': {},
            'network': {},
            'io_rx': None,
            'io_wx': None,
            'cpu_percent': None,
            'memory_percent': None,
            'network_rx': None,
            'network_tx': None,
            'uptime': None,
        }

        # Container Image
        try:
            # API fails on Unraid - See issue 2233
            stats['image'] = (','.join(container.image.tags if container.image.tags else []),)
        except requests.exceptions.HTTPError:
            stats['image'] = ''

        if container.attrs['Config'].get('Entrypoint', None):
            stats['command'].extend(container.attrs['Config'].get('Entrypoint', []))
        if container.attrs['Config'].get('Cmd', None):
            stats['command'].extend(container.attrs['Config'].get('Cmd', []))
        if not stats['command']:
            stats['command'] = None

        if stats['status'] not in self.CONTAINER_ACTIVE_STATUS:
            return stats

        stats_fetcher = self.stats_fetchers[container.id]
        activity_stats = stats_fetcher.activity_stats
        stats.update(activity_stats)

        # Additional fields
        stats['cpu_percent'] = stats['cpu']['total']
        stats['memory_usage'] = stats['memory'].get('usage')
        if stats['memory'].get('cache') is not None:
            stats['memory_usage'] -= stats['memory']['cache']

        if all(k in stats['io'] for k in ('ior', 'iow', 'time_since_update')):
            stats['io_rx'] = stats['io']['ior'] // stats['io']['time_since_update']
            stats['io_wx'] = stats['io']['iow'] // stats['io']['time_since_update']

        if all(k in stats['network'] for k in ('rx', 'tx', 'time_since_update')):
            stats['network_rx'] = stats['network']['rx'] // stats['network']['time_since_update']
            stats['network_tx'] = stats['network']['tx'] // stats['network']['time_since_update']

        started_at = container.attrs['State']['StartedAt']
        stats['uptime'] = pretty_date(parser.parse(started_at).astimezone(tz.tzlocal()).replace(tzinfo=None))

        # Manage special chars in command (see issue#2733)
        stats['command'] = replace_special_chars(' '.join(stats['command']))

        return stats
