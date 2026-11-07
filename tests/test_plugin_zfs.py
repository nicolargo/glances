#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 ZFS plugin model."""

from __future__ import annotations

import pytest

from glances.config import GlancesConfig
from glances.plugins.zfs import model as zfs_mod
from glances.plugins.zfs.model import PluginModel
from glances.stats_store import StatsStore

TANK_GUID = '3920273586464696295'


@pytest.fixture
def store() -> StatsStore:
    return StatsStore()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, 'SYSTEM_CONFIG_PATH', tmp_path / 'etc' / 'glances.conf')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg'))
    return GlancesConfig()


def _pool_list(name='tank', guid=TANK_GUID, size=1000, allocated=100, free=900, capacity=10, fragmentation=5):
    return {
        'name': name,
        'guid': guid,
        'properties': {
            'size': {'value': size},
            'allocated': {'value': allocated},
            'free': {'value': free},
            'capacity': {'value': capacity},
            'fragmentation': {'value': fragmentation},
            'health': {'value': 'ONLINE'},
        },
    }


def _pool_status(name='tank', guid=TANK_GUID, state='ONLINE', error_count=0, status=''):
    return {
        'name': name,
        'guid': guid,
        'state': state,
        'error_count': error_count,
        'status': status,
        'vdevs': {},
        'scan_stats': {},
    }


def _dataset(name='tank/home', pool='tank', used=10, available=90, referenced=5, mountpoint='/tank/home'):
    return {
        'name': name,
        'type': 'FILESYSTEM',
        'pool': pool,
        'properties': {
            'used': {'value': used},
            'available': {'value': available},
            'referenced': {'value': referenced},
            'mountpoint': {'value': mountpoint},
        },
    }


def _expected_dataset(name='tank/home', used=10, available=90, referenced=5, mountpoint='/tank/home'):
    return {
        'name': name,
        'used': used,
        'available': available,
        'referenced': referenced,
        'mountpoint': mountpoint,
        'used_percent': round(used * 100 / (used + available), 1) if (used + available) > 0 else 0,
    }


def _expected_pool(**overrides):
    pool = {
        'name': 'tank',
        'guid': TANK_GUID,
        'state': 'ONLINE',
        'health': 'ONLINE',
        'size': 1000,
        'allocated': 100,
        'free': 900,
        'capacity': 10,
        'fragmentation': 5,
        'read_errors': 0,
        'write_errors': 0,
        'checksum_errors': 0,
        'error_count': 0,
        'status': '',
        'scan_function': '',
        'scan_state': '',
        'scan_errors': 0,
        'scan_progress': 0,
        'vdevs': [],
        'datasets': [],
    }
    pool.update(overrides)
    return pool


def _patch_zfs(monkeypatch, pools_list=None, pools_status=None, datasets=None, supported=True):
    monkeypatch.setattr(zfs_mod.zfs, 'zfs_json_supported', lambda: supported)
    monkeypatch.setattr(zfs_mod.zfs, 'zfs_pools_list', lambda: pools_list or {})
    monkeypatch.setattr(zfs_mod.zfs, 'zfs_pools', lambda: pools_status or {})
    monkeypatch.setattr(zfs_mod.zfs, 'zfs_datasets', lambda: datasets or {})


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert (plugin.plugin_name, plugin.IS_COLLECTION, plugin._primary_key) == ('zfs', True, 'name')  # nosec B101


def test_disabled_by_default(store, config):
    assert PluginModel.is_disabled(config) is True  # nosec B101


def test_default_refresh_is_5_minutes(store, config):
    assert PluginModel.DEFAULT_REFRESH_TIME == 300.0  # nosec B101


