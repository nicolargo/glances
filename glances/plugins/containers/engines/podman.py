#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only

"""Podman Extension unit for Glances' Containers plugin."""

import time
from datetime import datetime
from typing import Any, Optional

from glances.globals import iterkeys, itervalues, nativestr, pretty_date, replace_special_chars, string_value_to_float
from glances.logger import logger
from glances.stats_streamer import ThreadedIterableStreamer

# Podman library (optional and Linux-only)
# https://pypi.org/project/podman/
try:
    from podman import PodmanClient
except Exception as e:
    disable_plugin_podman = True
    # Display debug message if import KeyError
    logger.warning(f"Error loading Podman deps Lib. Podman feature in the Containers plugin is disabled ({e})")
else:
    disable_plugin_podman = False


class PodmanContainerStatsFetcher:
    MANDATORY_FIELDS = ["CPU", "MemUsage", "MemLimit", "BlockInput", "BlockOutput"]

    def __init__(self, container):
        self._container = container

        # Previous stats are stored in the self._old_computed_stats variable
        # We store time data to enable rate calculations to avoid complexity for consumers of the APIs exposed.
        self._old_computed_stats = {}

        # Last time when output stats (results) were computed
        self._last_stats_computed_time = 0

        # Threaded Streamer
        stats_iterable = container.stats(decode=True)
        self._streamer = ThreadedIterableStreamer(stats_iterable, initial_stream_value={})

    def stop(self):
        self._streamer.stop()

    def get_streamed_stats(self) -> dict[str, Any]:
        stats = self._streamer.stats
        if stats["Error"]:
            logger.error(f"containers (Podman) Container({self._container.id}): Stats fetching failed")
            logger.debug(f"containers (Podman) Container({self._container.id}): ", stats)

        return stats["Stats"][0]

    @property
    def activity_stats(self) -> dict[str, Any]:
        """Activity Stats

        Each successive access of activity_stats will cause computation of activity_stats
        """
        computed_activity_stats = self._compute_activity_stats()
        self._old_computed_stats = computed_activity_stats
        self._last_stats_computed_time = time.time()
        return computed_activity_stats

    def _compute_activity_stats(self) -> dict[str, dict[str, Any]]:
        stats = {"cpu": {}, "memory": {}, "io": {}, "network": {}}
        api_stats = self.get_streamed_stats()

        if any(field not in api_stats for field in self.MANDATORY_FIELDS) or (
            "Network" not in api_stats and any(k not in api_stats for k in ['NetInput', 'NetOutput'])
        ):
            logger.error(f"containers (Podman) Container({self._container.id}): Missing mandatory fields")
            return stats

        try:
            stats["cpu"]["total"] = api_stats['CPU']

            stats["memory"]["usage"] = api_stats["MemUsage"]
            stats["memory"]["limit"] = api_stats["MemLimit"]

            stats["io"]["ior"] = api_stats["BlockInput"]
            stats["io"]["iow"] = api_stats["BlockOutput"]
            stats["io"]["time_since_update"] = 1
            # Hardcode `time_since_update` to 1 as podman already sends at the same fixed rate per second

            if "Network" not in api_stats:
                # For podman rooted mode
                stats["network"]['rx'] = api_stats["NetInput"]
                stats["network"]['tx'] = api_stats["NetOutput"]
                stats["network"]['time_since_update'] = 1
                # Hardcode to 1 as podman already sends at the same fixed rate per second
            elif api_stats["Network"] is not None:
                # api_stats["Network"] can be None if the infra container of the pod is killed
                # For podman in rootless mode
                stats['network'] = {
                    "cumulative_rx": sum(interface["RxBytes"] for interface in api_stats["Network"].values()),
                    "cumulative_tx": sum(interface["TxBytes"] for interface in api_stats["Network"].values()),
                }
                # Using previous stats to calculate rates
                old_network_stats = self._old_computed_stats.get("network")
                if old_network_stats:
                    stats['network']['time_since_update'] = round(self.time_since_update)
                    stats['network']['rx'] = stats['network']['cumulative_rx'] - old_network_stats["cumulative_rx"]
                    stats['network']['tx'] = stats['network']['cumulative_tx'] - old_network_stats['cumulative_tx']

        except ValueError as e:
            logger.error(f"containers (Podman) Container({self._container.id}): Non float stats values found", e)

        return stats

    @property
    def time_since_update(self) -> float:
        # In case no update (at startup), default to 1
        return max(1, self._streamer.last_update_time - self._last_stats_computed_time)


