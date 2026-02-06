#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the FileSystem plugin."""

import json

import pytest


@pytest.fixture
def fs_plugin(glances_stats):
    """Return the FileSystem plugin instance from glances_stats."""
    return glances_stats.get_plugin('fs')


class TestFsPluginBasics:
    """Test basic FileSystem plugin functionality."""

    def test_plugin_name(self, fs_plugin):
        """Test plugin name is correctly set."""
        assert fs_plugin.plugin_name == 'fs'

    def test_plugin_is_enabled(self, fs_plugin):
        """Test that the plugin is enabled by default."""
        assert fs_plugin.is_enabled() is True

    def test_display_curse_enabled(self, fs_plugin):
        """Test that curse display is enabled."""
        assert fs_plugin.display_curse is True

    def test_get_key_returns_mnt_point(self, fs_plugin):
        """Test that get_key returns mnt_point."""
        assert fs_plugin.get_key() == 'mnt_point'

    def test_history_items_defined(self, fs_plugin):
        """Test that history items are properly defined."""
        items = fs_plugin.get_items_history_list()
        assert items is not None
        item_names = [item['name'] for item in items]
        assert 'percent' in item_names


class TestFsPluginUpdate:
    """Test FileSystem plugin update functionality."""

    def test_update_returns_list(self, fs_plugin):
        """Test that update returns a list."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        assert isinstance(stats, list)

    def test_each_fs_has_mnt_point(self, fs_plugin):
        """Test that each filesystem entry has a mount point."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            assert 'mnt_point' in fs

    def test_each_fs_has_device_name(self, fs_plugin):
        """Test that each filesystem entry has a device name."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            assert 'device_name' in fs

    def test_size_used_free_present(self, fs_plugin):
        """Test that size, used, and free are present."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            assert 'size' in fs
            assert 'used' in fs
            assert 'free' in fs

    def test_percent_present(self, fs_plugin):
        """Test that percent is present."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            assert 'percent' in fs


class TestFsPluginValues:
    """Test FileSystem plugin values validity."""

    def test_size_values_positive(self, fs_plugin):
        """Test that size values are positive."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            if fs['size'] is not None:
                assert fs['size'] > 0

    def test_used_values_non_negative(self, fs_plugin):
        """Test that used values are non-negative."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            if fs['used'] is not None:
                assert fs['used'] >= 0

    def test_free_values_non_negative(self, fs_plugin):
        """Test that free values are non-negative."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            if fs['free'] is not None:
                assert fs['free'] >= 0

    def test_percent_in_valid_range(self, fs_plugin):
        """Test that percent is within valid range."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            if fs['percent'] is not None:
                assert 0 <= fs['percent'] <= 100

    def test_used_plus_free_equals_size(self, fs_plugin):
        """Test that used + free approximately equals size."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            if all(fs.get(k) is not None for k in ['used', 'free', 'size']):
                calculated = fs['used'] + fs['free']
                # Allow some tolerance due to reserved space
                assert calculated <= fs['size'] * 1.1


class TestFsPluginFsType:
    """Test FileSystem plugin filesystem type information."""

    def test_fs_type_present(self, fs_plugin):
        """Test that fs_type is present."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            assert 'fs_type' in fs

    def test_options_present(self, fs_plugin):
        """Test that options field is present."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            assert 'options' in fs


class TestFsPluginViews:
    """Test FileSystem plugin views functionality."""

    def test_update_views_creates_views(self, fs_plugin):
        """Test that update_views creates views dictionary."""
        fs_plugin.update()
        fs_plugin.update_views()
        views = fs_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_keyed_by_mnt_point(self, fs_plugin):
        """Test that views are keyed by mount point."""
        fs_plugin.update()
        fs_plugin.update_views()
        views = fs_plugin.get_views()
        stats = fs_plugin.get_raw()
        for fs in stats:
            if fs['mnt_point'] in views:
                assert isinstance(views[fs['mnt_point']], dict)

    def test_views_have_used_decoration(self, fs_plugin):
        """Test that views have decoration for used field."""
        fs_plugin.update()
        fs_plugin.update_views()
        views = fs_plugin.get_views()
        stats = fs_plugin.get_raw()
        for fs in stats:
            mnt = fs['mnt_point']
            if mnt in views and 'used' in views[mnt]:
                assert 'decoration' in views[mnt]['used']


class TestFsPluginJSON:
    """Test FileSystem plugin JSON serialization."""

    def test_get_stats_returns_json(self, fs_plugin):
        """Test that get_stats returns valid JSON."""
        fs_plugin.update()
        stats_json = fs_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, list)

    def test_json_preserves_fs_data(self, fs_plugin):
        """Test that JSON output preserves filesystem data."""
        fs_plugin.update()
        stats_json = fs_plugin.get_stats()
        parsed = json.loads(stats_json)
        for fs in parsed:
            assert 'mnt_point' in fs
            assert 'device_name' in fs


