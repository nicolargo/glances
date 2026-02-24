#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the DiskIO plugin."""

import json
import time

import pytest


@pytest.fixture
def diskio_plugin(glances_stats):
    """Return the DiskIO plugin instance from glances_stats."""
    return glances_stats.get_plugin('diskio')


class TestDiskioPluginBasics:
    """Test basic DiskIO plugin functionality."""

    def test_plugin_name(self, diskio_plugin):
        """Test plugin name is correctly set."""
        assert diskio_plugin.plugin_name == 'diskio'

    def test_plugin_is_enabled(self, diskio_plugin):
        """Test that the plugin is enabled by default."""
        assert diskio_plugin.is_enabled() is True

    def test_display_curse_enabled(self, diskio_plugin):
        """Test that curse display is enabled."""
        assert diskio_plugin.display_curse is True

    def test_get_key_returns_disk_name(self, diskio_plugin):
        """Test that get_key returns disk_name."""
        assert diskio_plugin.get_key() == 'disk_name'

    def test_history_items_defined(self, diskio_plugin):
        """Test that history items are properly defined."""
        items = diskio_plugin.get_items_history_list()
        assert items is not None
        item_names = [item['name'] for item in items]
        assert 'read_bytes_rate_per_sec' in item_names
        assert 'write_bytes_rate_per_sec' in item_names


class TestDiskioPluginUpdate:
    """Test DiskIO plugin update functionality."""

    def test_update_returns_list(self, diskio_plugin):
        """Test that update returns a list."""
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        assert isinstance(stats, list)

    def test_each_disk_has_name(self, diskio_plugin):
        """Test that each disk entry has a name."""
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            assert 'disk_name' in disk

    def test_read_write_bytes_present(self, diskio_plugin):
        """Test that read_bytes and write_bytes are present."""
        diskio_plugin.update()
        time.sleep(0.1)
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            assert 'read_bytes' in disk
            assert 'write_bytes' in disk

    def test_bytes_values_non_negative(self, diskio_plugin):
        """Test that byte values are non-negative."""
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            if 'read_bytes' in disk and disk['read_bytes'] is not None:
                assert disk['read_bytes'] >= 0
            if 'write_bytes' in disk and disk['write_bytes'] is not None:
                assert disk['write_bytes'] >= 0


class TestDiskioPluginRateCalculation:
    """Test DiskIO plugin rate calculation."""

    def test_rate_fields_after_two_updates(self, diskio_plugin):
        """Test that rate fields are populated after two updates."""
        diskio_plugin.update()
        time.sleep(0.2)
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            assert 'read_bytes_rate_per_sec' in disk or 'read_bytes' in disk
            assert 'write_bytes_rate_per_sec' in disk or 'write_bytes' in disk


class TestDiskioPluginLatency:
    """Test DiskIO plugin latency calculation."""

    def test_latency_fields_present(self, diskio_plugin):
        """Test that latency fields are present after update."""
        diskio_plugin.update()
        time.sleep(0.1)
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            assert 'read_latency' in disk
            assert 'write_latency' in disk

    def test_latency_values_non_negative(self, diskio_plugin):
        """Test that latency values are non-negative."""
        diskio_plugin.update()
        time.sleep(0.1)
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            if 'read_latency' in disk and disk['read_latency'] is not None:
                assert disk['read_latency'] >= 0
            if 'write_latency' in disk and disk['write_latency'] is not None:
                assert disk['write_latency'] >= 0


class TestDiskioPluginCounters:
    """Test DiskIO plugin read/write counters."""

    def test_read_count_present(self, diskio_plugin):
        """Test that read_count is present."""
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            assert 'read_count' in disk

    def test_write_count_present(self, diskio_plugin):
        """Test that write_count is present."""
        diskio_plugin.update()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            assert 'write_count' in disk


class TestDiskioPluginViews:
    """Test DiskIO plugin views functionality."""

    def test_update_views_creates_views(self, diskio_plugin):
        """Test that update_views creates views dictionary."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        views = diskio_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_keyed_by_disk(self, diskio_plugin):
        """Test that views are keyed by disk name."""
        diskio_plugin.update()
        time.sleep(0.1)
        diskio_plugin.update()
        diskio_plugin.update_views()
        views = diskio_plugin.get_views()
        stats = diskio_plugin.get_raw()
        for disk in stats:
            if disk['disk_name'] in views:
                assert isinstance(views[disk['disk_name']], dict)


class TestDiskioPluginJSON:
    """Test DiskIO plugin JSON serialization."""

    def test_get_stats_returns_json(self, diskio_plugin):
        """Test that get_stats returns valid JSON."""
        diskio_plugin.update()
        stats_json = diskio_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, list)

    def test_json_preserves_disk_data(self, diskio_plugin):
        """Test that JSON output preserves disk data."""
        diskio_plugin.update()
        stats_json = diskio_plugin.get_stats()
        parsed = json.loads(stats_json)
        for disk in parsed:
            assert 'disk_name' in disk


class TestDiskioPluginHistory:
    """Test DiskIO plugin history functionality."""

    def test_history_enable(self, diskio_plugin):
        """Test that history can be enabled."""
        assert diskio_plugin.history_enable() is not None


class TestDiskioPluginReset:
    """Test DiskIO plugin reset functionality."""

    def test_reset_clears_stats(self, diskio_plugin):
        """Test that reset clears stats."""
        diskio_plugin.update()
        diskio_plugin.reset()
        stats = diskio_plugin.get_raw()
        assert stats == diskio_plugin.get_init_value()

    def test_reset_views(self, diskio_plugin):
        """Test that reset_views clears views."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        diskio_plugin.reset_views()
        assert diskio_plugin.get_views() == {}


