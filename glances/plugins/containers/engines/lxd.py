#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only

"""LXD Extension unit for Glances' Containers plugin."""

import threading
import time
from datetime import datetime
from typing import Any

from glances.globals import nativestr, pretty_date, replace_special_chars
from glances.logger import logger

# pylxd library (optional and Linux-only)
# https://github.com/canonical/pylxd
try:
    from pylxd import Client as LxdClient
except Exception as e:
    disable_plugin_lxd = True
    logger.warning(f"Error loading LXD deps Lib. LXD feature in the Containers plugin is disabled ({e})")
else:
    disable_plugin_lxd = False


class LxdStatsFetcher:
    """Fetch stats for a single LXD instance by polling its state."""

    def __init__(self, instance, poll_interval=2):
        self._instance = instance
        self._poll_interval = poll_interval

        # Store previous stats for rate calculations
        self._old_computed_stats = {}
        self._last_stats_computed_time = 0

        # Latest polled state
        self._state = None
        self._state_lock = threading.Lock()

        # Polling thread
        self._stopper = threading.Event()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        """Poll instance.state() in a background thread."""
        while not self._stopper.is_set():
            try:
                state = self._instance.state()
                with self._state_lock:
                    self._state = state
            except Exception as e:
                logger.debug(f"containers (LXD) Instance({self._instance.name}): Failed to poll state ({e})")
            self._stopper.wait(self._poll_interval)

    def stop(self):
        self._stopper.set()

    @property
    def activity_stats(self) -> dict[str, dict[str, Any]]:
        """Compute activity stats from the latest polled state."""
        computed = self._compute_activity_stats()
        self._old_computed_stats = computed
        self._last_stats_computed_time = time.time()
        return computed

    @property
    def time_since_update(self) -> float:
        return max(1, time.time() - self._last_stats_computed_time)

    def _compute_activity_stats(self) -> dict[str, dict[str, Any]]:
        stats = {"cpu": {}, "memory": {}, "io": {}, "network": {}}

        with self._state_lock:
            state = self._state

        if state is None:
            return stats

        # CPU: state.cpu["usage"] is cumulative nanoseconds
        try:
            cumulative_cpu_ns = state.cpu["usage"]
            stats["cpu"]["cumulative_ns"] = cumulative_cpu_ns

            old_cpu = self._old_computed_stats.get("cpu", {})
            if "cumulative_ns" in old_cpu:
                delta_ns = cumulative_cpu_ns - old_cpu["cumulative_ns"]
                delta_seconds = self.time_since_update
                # Convert ns delta to a percentage (assuming 1 core = 100%)
                stats["cpu"]["total"] = (delta_ns / (delta_seconds * 1e9)) * 100.0
            else:
                stats["cpu"]["total"] = 0.0
        except (KeyError, TypeError, ZeroDivisionError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab CPU stats ({e})")

        # Memory: state.memory values are in bytes
        try:
            stats["memory"]["usage"] = state.memory["usage"]
            # total is 0 when unlimited; fall back to usage_peak
            mem_total = state.memory.get("total", 0)
            if mem_total > 0:
                stats["memory"]["limit"] = mem_total
            else:
                stats["memory"]["limit"] = state.memory.get("usage_peak", state.memory["usage"])
            stats["memory"]["inactive_file"] = 0
        except (KeyError, TypeError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab MEM stats ({e})")

        # Disk IO: state.disk["root"]["usage"] is cumulative bytes
        try:
            if state.disk and "root" in state.disk:
                cumulative_disk = state.disk["root"].get("usage", 0)
                stats["io"]["cumulative_ior"] = cumulative_disk
                stats["io"]["cumulative_iow"] = 0  # LXD doesn't split read/write

                old_io = self._old_computed_stats.get("io", {})
                if "cumulative_ior" in old_io:
                    stats["io"]["time_since_update"] = round(self.time_since_update)
                    stats["io"]["ior"] = max(0, cumulative_disk - old_io["cumulative_ior"])
                    stats["io"]["iow"] = 0
        except (KeyError, TypeError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab IO stats ({e})")

        # Network: sum counters across all non-loopback interfaces
        try:
            if state.network:
                cumulative_rx = 0
                cumulative_tx = 0
                for iface_name, iface in state.network.items():
                    if iface.get("type") == "loopback":
                        continue
                    counters = iface.get("counters", {})
                    cumulative_rx += counters.get("bytes_received", 0)
                    cumulative_tx += counters.get("bytes_sent", 0)

                stats["network"]["cumulative_rx"] = cumulative_rx
                stats["network"]["cumulative_tx"] = cumulative_tx

                old_net = self._old_computed_stats.get("network", {})
                if "cumulative_rx" in old_net:
                    stats["network"]["time_since_update"] = round(self.time_since_update)
                    stats["network"]["rx"] = max(0, cumulative_rx - old_net["cumulative_rx"])
                    stats["network"]["tx"] = max(0, cumulative_tx - old_net["cumulative_tx"])
        except (KeyError, TypeError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab NET stats ({e})")

        return stats


class LxdExtension:
    """Glances' Containers Plugin's LXD Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['Running', 'running']

    def __init__(self, endpoint=None):
        self.disable = disable_plugin_lxd
        if self.disable:
            raise Exception("Missing libs required to run LXD Extension (Containers)")

        self.display_error = True
        self.client = None
        self.ext_name = "containers (LXD)"
        self.endpoint = endpoint
        self.stats_fetchers = {}

        self.connect()

    def connect(self) -> None:
        """Connect to the LXD server."""
        try:
            if self.endpoint:
                self.client = LxdClient(endpoint=self.endpoint)
            else:
                self.client = LxdClient()
            # Verify connectivity
            self.client.has_api_extension('instances')
        except Exception as e:
            logger.debug(f"{self.ext_name} plugin - Can't connect to LXD ({e})")
            self.client = None
            self.disable = True

    def stop(self) -> None:
        for t in self.stats_fetchers.values():
            t.stop()

    def update(self, all_tag) -> tuple[dict, list[dict[str, Any]]]:
        """Update LXD stats using the input method."""
        if not self.client or self.disable:
            return {}, []

        # List instances
        try:
            instances = self.client.instances.all()
            if not all_tag:
                instances = [i for i in instances if i.status in self.CONTAINER_ACTIVE_STATUS]
            self.display_error = True
        except Exception as e:
            if self.display_error:
                logger.error(f"{self.ext_name} plugin - Can't get instances list ({e})")
                self.display_error = False
            else:
                logger.debug(f"{self.ext_name} plugin - Can't get instances list ({e})")
            return {}, []

        # Start new fetcher threads for new instances
        for instance in instances:
            if instance.name not in self.stats_fetchers:
                logger.debug(f"{self.ext_name} plugin - Create thread for instance {instance.name}")
                self.stats_fetchers[instance.name] = LxdStatsFetcher(instance)

        # Stop threads for removed instances
        current_names = {i.name for i in instances}
        absent = set(self.stats_fetchers.keys()) - current_names
        for name in absent:
            logger.debug(f"{self.ext_name} plugin - Stop thread for old instance {name}")
            self.stats_fetchers[name].stop()
            del self.stats_fetchers[name]

        # Generate stats
        container_stats = [self.generate_stats(instance) for instance in instances]
        return {}, container_stats

    @property
    def key(self) -> str:
        return 'name'

    def generate_stats(self, instance) -> dict[str, Any]:
        stats = {
            'key': self.key,
            'name': nativestr(instance.name),
            'id': instance.name,
            'image': instance.config.get('image.description', ''),
            'status': instance.status.lower(),
            'created': instance.created_at,
            'command': None,
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
            'ports': '',
            'uptime': None,
        }

        if instance.status not in self.CONTAINER_ACTIVE_STATUS:
            return stats

        if instance.name not in self.stats_fetchers:
            return stats

        stats_fetcher = self.stats_fetchers[instance.name]
        activity_stats = stats_fetcher.activity_stats
        stats.update(activity_stats)

        # Additional fields
        stats['cpu_percent'] = stats['cpu'].get('total')
        stats['memory_usage'] = stats['memory'].get('usage')
        stats['memory_inactive_file'] = stats['memory'].get('inactive_file')
        stats['memory_limit'] = stats['memory'].get('limit')

        if all(k in stats['io'] for k in ('ior', 'iow', 'time_since_update')):
            stats['io_rx'] = stats['io']['ior'] // stats['io']['time_since_update']
            stats['io_wx'] = stats['io']['iow'] // stats['io']['time_since_update']

        if all(k in stats['network'] for k in ('rx', 'tx', 'time_since_update')):
            stats['network_rx'] = stats['network']['rx'] // stats['network']['time_since_update']
            stats['network_tx'] = stats['network']['tx'] // stats['network']['time_since_update']

        # Uptime from last_used_at
        try:
            last_used = instance.last_used_at
            if last_used and last_used != '1970-01-01T00:00:00Z':
                started = datetime.fromisoformat(last_used.replace('Z', '+00:00')).replace(tzinfo=None)
                stats['uptime'] = pretty_date(started)
        except (ValueError, AttributeError) as e:
            logger.debug(f"{self.ext_name} plugin - Can't compute uptime for {instance.name} ({e})")

        return stats
