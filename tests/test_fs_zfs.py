#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the ZFS helper functions (glances.plugins.fs.zfs)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from glances.plugins.fs import zfs

FIXTURES = Path(__file__).resolve().parent.parent / 'tests-data' / 'plugins' / 'fs' / 'zfs'

ZPOOL_STATUS_ARGS = ('zpool', 'status', '-j', '--json-int', '--json-pool-key-guid')
ZPOOL_LIST_ARGS = ('zpool', 'list', '-j', '--json-int', '--json-pool-key-guid')
ZFS_LIST_ARGS = (
    'zfs',
    'list',
    '-j',
    '--json-int',
    '-t',
    'filesystem,volume',
    '-o',
    'name,type,used,available,referenced,mountpoint',
)
VERSION_ARGS = ('zfs', '--version')


def _fixture(name):
    """Return the content of a ZFS JSON fixture."""
    return (FIXTURES / name).read_text()


def _runner(version='zfs-2.3.9-1\nzfs-kmod-2.3.9-1', outputs=None):
    """Build a stand-in for zfs._run_zfs_command.

    outputs maps an argv tuple to the stdout to return (or None to simulate
    a command failure).
    """
    outputs = outputs or {}

    def run(args, timeout=None):
        if tuple(args) == VERSION_ARGS:
            return version
        return outputs.get(tuple(args))

    return run


@pytest.fixture(autouse=True)
def clear_version_cache():
    """The JSON-capability check is cached; drop it around every test."""
    zfs.zfs_json_supported.cache_clear()
    yield
    zfs.zfs_json_supported.cache_clear()


class TestZfsJsonSupported:
    """JSON support is gated on the installed ZFS version being >= 2.3."""

    def test_supported_on_2_3(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version='zfs-2.3.0-1\nzfs-kmod-2.3.0-1'))
        assert zfs.zfs_json_supported() is True

    def test_supported_on_newer(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version='zfs-2.4.1-1'))
        assert zfs.zfs_json_supported() is True

    def test_not_supported_on_2_2(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version='zfs-2.2.6-1\nzfs-kmod-2.2.6-1'))
        assert zfs.zfs_json_supported() is False

    def test_not_supported_when_version_unparsable(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version='not a version'))
        assert zfs.zfs_json_supported() is False

    def test_not_supported_when_binary_missing(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version=None))
        assert zfs.zfs_json_supported() is False


class TestZfsPools:
    """zfs_pools() parses `zpool status -j` output, keyed by pool GUID."""

    def test_pools_keyed_by_guid(self, monkeypatch):
        monkeypatch.setattr(
            zfs, '_run_zfs_command', _runner(outputs={ZPOOL_STATUS_ARGS: _fixture('zpool_status.json')})
        )
        pools = zfs.zfs_pools()
        assert list(pools.keys()) == ['3920273586464696295']
        assert pools['3920273586464696295']['name'] == 'tank'

    def test_pool_numbers_are_integers(self, monkeypatch):
        monkeypatch.setattr(
            zfs, '_run_zfs_command', _runner(outputs={ZPOOL_STATUS_ARGS: _fixture('zpool_status.json')})
        )
        pools = zfs.zfs_pools()
        assert pools['3920273586464696295']['error_count'] == 0
        assert pools['3920273586464696295']['vdevs']['tank']['alloc_space'] == 68812800000
        assert pools['3920273586464696295']['vdevs']['tank']['total_space'] == 16492674416640

    def test_vdev_guids_are_preserved(self, monkeypatch):
        monkeypatch.setattr(
            zfs, '_run_zfs_command', _runner(outputs={ZPOOL_STATUS_ARGS: _fixture('zpool_status.json')})
        )
        pools = zfs.zfs_pools()
        vdevs = pools['3920273586464696295']['vdevs']['tank']['vdevs']
        assert vdevs['12841765308123764671']['guid'] == '12841765308123764671'

    def test_empty_when_pre_2_3(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version='zfs-2.2.6-1'))
        assert zfs.zfs_pools() == {}

    def test_empty_on_malformed_json(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(outputs={ZPOOL_STATUS_ARGS: '<html>oops'}))
        assert zfs.zfs_pools() == {}

    def test_empty_on_command_failure(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(outputs={ZPOOL_STATUS_ARGS: None}))
        assert zfs.zfs_pools() == {}


class TestZfsDatasets:
    """zfs_datasets() parses `zfs list -j` output, keyed by dataset name."""

    def test_datasets_keyed_by_name(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(outputs={ZFS_LIST_ARGS: _fixture('zfs_list.json')}))
        datasets = zfs.zfs_datasets()
        assert list(datasets.keys()) == ['tank', 'tank/home']

    def test_dataset_property_values(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(outputs={ZFS_LIST_ARGS: _fixture('zfs_list.json')}))
        datasets = zfs.zfs_datasets()
        assert datasets['tank/home']['properties']['used']['value'] == 49152
        assert datasets['tank/home']['properties']['mountpoint']['value'] == '/tank/home'

    def test_empty_when_pre_2_3(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version='zfs-2.2.6-1'))
        assert zfs.zfs_datasets() == {}


class TestRunZfsCommand:
    """_run_zfs_command() wraps subprocess failures instead of raising."""

    def test_returns_stdout_on_success(self, monkeypatch):
        monkeypatch.setattr(
            zfs.subprocess,
            'run',
            lambda *a, **kw: SimpleNamespace(returncode=0, stdout='hello', stderr=''),
        )
        assert zfs._run_zfs_command(['zfs', '--version']) == 'hello'

    def test_returns_none_on_missing_binary(self, monkeypatch):
        def raise_not_found(*a, **kw):
            raise FileNotFoundError('zfs')

        monkeypatch.setattr(zfs.subprocess, 'run', raise_not_found)
        assert zfs._run_zfs_command(['zfs', '--version']) is None

    def test_returns_none_on_nonzero_exit(self, monkeypatch):
        monkeypatch.setattr(
            zfs.subprocess,
            'run',
            lambda *a, **kw: SimpleNamespace(returncode=1, stdout='', stderr='invalid option'),
        )
        assert zfs._run_zfs_command(['zpool', 'status', '-j']) is None

    def test_returns_none_on_timeout(self, monkeypatch):
        def raise_timeout(*a, **kw):
            raise zfs.subprocess.TimeoutExpired(cmd='zfs', timeout=5)

        monkeypatch.setattr(zfs.subprocess, 'run', raise_timeout)
        assert zfs._run_zfs_command(['zpool', 'status', '-j']) is None


class TestZfsPoolsList:
    """zfs_pools_list() parses `zpool list -j` output, keyed by pool GUID."""

    def test_pools_keyed_by_guid(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(outputs={ZPOOL_LIST_ARGS: _fixture('zpool_list.json')}))
        pools = zfs.zfs_pools_list()
        assert list(pools.keys()) == ['3920273586464696295']
        assert pools['3920273586464696295']['name'] == 'tank'

    def test_property_values_are_integers(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(outputs={ZPOOL_LIST_ARGS: _fixture('zpool_list.json')}))
        props = zfs.zfs_pools_list()['3920273586464696295']['properties']
        assert props['size']['value'] == 16492674416640
        assert props['allocated']['value'] == 68812800000
        assert props['capacity']['value'] == 1

    def test_empty_when_pre_2_3(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(version='zfs-2.2.6-1'))
        assert zfs.zfs_pools_list() == {}

    def test_empty_on_command_failure(self, monkeypatch):
        monkeypatch.setattr(zfs, '_run_zfs_command', _runner(outputs={ZPOOL_LIST_ARGS: None}))
        assert zfs.zfs_pools_list() == {}
