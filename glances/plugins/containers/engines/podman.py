# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only

"""Podman Extension unit for Glances' Containers plugin."""
from datetime import datetime

from glances.globals import iterkeys, itervalues, nativestr, pretty_date, string_value_to_float
from glances.logger import logger
from glances.plugins.containers.stats_streamer import StatsStreamer

# Podman library (optional and Linux-only)
# https://pypi.org/project/podman/
try:
    from podman import PodmanClient
except Exception as e:
    import_podman_error_tag = True
    # Display debug message if import KeyError
    logger.warning("Error loading Podman deps Lib. Podman feature in the Containers plugin is disabled ({})".format(e))
else:
    import_podman_error_tag = False


class PodmanContainerStatsFetcher:
    MANDATORY_FIELDS = ["CPU", "MemUsage", "MemLimit", "NetInput", "NetOutput", "BlockInput", "BlockOutput"]

    def __init__(self, container):
        self._container = container

        # Threaded Streamer
        stats_iterable = container.stats(decode=True)
        self._streamer = StatsStreamer(stats_iterable, initial_stream_value={})

    def _log_debug(self, msg, exception=None):
        logger.debug("containers (Podman) ID: {} - {} ({})".format(self._container.id, msg, exception))
        logger.debug(self._streamer.stats)

    def stop(self):
        self._streamer.stop()

    @property
    def stats(self):
        stats = self._streamer.stats
        if stats["Error"]:
            self._log_debug("Stats fetching failed", stats["Error"])

        return stats["Stats"][0]

    @property
    def activity_stats(self):
        result_stats = {"cpu": {}, "memory": {}, "io": {}, "network": {}}
        api_stats = self.stats

        if any(field not in api_stats for field in self.MANDATORY_FIELDS):
            self._log_debug("Missing mandatory fields")
            return result_stats

        try:
            cpu_usage = float(api_stats.get("CPU", 0))

            mem_usage = float(api_stats["MemUsage"])
            mem_limit = float(api_stats["MemLimit"])

            rx = float(api_stats["NetInput"])
            tx = float(api_stats["NetOutput"])

            ior = float(api_stats["BlockInput"])
            iow = float(api_stats["BlockOutput"])

            # Hardcode `time_since_update` to 1 as podman already sends the calculated rate
            result_stats = {
                "cpu": {"total": cpu_usage},
                "memory": {"usage": mem_usage, "limit": mem_limit},
                "io": {"ior": ior, "iow": iow, "time_since_update": 1},
                "network": {"rx": rx, "tx": tx, "time_since_update": 1},
            }
        except ValueError as e:
            self._log_debug("Non float stats values found", e)

        return result_stats