def test_fields_description():
    actual = {
        name: {
            'primary_key': spec.get('primary_key', False),
            'unit': spec.get('unit'),
            'internal': spec.get('internal', False),
            'watched': spec.get('watched', False),
            'history': spec.get('history', False),
        }
        for name, spec in PluginModel.fields_description.items()
    }
    assert actual == {  # nosec B101
        'name': {'primary_key': True, 'unit': 'string', 'internal': False, 'watched': False, 'history': False},
        'guid': {'primary_key': False, 'unit': 'string', 'internal': True, 'watched': False, 'history': False},
        'state': {'primary_key': False, 'unit': 'string', 'internal': False, 'watched': False, 'history': False},
        'health': {'primary_key': False, 'unit': 'string', 'internal': True, 'watched': False, 'history': False},
        'size': {'primary_key': False, 'unit': 'bytes', 'internal': True, 'watched': False, 'history': False},
        'allocated': {'primary_key': False, 'unit': 'bytes', 'internal': True, 'watched': False, 'history': True},
        'free': {'primary_key': False, 'unit': 'bytes', 'internal': True, 'watched': False, 'history': False},
        'capacity': {'primary_key': False, 'unit': 'percent', 'internal': False, 'watched': True, 'history': True},
        'fragmentation': {
            'primary_key': False,
            'unit': 'percent',
            'internal': False,
            'watched': False,
            'history': False,
        },
        'read_errors': {'primary_key': False, 'unit': 'number', 'internal': False, 'watched': True, 'history': False},
        'write_errors': {'primary_key': False, 'unit': 'number', 'internal': False, 'watched': True, 'history': False},
        'checksum_errors': {
            'primary_key': False,
            'unit': 'number',
            'internal': False,
            'watched': True,
            'history': False,
        },
        'error_count': {'primary_key': False, 'unit': 'number', 'internal': False, 'watched': True, 'history': False},
        'status': {'primary_key': False, 'unit': 'string', 'internal': True, 'watched': False, 'history': False},
        'scan_function': {'primary_key': False, 'unit': 'string', 'internal': True, 'watched': False, 'history': False},
        'scan_state': {'primary_key': False, 'unit': 'string', 'internal': True, 'watched': False, 'history': False},
        'scan_errors': {'primary_key': False, 'unit': 'number', 'internal': False, 'watched': True, 'history': False},
        'scan_progress': {
            'primary_key': False,
            'unit': 'percent',
            'internal': True,
            'watched': False,
            'history': False,
        },
        'vdevs': {'primary_key': False, 'unit': 'list', 'internal': True, 'watched': False, 'history': False},
        'datasets': {'primary_key': False, 'unit': 'list', 'internal': True, 'watched': False, 'history': False},
    }


def test_config_knobs_are_read(store, tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfig, 'SYSTEM_CONFIG_PATH', tmp_path / 'etc' / 'glances.conf')
    xdg = tmp_path / 'xdg'
    cfg_dir = xdg / 'glances'
    cfg_dir.mkdir(parents=True)
    (cfg_dir / 'glances.conf').write_text('[zfs]\ndisable=False\nshow_datasets=True\nmax_depth=2\nmax_datasets=50\n')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(xdg))
    plugin = PluginModel(store, GlancesConfig())
    assert (plugin.show_datasets, plugin.max_depth, plugin.max_datasets) == (True, 2, 50)  # nosec B101


@pytest.mark.asyncio
async def test_grab_stats_builds_pools_and_datasets(store, config, monkeypatch):
    _patch_zfs(
        monkeypatch,
        pools_list={TANK_GUID: _pool_list()},
        pools_status={TANK_GUID: _pool_status()},
        datasets={'tank/home': _dataset()},
    )
    plugin = PluginModel(store, config)
    assert await plugin._grab_stats() == [  # nosec B101
        _expected_pool(datasets=[_expected_dataset()]),
    ]


@pytest.mark.asyncio
async def test_grab_stats_keeps_status_text(store, config, monkeypatch):
    raw_status = 'One or more devices are configured to use a non-native block size.\n\tExpect reduced performance.\n'
    _patch_zfs(
        monkeypatch,
        pools_list={TANK_GUID: _pool_list()},
        pools_status={TANK_GUID: _pool_status(status=raw_status)},
    )
    plugin = PluginModel(store, config)
    assert await plugin._grab_stats() == [_expected_pool(status=raw_status)]  # nosec B101


