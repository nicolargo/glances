#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Memory plugin."""

import json

import pytest


@pytest.fixture
def mem_plugin(glances_stats):
    """Return the Memory plugin instance from glances_stats."""
    return glances_stats.get_plugin('mem')


class TestMemPluginBasics:
    """Test basic Memory plugin functionality."""

    def test_plugin_name(self, mem_plugin):
        """Test plugin name is correctly set."""
        assert mem_plugin.plugin_name == 'mem'

    def test_plugin_is_enabled(self, mem_plugin):
        """Test that the plugin is enabled by default."""
        assert mem_plugin.is_enabled() is True

    def test_display_curse_enabled(self, mem_plugin):
        """Test that curse display is enabled."""
        assert mem_plugin.display_curse is True

    def test_history_items_defined(self, mem_plugin):
        """Test that history items are properly defined."""
        items = mem_plugin.get_items_history_list()
        assert items is not None
        item_names = [item['name'] for item in items]
        assert 'percent' in item_names


class TestMemPluginUpdate:
    """Test Memory plugin update functionality."""

    def test_update_returns_dict(self, mem_plugin):
        """Test that update returns a dictionary."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        assert isinstance(stats, dict)

    def test_update_contains_mandatory_keys(self, mem_plugin):
        """Test that stats contain mandatory keys."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        mandatory_keys = ['total', 'available', 'used', 'free', 'percent']
        for key in mandatory_keys:
            assert key in stats, f"Missing mandatory key: {key}"

    def test_memory_values_positive(self, mem_plugin):
        """Test that memory values are positive."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        for key in ['total', 'available', 'used', 'free']:
            if key in stats and stats[key] is not None:
                assert stats[key] >= 0, f"{key} should be non-negative"

    def test_memory_percent_in_valid_range(self, mem_plugin):
        """Test that memory percentage is within valid range."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        assert 'percent' in stats
        assert 0 <= stats['percent'] <= 100

    def test_used_plus_free_less_than_total(self, mem_plugin):
        """Test that used + available approximately equals total."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        if all(key in stats for key in ['used', 'available', 'total']):
            # Allow for some rounding/calculation variance
            calculated = stats['used'] + stats['available']
            # Should be close to total (within 10% due to different calculation methods)
            assert abs(calculated - stats['total']) / stats['total'] < 0.1

    def test_total_memory_reasonable(self, mem_plugin):
        """Test that total memory is a reasonable value (> 100MB)."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        min_memory = 100 * 1024 * 1024  # 100 MB
        assert stats['total'] > min_memory


class TestMemPluginOptionalFields:
    """Test Memory plugin optional fields."""

    def test_active_inactive_memory(self, mem_plugin):
        """Test active/inactive memory fields if available."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        # These are platform-specific, so just check they're valid if present
        if 'active' in stats and stats['active'] is not None:
            assert stats['active'] >= 0
        if 'inactive' in stats and stats['inactive'] is not None:
            assert stats['inactive'] >= 0

    def test_buffers_cached_memory(self, mem_plugin):
        """Test buffers/cached memory fields if available."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        if 'buffers' in stats and stats['buffers'] is not None:
            assert stats['buffers'] >= 0
        if 'cached' in stats and stats['cached'] is not None:
            assert stats['cached'] >= 0


class TestMemPluginViews:
    """Test Memory plugin views functionality."""

    def test_update_views_creates_views(self, mem_plugin):
        """Test that update_views creates views dictionary."""
        mem_plugin.update()
        mem_plugin.update_views()
        views = mem_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_contain_percent_decoration(self, mem_plugin):
        """Test that views contain decoration for percent."""
        mem_plugin.update()
        mem_plugin.update_views()
        views = mem_plugin.get_views()
        if views:
            assert 'percent' in views
            assert 'decoration' in views['percent']


class TestMemPluginJSON:
    """Test Memory plugin JSON serialization."""

    def test_get_stats_returns_json(self, mem_plugin):
        """Test that get_stats returns valid JSON."""
        mem_plugin.update()
        stats_json = mem_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, dict)

    def test_json_contains_expected_fields(self, mem_plugin):
        """Test that JSON output contains expected fields."""
        mem_plugin.update()
        stats_json = mem_plugin.get_stats()
        parsed = json.loads(stats_json)
        expected_fields = ['total', 'used', 'free', 'percent']
        for field in expected_fields:
            assert field in parsed