class PodmanPodStatsFetcher:
    def __init__(self, pod_manager):
        self._pod_manager = pod_manager

        # Threaded Streamer
        # Temporary patch to get podman extension working
        stats_iterable = (pod_manager.stats(decode=True) for _ in iter(int, 1))
        self._streamer = ThreadedIterableStreamer(stats_iterable, initial_stream_value={}, sleep_duration=2)

    def _log_debug(self, msg, exception=None):
        logger.debug(f"containers (Podman): Pod Manager - {msg} ({exception})")
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
                "cpu": cpu_stats or {},
            }
            result_stats[stat["CID"]] = computed_stats

        return result_stats

    def _get_cpu_stats(self, stats: dict) -> Optional[dict]:
        """Return the container CPU usage.

        Output: a dict {'total': 1.49}
        """
        if "CPU" not in stats:
            self._log_debug("Missing CPU usage fields")
            return None

        cpu_usage = string_value_to_float(stats["CPU"].rstrip("%"))
        return {"total": cpu_usage}

    def _get_memory_stats(self, stats) -> Optional[dict]:
        """Return the container MEMORY.

        Output: a dict {'usage': ..., 'limit': ...}
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

        return {'usage': usage, 'limit': limit, 'inactive_file': 0}

    def _get_network_stats(self, stats) -> Optional[dict]:
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

        # Hardcode `time_since_update` to 1 as podman docs don't specify the rate calculation procedure
        return {"rx": rx, "tx": tx, "time_since_update": 1}

    def _get_io_stats(self, stats) -> Optional[dict]:
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

        # Hardcode `time_since_update` to 1 as podman docs don't specify the rate calculation procedure
        return {"ior": ior, "iow": iow, "time_since_update": 1}


class PodmanExtension:
    """Glances' Containers Plugin's Docker Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['running', 'paused']

    def __init__(self, podman_sock):
        self.disable = disable_plugin_podman
        if self.disable:
            raise Exception("Missing libs required to run Podman Extension (Containers)")

        self.display_error = True

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
            logger.debug(f"{self.ext_name} plugin - Can't connect to Podman ({e})")
            self.client = None
            self.disable = True

    def update_version(self):
        # Long and not useful anymore because the information is no more displayed in UIs
        # return self.client.version()
        return {}

    def stop(self) -> None:
        # Stop all streaming threads
        for t in itervalues(self.container_stats_fetchers):
            t.stop()

        if self.pods_stats_fetcher:
            self.pods_stats_fetcher.stop()

    def update(self, all_tag) -> tuple[dict, list[dict[str, Any]]]:
        """Update Podman stats using the input method."""

        if not self.client or self.disable:
            return {}, []

        version_stats = self.update_version()

        # Update current containers list
        try:
            # Issue #1152: Podman module doesn't export details about stopped containers
            # The Containers/all key of the configuration file should be set to True
            containers = self.client.containers.list(all=all_tag)
            if not self.pods_stats_fetcher:
                self.pods_stats_fetcher = PodmanPodStatsFetcher(self.client.pods)
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
            if container.id not in self.container_stats_fetchers:
                # StatsFetcher did not exist in the internal dict
                # Create it, add it to the internal dict
                logger.debug(f"{self.ext_name} plugin - Create thread for container {container.id[:12]}")
                self.container_stats_fetchers[container.id] = PodmanContainerStatsFetcher(container)

        # Stop threads for non-existing containers
        absent_containers = set(iterkeys(self.container_stats_fetchers)) - {c.id for c in containers}
        for container_id in absent_containers:
            # Stop the StatsFetcher
            logger.debug(f"{self.ext_name} plugin - Stop thread for old container {container_id[:12]}")
            self.container_stats_fetchers[container_id].stop()
            # Delete the StatsFetcher from the dict
            del self.container_stats_fetchers[container_id]

        # Get stats for all containers
        container_stats = [self.generate_stats(container) for container in containers]

        pod_stats = self.pods_stats_fetcher.activity_stats
        for stats in container_stats:
            if stats["id"][:12] in pod_stats:
                stats["pod_name"] = pod_stats[stats["id"][:12]]["name"]
                stats["pod_id"] = pod_stats[stats["id"][:12]]["pod_id"]

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
            'image': ','.join(container.image.tags if container.image.tags else []),
            'status': container.attrs['State'],
            'created': container.attrs['Created'],
            'command': container.attrs.get('Command') or [],
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

        if stats['status'] not in self.CONTAINER_ACTIVE_STATUS:
            return stats

        stats_fetcher = self.container_stats_fetchers[container.id]
        activity_stats = stats_fetcher.activity_stats
        stats.update(activity_stats)

        # Additional fields
        stats['cpu_percent'] = stats['cpu'].get('total')
        stats['memory_usage'] = stats['memory'].get('usage')
        if stats['memory'].get('cache') is not None:
            stats['memory_usage'] -= stats['memory']['cache']

        if all(k in stats['io'] for k in ('ior', 'iow', 'time_since_update')):
            stats['io_rx'] = stats['io']['ior'] // stats['io']['time_since_update']
            stats['io_wx'] = stats['io']['iow'] // stats['io']['time_since_update']

        if all(k in stats['network'] for k in ('rx', 'tx', 'time_since_update')):
            stats['network_rx'] = stats['network']['rx'] // stats['network']['time_since_update']
            stats['network_tx'] = stats['network']['tx'] // stats['network']['time_since_update']

        started_at = datetime.fromtimestamp(container.attrs['StartedAt'])
        stats['uptime'] = pretty_date(started_at)

        # Manage special chars in command (see issue#2733)
        stats['command'] = replace_special_chars(' '.join(stats['command']))

        return stats