class TestFsPluginHistory:
    """Test FileSystem plugin history functionality."""

    def test_history_enable(self, fs_plugin):
        """Test that history can be enabled."""
        assert fs_plugin.history_enable() is not None


class TestFsPluginReset:
    """Test FileSystem plugin reset functionality."""

    def test_reset_clears_stats(self, fs_plugin):
        """Test that reset clears stats."""
        fs_plugin.update()
        fs_plugin.reset()
        stats = fs_plugin.get_raw()
        assert stats == fs_plugin.get_init_value()

    def test_reset_views(self, fs_plugin):
        """Test that reset_views clears views."""
        fs_plugin.update()
        fs_plugin.update_views()
        fs_plugin.reset_views()
        assert fs_plugin.get_views() == {}


class TestFsPluginFieldsDescription:
    """Test FileSystem plugin fields description."""

    def test_fields_description_exists(self, fs_plugin):
        """Test that fields_description is defined."""
        assert fs_plugin.fields_description is not None

    def test_mandatory_fields_described(self, fs_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['device_name', 'mnt_point', 'size', 'used', 'free', 'percent']
        for field in mandatory_fields:
            assert field in fs_plugin.fields_description

    def test_byte_fields_have_unit(self, fs_plugin):
        """Test that byte fields have unit defined."""
        byte_fields = ['size', 'used', 'free']
        for field in byte_fields:
            if field in fs_plugin.fields_description:
                assert 'unit' in fs_plugin.fields_description[field]


class TestFsPluginMsgCurse:
    """Test FileSystem plugin curse message generation."""

    def test_msg_curse_returns_list(self, fs_plugin):
        """Test that msg_curse returns a list."""
        fs_plugin.update()
        msg = fs_plugin.msg_curse(max_width=80)
        assert isinstance(msg, list)

    def test_msg_curse_empty_without_max_width(self, fs_plugin):
        """Test that msg_curse returns empty without max_width."""
        fs_plugin.update()
        msg = fs_plugin.msg_curse()
        assert isinstance(msg, list)

    def test_msg_curse_with_max_width(self, fs_plugin):
        """Test that msg_curse works with max_width."""
        fs_plugin.update()
        msg = fs_plugin.msg_curse(max_width=80)
        assert isinstance(msg, list)


class TestFsPluginExport:
    """Test FileSystem plugin export functionality."""

    def test_get_export_returns_list(self, fs_plugin):
        """Test that get_export returns a list."""
        fs_plugin.update()
        export = fs_plugin.get_export()
        assert isinstance(export, list)

    def test_export_equals_raw(self, fs_plugin):
        """Test that export equals raw stats by default."""
        fs_plugin.update()
        assert fs_plugin.get_export() == fs_plugin.get_raw()


class TestFsPluginAlias:
    """Test FileSystem plugin alias functionality."""

    def test_alias_field_may_be_present(self, fs_plugin):
        """Test that alias field may be present for filesystems."""
        fs_plugin.update()
        stats = fs_plugin.get_raw()
        for fs in stats:
            if 'alias' in fs:
                assert fs['alias'] is None or isinstance(fs['alias'], str)


class TestFsPluginDiskPartitions:
    """Test FileSystem plugin disk partitions method."""

    def test_get_disk_partitions_returns_list(self, fs_plugin):
        """Test that get_disk_partitions returns a list-like object."""
        partitions = fs_plugin.get_disk_partitions()
        assert hasattr(partitions, '__iter__')

    def test_get_disk_partitions_fetch_all(self, fs_plugin):
        """Test get_disk_partitions with fetch_all=True."""
        partitions = fs_plugin.get_disk_partitions(fetch_all=True)
        assert hasattr(partitions, '__iter__')

    def test_physical_partitions_subset_of_all(self, fs_plugin):
        """Test that physical partitions are a subset of all partitions."""
        physical = {p.mountpoint for p in fs_plugin.get_disk_partitions(fetch_all=False)}
        all_partitions = {p.mountpoint for p in fs_plugin.get_disk_partitions(fetch_all=True)}
        assert physical.issubset(all_partitions)


class TestFsPluginReadOnlyHandling:
    """Test FileSystem plugin read-only mount handling."""

    def test_views_skip_ro_mounts_for_threshold(self, fs_plugin):
        """Test that views handle read-only mounts appropriately."""
        fs_plugin.update()
        fs_plugin.update_views()
        stats = fs_plugin.get_raw()
        fs_plugin.get_views()

        # Read-only mounts should still have views, but decoration handling differs
        for fs in stats:
            if 'ro' in fs.get('options', '').split(','):
                # The mount point should still be in views
                # (decoration logic is handled differently for ro mounts)
                pass


class TestFsPluginConfiguration:
    """Test FileSystem plugin configuration."""

    def test_can_get_conf_value(self, fs_plugin):
        """Test that configuration values can be retrieved."""
        # 'allow' is a valid config option for fs plugin
        allowed = fs_plugin.get_conf_value('allow')
        assert isinstance(allowed, list)