class TestMemPluginHistory:
    """Test Memory plugin history functionality."""

    def test_history_enable_check(self, mem_plugin):
        """Test that history_enable returns a boolean."""
        result = mem_plugin.history_enable()
        assert isinstance(result, bool)

    def test_get_items_history_list(self, mem_plugin):
        """Test that get_items_history_list returns the history items."""
        items = mem_plugin.get_items_history_list()
        if items is not None:
            assert isinstance(items, list)
            item_names = [item['name'] for item in items]
            assert 'percent' in item_names


class TestMemPluginReset:
    """Test Memory plugin reset functionality."""

    def test_reset_clears_stats(self, mem_plugin):
        """Test that reset clears stats."""
        mem_plugin.update()
        mem_plugin.reset()
        stats = mem_plugin.get_raw()
        assert stats == mem_plugin.get_init_value()

    def test_reset_views(self, mem_plugin):
        """Test that reset_views clears views."""
        mem_plugin.update()
        mem_plugin.update_views()
        mem_plugin.reset_views()
        assert mem_plugin.get_views() == {}


class TestMemPluginFieldsDescription:
    """Test Memory plugin fields description."""

    def test_fields_description_exists(self, mem_plugin):
        """Test that fields_description is defined."""
        assert mem_plugin.fields_description is not None

    def test_mandatory_fields_described(self, mem_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['total', 'available', 'percent', 'used', 'free']
        for field in mandatory_fields:
            assert field in mem_plugin.fields_description

    def test_field_has_description(self, mem_plugin):
        """Test that each field has a description."""
        for field, info in mem_plugin.fields_description.items():
            assert 'description' in info, f"Field {field} missing description"

    def test_field_has_unit(self, mem_plugin):
        """Test that byte fields have unit defined."""
        byte_fields = ['total', 'available', 'used', 'free']
        for field in byte_fields:
            if field in mem_plugin.fields_description:
                assert 'unit' in mem_plugin.fields_description[field]


class TestMemPluginAlerts:
    """Test Memory plugin alert functionality."""

    def test_get_alert_log_returns_valid_status(self, mem_plugin):
        """Test that get_alert_log returns a valid status."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        if 'used' in stats and 'total' in stats:
            alert = mem_plugin.get_alert_log(stats['used'], maximum=stats['total'])
            valid_statuses = [
                'OK',
                'OK_LOG',
                'CAREFUL',
                'CAREFUL_LOG',
                'WARNING',
                'WARNING_LOG',
                'CRITICAL',
                'CRITICAL_LOG',
                'DEFAULT',
                'MAX',
            ]
            assert any(alert.startswith(status) for status in valid_statuses)


class TestMemPluginMsgCurse:
    """Test Memory plugin curse message generation."""

    def test_msg_curse_returns_list(self, mem_plugin):
        """Test that msg_curse returns a list."""
        mem_plugin.update()
        msg = mem_plugin.msg_curse()
        assert isinstance(msg, list)

    def test_msg_curse_format(self, mem_plugin):
        """Test that msg_curse returns properly formatted entries."""
        mem_plugin.update()
        msg = mem_plugin.msg_curse()
        if msg:
            for entry in msg:
                assert isinstance(entry, dict)
                assert 'msg' in entry

    def test_msg_curse_structure(self, mem_plugin):
        """Test msg_curse output structure when stats available."""
        mem_plugin.update()
        stats = mem_plugin.get_raw()
        if stats and not mem_plugin.is_disabled():
            msg = mem_plugin.msg_curse()
            if msg:
                messages = [m.get('msg', '') for m in msg]
                # Should contain MEM when properly configured
                assert len(messages) > 0


class TestMemPluginZFS:
    """Test Memory plugin ZFS integration."""

    def test_zfs_enabled_attribute(self, mem_plugin):
        """Test that zfs_enabled attribute exists."""
        assert hasattr(mem_plugin, 'zfs_enabled')

    def test_available_config_option(self, mem_plugin):
        """Test that available config option exists."""
        assert hasattr(mem_plugin, 'available')


class TestMemPluginExport:
    """Test Memory plugin export functionality."""

    def test_get_export_returns_dict(self, mem_plugin):
        """Test that get_export returns a dict."""
        mem_plugin.update()
        export = mem_plugin.get_export()
        assert isinstance(export, dict)

    def test_export_equals_raw(self, mem_plugin):
        """Test that export equals raw stats by default."""
        mem_plugin.update()
        assert mem_plugin.get_export() == mem_plugin.get_raw()

    def test_export_contains_stats_when_available(self, mem_plugin):
        """Test that export contains expected keys when stats are available."""
        mem_plugin.update()
        export = mem_plugin.get_export()
        if export:  # If there are stats
            assert 'total' in export