class PodmanPodStatsFetcher:
    def __init__(self, pod_manager):
        self._pod_manager = pod_manager

        # Threaded Streamer
        # Temporary patch to get podman extension working
        stats_iterable = (pod_manager.stats(decode=True) for _ in iter(int, 1))
        self._streamer = StatsStreamer(stats_iterable, initial_stream_value={}, sleep_duration=2)

    def _log_debug(self, msg, exception=None):
        logger.debug("containers (Podman): Pod Manager - {} ({})".format(msg, exception))
        logger.debug(self._streamer.stats)

    def stop(self):
        self._streamer.stop()

    @property
    def activity_stats(self):
        result_stats = {}
        container_stats = self._streamer.stats
        for stat in container_stats:
            io_stats = self._get_io_stats(stat)
            cpu_stats = self._get_cpu_stats(stat)
            memory_stats = self._get_memory_stats(stat)
            network_stats = self._get_network_stats(stat)

            computed_stats = {
                "name": stat["Name"],
                "cid": stat["CID"],
                "pod_id": stat["Pod"],
                "io": io_stats or {},
                "memory": memory_stats or {},
                "network": network_stats or {},
                "cpu": cpu_stats or {"total": 0.0},
            }
            result_stats[stat["CID"]] = computed_stats

        return result_stats

    def _get_cpu_stats(self, stats):
        """Return the container CPU usage.

        Output: a dict {'total': 1.49}
        """
        if "CPU" not in stats:
            self._log_debug("Missing CPU usage fields")
            return None

        cpu_usage = string_value_to_float(stats["CPU"].rstrip("%"))
        return {"total": cpu_usage}

    def _get_memory_stats(self, stats):
        """Return the container MEMORY.

        Output: a dict {'rss': 1015808, 'cache': 356352,  'usage': ..., 'max_usage': ...}
        """
        if "MemUsage" not in stats or "/" not in stats["MemUsage"]:
            self._log_debug("Missing MEM usage fields")
            return None

        memory_usage_str = stats["MemUsage"]
        usage_str, limit_str = memory_usage_str.split("/")

        try:
            usage = string_value_to_float(usage_str)
            limit = string_value_to_float(limit_str)
        except ValueError as e:
            self._log_debug("Compute MEM usage failed", e)
            return None

        return {"usage": usage, "limit": limit}

    def _get_network_stats(self, stats):
        """Return the container network usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'rx': 10, 'tx': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            rx: Number of bytes received
            tx: Number of bytes transmitted
        """
        if "NetIO" not in stats or "/" not in stats["NetIO"]:
            self._log_debug("Compute MEM usage failed")
            return None

        net_io_str = stats["NetIO"]
        rx_str, tx_str = net_io_str.split("/")

        try:
            rx = string_value_to_float(rx_str)
            tx = string_value_to_float(tx_str)
        except ValueError as e:
            self._log_debug("Compute MEM usage failed", e)
            return None

        # Hardcode `time_since_update` to 1 as podman docs don't specify the rate calculated procedure
        return {"rx": rx, "tx": tx, "time_since_update": 1}

    def _get_io_stats(self, stats):
        """Return the container IO usage using the Docker API (v1.0 or higher).

        Output: a dict {'time_since_update': 3000, 'ior': 10, 'iow': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            ior: Number of bytes read
            iow: Number of bytes written
        """
        if "BlockIO" not in stats or "/" not in stats["BlockIO"]:
            self._log_debug("Missing BlockIO usage fields")
            return None

        block_io_str = stats["BlockIO"]
        ior_str, iow_str = block_io_str.split("/")

        try:
            ior = string_value_to_float(ior_str)
            iow = string_value_to_float(iow_str)
        except ValueError as e:
            self._log_debug("Compute BlockIO usage failed", e)
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
        self.ext_name = "containers (Podman)"
        self.podman_sock = podman_sock
        self.pods_stats_fetcher = None
        self.container_stats_fetchers = {}

        self.connect()

    def connect(self):
        """Connect to Podman."""
        try:
            self.client = PodmanClient(base_url=self.podman_sock)
            # PodmanClient works lazily, so make a ping to determine if socket is open
            self.client.ping()
        except Exception as e:
            logger.error("{} plugin - Can't connect to Podman ({})".format(self.ext_name, e))
            self.client = None

    def update_version(self):
        # Long and not useful anymore because the information is no more displayed in UIs
        # return self.client.version()
        return {}

    def stop(self):
        # Stop all streaming threads
        for t in itervalues(self.container_stats_fetchers):
            t.stop()

        if self.pods_stats_fetcher:
            self.pods_stats_fetcher.stop()

    def update(self, all_tag):
        """Update Podman stats using the input method."""

        if not self.client:
            return {}, []

        version_stats = self.update_version()

        # Update current containers list
        try:
            # Issue #1152: Podman module doesn't export details about stopped containers
            # The Containers/all key of the configuration file should be set to True
            containers = self.client.containers.list(all=all_tag)
            if not self.pods_stats_fetcher:
                self.pods_stats_fetcher = PodmanPodStatsFetcher(self.client.pods)
        except Exception as e:
            logger.error("{} plugin - Can't get containers list ({})".format(self.ext_name, e))
            return version_stats, []

        # Start new thread for new container
        for container in containers:
            if container.id not in self.container_stats_fetchers:
                # StatsFetcher did not exist in the internal dict
                # Create it, add it to the internal dict
                logger.debug("{} plugin - Create thread for container {}".format(self.ext_name, container.id[:12]))
                self.container_stats_fetchers[container.id] = PodmanContainerStatsFetcher(container)

        # Stop threads for non-existing containers
        absent_containers = set(iterkeys(self.container_stats_fetchers)) - set(c.id for c in containers)
        for container_id in absent_containers:
            # Stop the StatsFetcher
            logger.debug("{} plugin - Stop thread for old container {}".format(self.ext_name, container_id[:12]))
            self.container_stats_fetchers[container_id].stop()
            # Delete the StatsFetcher from the dict
            del self.container_stats_fetchers[container_id]

        # Get stats for all containers
        container_stats = [self.generate_stats(container) for container in containers]

        pod_stats = self.pods_stats_fetcher.activity_stats
        for stats in container_stats:
            if stats["Id"][:12] in pod_stats:
                stats["pod_name"] = pod_stats[stats["Id"][:12]]["name"]
                stats["pod_id"] = pod_stats[stats["Id"][:12]]["pod_id"]

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
            started_at = datetime.fromtimestamp(container.attrs['StartedAt'])
            stats_fetcher = self.container_stats_fetchers[container.id]
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
            stats['Uptime'] = pretty_date(started_at)
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
