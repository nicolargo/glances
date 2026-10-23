#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — ZFS plugin (collection, per-pool).

Pools and datasets are read from the JSON output of ``zpool``/``zfs``,
available since OpenZFS 2.3. Pools are joined from ``zpool list`` and
``zpool status`` by GUID; datasets are attached by pool name.

The plugin disables itself automatically when ZFS JSON output is
unavailable (no ZFS, or OpenZFS < 2.3).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.fs import zfs
from glances.plugins.plugin.base import GlancesPluginBase

logger = logging.getLogger(__name__)

STATE_LEVEL = {
    'ONLINE': 'ok',
    'DEGRADED': 'warning',
    'OFFLINE': 'warning',
    'REMOVED': 'warning',
    'FAULTED': 'critical',
    'UNAVAIL': 'critical',
}


class PluginModel(GlancesPluginBase[list]):
    """ZFS pools and datasets plugin (collection)."""

    plugin_name: ClassVar[str] = 'zfs'
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True
    DISABLED_BY_DEFAULT: ClassVar[bool] = True
    DEFAULT_REFRESH_TIME: ClassVar[float | None] = 300.0

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        'name': {
            'description': 'Pool name.',
            'unit': 'string',
            'primary_key': True,
        },
        'guid': {
            'description': 'Pool GUID.',
            'unit': 'string',
            'internal': True,
            'watched': False,
        },
        'state': {
            'description': 'Pool state (ONLINE, DEGRADED, ...).',
            'short_name': 'STATE',
            'unit': 'string',
            'watched': False,
        },
        'health': {
            'description': 'Pool health reported by zpool list.',
            'unit': 'string',
            'internal': True,
            'watched': False,
        },
        'size': {
            'description': 'Pool total size.',
            'unit': 'bytes',
            'internal': True,
            'watched': False,
        },
        'allocated': {
            'description': 'Pool allocated space.',
            'unit': 'bytes',
            'history': True,
            'internal': True,
            'watched': False,
        },
        'free': {
            'description': 'Pool free space.',
            'unit': 'bytes',
            'internal': True,
            'watched': False,
        },
        'capacity': {
            'description': 'Pool capacity in percent.',
            'short_name': 'CAP',
            'unit': 'percent',
            'history': True,
            'watched': True,
            'watch_direction': 'high',
            'prominent': False,
            'default_thresholds': {'warning': 80.0, 'critical': 90.0},
        },
        'fragmentation': {
            'description': 'Pool fragmentation in percent.',
            'short_name': 'FRAG',
            'unit': 'percent',
            'watched': False,
        },
        'read_errors': {
            'description': 'Total read errors.',
            'short_name': 'ERR',
            'unit': 'number',
            'watched': True,
            'watch_direction': 'high',
            'threshold_field': 'errors',
            'prominent': False,
            'default_thresholds': {'warning': 1.0},
        },
        'write_errors': {
            'description': 'Total write errors.',
            'unit': 'number',
            'watched': True,
            'watch_direction': 'high',
            'threshold_field': 'errors',
            'prominent': False,
            'default_thresholds': {'warning': 1.0},
        },
        'checksum_errors': {
            'description': 'Total checksum errors.',
            'unit': 'number',
            'watched': True,
            'watch_direction': 'high',
            'threshold_field': 'errors',
            'prominent': False,
            'default_thresholds': {'warning': 1.0},
        },
        'error_count': {
            'description': 'Pool data error count.',
            'unit': 'number',
            'watched': True,
            'watch_direction': 'high',
            'threshold_field': 'errors',
            'prominent': False,
            'default_thresholds': {'warning': 1.0},
        },
        'status': {
            'description': 'Pool status message from zpool status.',
            'unit': 'string',
            'internal': True,
            'watched': False,
        },
        'scan_function': {
            'description': 'Last scan function (scrub or resilver).',
            'unit': 'string',
            'internal': True,
            'watched': False,
        },
        'scan_state': {
            'description': 'Last scan state.',
            'unit': 'string',
            'internal': True,
            'watched': False,
        },
        'scan_errors': {
            'description': 'Last scan errors.',
            'unit': 'number',
            'watched': True,
            'watch_direction': 'high',
            'threshold_field': 'scan',
            'prominent': False,
            'default_thresholds': {'warning': 1.0},
        },
        'scan_progress': {
            'description': 'Current scan progress in percent.',
            'unit': 'percent',
            'internal': True,
            'watched': False,
        },
        'vdevs': {
            'description': 'Pool VDEVs.',
            'unit': 'list',
            'internal': True,
            'watched': False,
        },
        'datasets': {
            'description': 'Pool datasets.',
            'unit': 'list',
            'internal': True,
            'watched': False,
        },
    }

    def __init__(self, store, config) -> None:
        """Initialize the ZFS plugin from the shared stats store and configuration."""
        super().__init__(store, config)
        self.show_datasets = bool(self.config.get(self.plugin_name, 'show_datasets', False))
        self.max_depth = int(self.config.get(self.plugin_name, 'max_depth', 32))
        self.max_datasets = int(self.config.get(self.plugin_name, 'max_datasets', 1000))

    def _add_metadata(self) -> None:
        super()._add_metadata()
        self._metadata['show_datasets'] = self.show_datasets

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect, self.max_depth, self.max_datasets)

    @staticmethod
    def _collect(max_depth: int, max_datasets: int) -> list:
        if not zfs.zfs_json_supported():
            return []

        pools_list = zfs.zfs_pools_list()
        pools_status = zfs.zfs_pools()
        if not pools_list and not pools_status:
            logger.debug('zfs: no pools found')
            return []

        return PluginModel._build_stats(pools_list, pools_status, zfs.zfs_datasets(), max_depth, max_datasets)

    @staticmethod
    def _as_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _property_value(props, key, default=''):
        return props.get(key, {}).get('value', default)

    @classmethod
    def _flatten_vdevs(cls, vdevs):
        ret = []
        if not isinstance(vdevs, dict):
            return ret
        for vdev in vdevs.values():
            if not isinstance(vdev, dict):
                continue
            ret.append(
                {
                    'name': vdev.get('name', ''),
                    'guid': vdev.get('guid', ''),
                    'type': vdev.get('vdev_type', ''),
                    'state': vdev.get('state', ''),
                    'read_errors': cls._as_int(vdev.get('read_errors', 0)),
                    'write_errors': cls._as_int(vdev.get('write_errors', 0)),
                    'checksum_errors': cls._as_int(vdev.get('checksum_errors', 0)),
                }
            )
            ret.extend(cls._flatten_vdevs(vdev.get('vdevs', {})))
        return ret

    @classmethod
    def _scan_progress(cls, scan):
        to_examine = cls._as_int(scan.get('to_examine', 0))
        if to_examine <= 0:
            return 0
        return round(cls._as_int(scan.get('examined', 0)) * 100 / to_examine, 1)

    @classmethod
    def _datasets_by_pool(cls, datasets, max_depth, max_datasets):
        ret = {}
        count = 0
        for name in sorted(datasets):
            dataset = datasets[name]
            if not isinstance(dataset, dict):
                continue
            if max_datasets > 0 and count >= max_datasets:
                break
            if max_depth > 0 and name.count('/') > max_depth:
                continue
            props = dataset.get('properties', {})
            used = cls._as_int(cls._property_value(props, 'used', 0))
            available = cls._as_int(cls._property_value(props, 'available', 0))
            ret.setdefault(dataset.get('pool', ''), []).append(
                {
                    'name': name,
                    'used': used,
                    'available': available,
                    'referenced': cls._as_int(cls._property_value(props, 'referenced', 0)),
                    'mountpoint': cls._property_value(props, 'mountpoint', ''),
                    'used_percent': round(used * 100 / (used + available), 1) if (used + available) > 0 else 0,
                }
            )
            count += 1
        return ret

    @classmethod
    def _build_stats(cls, pools_list, pools_status, datasets, max_depth, max_datasets):
        stats = []
        datasets_by_pool = cls._datasets_by_pool(datasets, max_depth, max_datasets)
        for guid in sorted(set(pools_list) | set(pools_status)):
            pool_list = pools_list.get(guid, {})
            pool_status = pools_status.get(guid, {})
            props = pool_list.get('properties', {})
            name = pool_list.get('name') or pool_status.get('name') or guid
            health = cls._property_value(props, 'health', '')
            state = pool_status.get('state') or pool_list.get('state') or health
            vdevs = cls._flatten_vdevs(pool_status.get('vdevs', {}))
            scan = pool_status.get('scan_stats', {})
            stats.append(
                {
                    'name': name,
                    'guid': guid,
                    'state': state,
                    'health': health,
                    'size': cls._as_int(cls._property_value(props, 'size', 0)),
                    'allocated': cls._as_int(cls._property_value(props, 'allocated', 0)),
                    'free': cls._as_int(cls._property_value(props, 'free', 0)),
                    'capacity': cls._as_int(cls._property_value(props, 'capacity', 0)),
                    'fragmentation': cls._as_int(cls._property_value(props, 'fragmentation', 0)),
                    'read_errors': sum(v['read_errors'] for v in vdevs),
                    'write_errors': sum(v['write_errors'] for v in vdevs),
                    'checksum_errors': sum(v['checksum_errors'] for v in vdevs),
                    'error_count': cls._as_int(pool_status.get('error_count', 0)),
                    'status': pool_status.get('status', '') or '',
                    'scan_function': scan.get('function', ''),
                    'scan_state': scan.get('state', ''),
                    'scan_errors': cls._as_int(scan.get('errors', 0)),
                    'scan_progress': cls._scan_progress(scan),
                    'vdevs': vdevs,
                    'datasets': datasets_by_pool.get(name, []),
                }
            )
        return stats

    def _derived_parameters(self) -> None:
        super()._derived_parameters()
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            name = item.get('name')
            if name is None:
                continue
            entry = self._levels.setdefault(name, {})
            level = STATE_LEVEL.get(str(item.get('state', '')))
            if level is not None:
                entry['state'] = {'level': level, 'prominent': False}
