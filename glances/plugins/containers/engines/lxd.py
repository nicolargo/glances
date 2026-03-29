#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Christian Rishøj <christian@rishoj.net>
#
# SPDX-License-Identifier: LGPL-3.0-only

"""LXD Extension unit for Glances' Containers plugin."""

import threading
import time
from datetime import datetime
from typing import Any

from glances.globals import nativestr, pretty_date
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
        self._last_stats_computed_time = time.time()

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
        with self._state_lock:
            state = self._state

        if state is None:
            return {"cpu": {}, "memory": {}, "io": {}, "network": {}}

        return {
            "cpu": self._get_cpu_stats(state),
            "memory": self._get_memory_stats(state),
            "io": self._get_io_stats(state),
            "network": self._get_network_stats(state),
        }

    def _get_cpu_stats(self, state) -> dict[str, Any]:
        """Return CPU usage stats.

        LXD reports cumulative CPU time in nanoseconds.
        We compute a percentage from the delta between two polls.
        """
        stats = {}
        try:
            cumulative_cpu_ns = state.cpu["usage"]
            stats["cumulative_ns"] = cumulative_cpu_ns

            old_cpu = self._old_computed_stats.get("cpu", {})
            if "cumulative_ns" in old_cpu:
                delta_ns = cumulative_cpu_ns - old_cpu["cumulative_ns"]
                delta_seconds = self.time_since_update
                # Convert ns delta to a percentage (assuming 1 core = 100%)
                stats["total"] = (delta_ns / (delta_seconds * 1e9)) * 100.0
            else:
                stats["total"] = 0.0
        except (KeyError, TypeError, ZeroDivisionError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab CPU stats ({e})")
        return stats

    def _get_memory_stats(self, state) -> dict[str, Any]:
        """Return memory usage stats.

        LXD reports memory values in bytes.
        'total' is 0 when unlimited; fall back to usage_peak.
        """
        stats = {}
        try:
            stats["usage"] = state.memory["usage"]
            mem_total = state.memory.get("total", 0)
            if mem_total > 0:
                stats["limit"] = mem_total
            else:
                stats["limit"] = state.memory.get("usage_peak", state.memory["usage"])
            stats["inactive_file"] = 0
        except (KeyError, TypeError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab MEM stats ({e})")
        return stats

    def _get_io_stats(self, state) -> dict[str, Any]:
        """Return disk IO stats.

        LXD only exposes cumulative disk usage per device, not separate read/write.
        """
        stats = {}
        try:
            if state.disk and "root" in state.disk:
                cumulative_disk = state.disk["root"].get("usage", 0)
                stats["cumulative_ior"] = cumulative_disk
                stats["cumulative_iow"] = 0

                old_io = self._old_computed_stats.get("io", {})
                if "cumulative_ior" in old_io:
                    stats["time_since_update"] = round(self.time_since_update)
                    stats["ior"] = max(0, cumulative_disk - old_io["cumulative_ior"])
                    stats["iow"] = 0
        except (KeyError, TypeError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab IO stats ({e})")
        return stats

    def _get_network_stats(self, state) -> dict[str, Any]:
        """Return network usage stats.

        Sums counters across all non-loopback interfaces.
        """
        stats = {}
        try:
            if state.network:
                cumulative_rx = 0
                cumulative_tx = 0
                for iface in state.network.values():
                    if iface.get("type") == "loopback":
                        continue
                    counters = iface.get("counters", {})
                    cumulative_rx += counters.get("bytes_received", 0)
                    cumulative_tx += counters.get("bytes_sent", 0)

                stats["cumulative_rx"] = cumulative_rx
                stats["cumulative_tx"] = cumulative_tx

                old_net = self._old_computed_stats.get("network", {})
                if "cumulative_rx" in old_net:
                    stats["time_since_update"] = round(self.time_since_update)
                    stats["rx"] = max(0, cumulative_rx - old_net["cumulative_rx"])
                    stats["tx"] = max(0, cumulative_tx - old_net["cumulative_tx"])
        except (KeyError, TypeError) as e:
            logger.debug(f"containers (LXD) Instance({self._instance.name}): Can't grab NET stats ({e})")
        return stats


class LxdExtension:
    """Glances' Containers Plugin's LXD Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['Running']

    def __init__(self, endpoint=None, poll_interval=2):
        self.disable = disable_plugin_lxd
        if self.disable:
            raise Exception("Missing libs required to run LXD Extension (Containers)")

        self.display_error = True
        self.client = None
        self.ext_name = "containers (LXD)"
        self.endpoint = endpoint
        self.poll_interval = poll_interval
        self.stats_fetchers = {}
        self.local_node = None

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
            # Determine local cluster member name (for filtering)
            try:
                env = self.client.host_info.get('environment', {})
                self.local_node = env.get('server_name')
            except Exception:
                self.local_node = None
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
            # In a cluster, only show instances running on this node
            if self.local_node:
                instances = [i for i in instances if getattr(i, 'location', None) == self.local_node]
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
                self.stats_fetchers[instance.name] = LxdStatsFetcher(instance, poll_interval=self.poll_interval)

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
            stats['io_rx'] = stats['io']['ior'] // max(1, stats['io']['time_since_update'])
            stats['io_wx'] = stats['io']['iow'] // max(1, stats['io']['time_since_update'])

        if all(k in stats['network'] for k in ('rx', 'tx', 'time_since_update')):
            stats['network_rx'] = stats['network']['rx'] // max(1, stats['network']['time_since_update'])
            stats['network_tx'] = stats['network']['tx'] // max(1, stats['network']['time_since_update'])

        # Ports from proxy devices (e.g. listen=tcp:0.0.0.0:80 connect=tcp:127.0.0.1:80)
        try:
            devices = instance.expanded_devices or {}
            port_list = []
            for dev in devices.values():
                if dev.get('type') != 'proxy':
                    continue
                listen = dev.get('listen', '')
                connect = dev.get('connect', '')
                # Extract port from "tcp:0.0.0.0:80" format
                listen_port = listen.rsplit(':', 1)[-1] if listen else ''
                connect_port = connect.rsplit(':', 1)[-1] if connect else ''
                if listen_port:
                    proto = listen.split(':')[0] if ':' in listen else 'tcp'
                    port_list.append(f"{listen_port}->{connect_port}/{proto}")
            if port_list:
                stats['ports'] = ','.join(port_list)
        except (AttributeError, TypeError) as e:
            logger.debug(f"{self.ext_name} plugin - Can't get ports for {instance.name} ({e})")

        # Uptime from last_used_at
        try:
            last_used = instance.last_used_at
            if last_used and last_used != '1970-01-01T00:00:00Z':
                started = datetime.fromisoformat(last_used.replace('Z', '+00:00')).replace(tzinfo=None)
                stats['uptime'] = pretty_date(started)
        except (ValueError, AttributeError) as e:
            logger.debug(f"{self.ext_name} plugin - Can't compute uptime for {instance.name} ({e})")

        return stats