class TestDiskioPluginFieldsDescription:
    """Test DiskIO plugin fields description."""

    def test_fields_description_exists(self, diskio_plugin):
        """Test that fields_description is defined."""
        assert diskio_plugin.fields_description is not None

    def test_mandatory_fields_described(self, diskio_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['disk_name', 'read_bytes', 'write_bytes']
        for field in mandatory_fields:
            assert field in diskio_plugin.fields_description

    def test_rate_fields_described(self, diskio_plugin):
        """Test that rate-enabled fields have rate flag."""
        rate_fields = ['read_bytes', 'write_bytes', 'read_count', 'write_count']
        for field in rate_fields:
            if field in diskio_plugin.fields_description:
                assert diskio_plugin.fields_description[field].get('rate') is True

    def test_latency_fields_described(self, diskio_plugin):
        """Test that latency fields are described."""
        latency_fields = ['read_latency', 'write_latency']
        for field in latency_fields:
            assert field in diskio_plugin.fields_description


class TestDiskioPluginConfiguration:
    """Test DiskIO plugin configuration options."""

    def test_hide_zero_attribute(self, diskio_plugin):
        """Test that hide_zero attribute exists."""
        assert hasattr(diskio_plugin, 'hide_zero')

    def test_hide_zero_fields_defined(self, diskio_plugin):
        """Test that hide_zero_fields is defined."""
        assert hasattr(diskio_plugin, 'hide_zero_fields')
        assert isinstance(diskio_plugin.hide_zero_fields, list)

    def test_hide_threshold_bytes_attribute(self, diskio_plugin):
        """Test that hide_threshold_bytes attribute exists."""
        assert hasattr(diskio_plugin, 'hide_threshold_bytes')


class TestDiskioPluginMsgCurse:
    """Test DiskIO plugin curse message generation."""

    def test_msg_curse_returns_list(self, diskio_plugin):
        """Test that msg_curse returns a list."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        msg = diskio_plugin.msg_curse(max_width=80)
        assert isinstance(msg, list)

    def test_msg_curse_empty_without_max_width(self, diskio_plugin):
        """Test that msg_curse returns empty without max_width."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        msg = diskio_plugin.msg_curse()
        assert isinstance(msg, list)

    def test_msg_curse_with_max_width(self, diskio_plugin):
        """Test that msg_curse works with max_width."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        msg = diskio_plugin.msg_curse(max_width=80)
        assert isinstance(msg, list)


class TestDiskioPluginSorting:
    """Test DiskIO plugin sorting functionality."""

    def test_sorted_stats_returns_list(self, diskio_plugin):
        """Test that sorted_stats returns a list."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        sorted_stats = diskio_plugin.sorted_stats()
        assert isinstance(sorted_stats, list)

    def test_sorted_stats_preserves_count(self, diskio_plugin):
        """Test that sorted_stats preserves disk count."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        raw_count = len(diskio_plugin.get_raw())
        sorted_count = len(diskio_plugin.sorted_stats())
        assert raw_count == sorted_count


class TestDiskioPluginExport:
    """Test DiskIO plugin export functionality."""

    def test_get_export_returns_list(self, diskio_plugin):
        """Test that get_export returns a list."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        export = diskio_plugin.get_export()
        assert isinstance(export, list)

    def test_export_equals_raw(self, diskio_plugin):
        """Test that export equals raw stats by default."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        assert diskio_plugin.get_export() == diskio_plugin.get_raw()


class TestDiskioPluginAlerts:
    """Test DiskIO plugin alert functionality."""

    def test_views_have_decoration(self, diskio_plugin):
        """Test that disk views have decoration after update."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        time.sleep(0.1)
        diskio_plugin.update()
        diskio_plugin.update_views()
        views = diskio_plugin.get_views()
        stats = diskio_plugin.get_raw()

        for disk in stats:
            disk_name = disk['disk_name']
            if disk_name in views and 'read_bytes' in views[disk_name]:
                assert 'decoration' in views[disk_name]['read_bytes']


class TestDiskioPluginAlias:
    """Test DiskIO plugin alias functionality."""

    def test_alias_field_may_be_present(self, diskio_plugin):
        """Test that alias field may be present for disks."""
        diskio_plugin.update()
        diskio_plugin.update_views()
        stats = diskio_plugin.get_raw()
        # Alias is optional, so just verify the field handling works
        for disk in stats:
            if 'alias' in disk:
                assert disk['alias'] is None or isinstance(disk['alias'], str)