@pytest.mark.asyncio
async def test_grab_stats_empty_when_json_unsupported(store, config, monkeypatch):
    _patch_zfs(monkeypatch, supported=False)
    plugin = PluginModel(store, config)
    assert await plugin._grab_stats() == []  # nosec B101


@pytest.mark.asyncio
async def test_grab_stats_empty_when_no_pools(store, config, monkeypatch):
    _patch_zfs(monkeypatch)
    plugin = PluginModel(store, config)
    assert await plugin._grab_stats() == []  # nosec B101


@pytest.mark.asyncio
async def test_datasets_are_limited_by_depth_and_count(store, tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfig, 'SYSTEM_CONFIG_PATH', tmp_path / 'etc' / 'glances.conf')
    xdg = tmp_path / 'xdg'
    cfg_dir = xdg / 'glances'
    cfg_dir.mkdir(parents=True)
    (cfg_dir / 'glances.conf').write_text('[zfs]\ndisable=False\nmax_depth=1\nmax_datasets=2\n')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(xdg))
    datasets = {
        'tank/a': _dataset('tank/a'),
        'tank/a/b': _dataset('tank/a/b'),
        'tank/b': _dataset('tank/b'),
    }
    _patch_zfs(
        monkeypatch,
        pools_list={TANK_GUID: _pool_list()},
        pools_status={TANK_GUID: _pool_status()},
        datasets=datasets,
    )
    plugin = PluginModel(store, GlancesConfig())
    assert await plugin._grab_stats() == [  # nosec B101
        _expected_pool(datasets=[_expected_dataset('tank/a'), _expected_dataset('tank/b')]),
    ]


def _row(state='ONLINE', capacity=10, read_errors=0):
    return {
        'name': 'tank',
        'state': state,
        'capacity': capacity,
        'read_errors': read_errors,
        'write_errors': 0,
        'checksum_errors': 0,
        'error_count': 0,
        'scan_errors': 0,
        'status': '',
    }


def _expected_levels(*, state='ok', capacity='ok', read_errors='ok'):
    return {
        'capacity': {'level': capacity, 'prominent': False},
        'read_errors': {'level': read_errors, 'prominent': False},
        'write_errors': {'level': 'ok', 'prominent': False},
        'checksum_errors': {'level': 'ok', 'prominent': False},
        'error_count': {'level': 'ok', 'prominent': False},
        'scan_errors': {'level': 'ok', 'prominent': False},
        'state': {'level': state, 'prominent': False},
    }


def test_state_levels(store, config):
    plugin = PluginModel(store, config)
    plugin._stats = [_row(state='ONLINE') | {'name': 'ok'}, _row(state='DEGRADED') | {'name': 'deg'}]
    plugin._derived_parameters()
    assert plugin._levels == {  # nosec B101
        'ok': _expected_levels(state='ok'),
        'deg': _expected_levels(state='warning'),
    }


def test_faulted_state_is_critical(store, config):
    plugin = PluginModel(store, config)
    plugin._stats = [_row(state='FAULTED')]
    plugin._derived_parameters()
    assert plugin._levels == {'tank': _expected_levels(state='critical')}  # nosec B101


def test_capacity_uses_watched_threshold(store, config):
    plugin = PluginModel(store, config)
    plugin._stats = [_row(capacity=95)]
    plugin._derived_parameters()
    assert plugin._levels == {'tank': _expected_levels(capacity='critical')}  # nosec B101


def test_device_errors_are_watched(store, config):
    plugin = PluginModel(store, config)
    plugin._stats = [_row(read_errors=1)]
    plugin._derived_parameters()
    assert plugin._levels == {'tank': _expected_levels(read_errors='warning')}  # nosec B101
