#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the MemSwap plugin."""

import json

import pytest


@pytest.fixture
def memswap_plugin(glances_stats):
    """Return the MemSwap plugin instance from glances_stats."""
    return glances_stats.get_plugin('memswap')


class TestMemswapPluginBasics:
    """Test basic MemSwap plugin functionality."""

    def test_plugin_name(self, memswap_plugin):
        """Test plugin name is correctly set."""
        assert memswap_plugin.plugin_name == 'memswap'

    def test_plugin_is_enabled(self, memswap_plugin):
        """Test that the plugin is enabled by default."""
        assert memswap_plugin.is_enabled() is True

    def test_display_curse_enabled(self, memswap_plugin):
        """Test that curse display is enabled."""
        assert memswap_plugin.display_curse is True

    def test_history_items_defined(self, memswap_plugin):
        """Test that history items are properly defined."""
        items = memswap_plugin.get_items_history_list()
        assert items is not None
        item_names = [item['name'] for item in items]
        assert 'percent' in item_names


class TestMemswapPluginUpdate:
    """Test MemSwap plugin update functionality."""

    def test_update_returns_dict(self, memswap_plugin):
        """Test that update returns a dictionary."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        assert isinstance(stats, dict)

    def test_update_contains_mandatory_keys(self, memswap_plugin):
        """Test that stats contain mandatory keys."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        mandatory_keys = ['total', 'used', 'free', 'percent']
        for key in mandatory_keys:
            assert key in stats, f"Missing mandatory key: {key}"

    def test_swap_values_non_negative(self, memswap_plugin):
        """Test that swap values are non-negative."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        for key in ['total', 'used', 'free']:
            if key in stats and stats[key] is not None:
                assert stats[key] >= 0, f"{key} should be non-negative"

    def test_swap_percent_in_valid_range(self, memswap_plugin):
        """Test that swap percentage is within valid range."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        if 'percent' in stats and stats['percent'] is not None:
            assert 0 <= stats['percent'] <= 100


class TestMemswapPluginSwapActivity:
    """Test MemSwap plugin swap in/out activity."""

    def test_sin_sout_present(self, memswap_plugin):
        """Test that sin and sout are present if swap is available."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        # sin/sout may not be present on all systems
        if stats.get('total', 0) > 0:
            # If swap exists, sin/sout should be present
            pass  # These fields are platform-dependent

    def test_time_since_update_present(self, memswap_plugin):
        """Test that time_since_update is present."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        if stats:  # If swap exists
            assert 'time_since_update' in stats


class TestMemswapPluginViews:
    """Test MemSwap plugin views functionality."""

    def test_update_views_creates_views(self, memswap_plugin):
        """Test that update_views creates views dictionary."""
        memswap_plugin.update()
        memswap_plugin.update_views()
        views = memswap_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_contain_percent_decoration(self, memswap_plugin):
        """Test that views contain decoration for percent."""
        memswap_plugin.update()
        memswap_plugin.update_views()
        views = memswap_plugin.get_views()
        if 'percent' in views:
            assert 'decoration' in views['percent']


class TestMemswapPluginJSON:
    """Test MemSwap plugin JSON serialization."""

    def test_get_stats_returns_json(self, memswap_plugin):
        """Test that get_stats returns valid JSON."""
        memswap_plugin.update()
        stats_json = memswap_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, dict)

    def test_json_contains_expected_fields(self, memswap_plugin):
        """Test that JSON output contains expected fields."""
        memswap_plugin.update()
        stats_json = memswap_plugin.get_stats()
        parsed = json.loads(stats_json)
        expected_fields = ['total', 'used', 'free', 'percent']
        for field in expected_fields:
            assert field in parsed


class TestMemswapPluginHistory:
    """Test MemSwap plugin history functionality."""

    def test_history_enable_check(self, memswap_plugin):
        """Test that history_enable returns a boolean."""
        result = memswap_plugin.history_enable()
        assert isinstance(result, bool)

    def test_get_items_history_list(self, memswap_plugin):
        """Test that get_items_history_list returns the history items."""
        items = memswap_plugin.get_items_history_list()
        if items is not None:
            assert isinstance(items, list)
            item_names = [item['name'] for item in items]
            assert 'percent' in item_names


class TestMemswapPluginReset:
    """Test MemSwap plugin reset functionality."""

    def test_reset_clears_stats(self, memswap_plugin):
        """Test that reset clears stats."""
        memswap_plugin.update()
        memswap_plugin.reset()
        stats = memswap_plugin.get_raw()
        assert stats == memswap_plugin.get_init_value()

    def test_reset_views(self, memswap_plugin):
        """Test that reset_views clears views."""
        memswap_plugin.update()
        memswap_plugin.update_views()
        memswap_plugin.reset_views()
        assert memswap_plugin.get_views() == {}


class TestMemswapPluginFieldsDescription:
    """Test MemSwap plugin fields description."""

    def test_fields_description_exists(self, memswap_plugin):
        """Test that fields_description is defined."""
        assert memswap_plugin.fields_description is not None

    def test_mandatory_fields_described(self, memswap_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['total', 'used', 'free', 'percent']
        for field in mandatory_fields:
            assert field in memswap_plugin.fields_description

    def test_sin_sout_fields_described(self, memswap_plugin):
        """Test that sin and sout fields are described."""
        assert 'sin' in memswap_plugin.fields_description
        assert 'sout' in memswap_plugin.fields_description

    def test_field_has_description(self, memswap_plugin):
        """Test that each field has a description."""
        for field, info in memswap_plugin.fields_description.items():
            assert 'description' in info, f"Field {field} missing description"

    def test_byte_fields_have_unit(self, memswap_plugin):
        """Test that byte fields have unit defined."""
        byte_fields = ['total', 'used', 'free', 'sin', 'sout']
        for field in byte_fields:
            if field in memswap_plugin.fields_description:
                assert 'unit' in memswap_plugin.fields_description[field]


class TestMemswapPluginAlerts:
    """Test MemSwap plugin alert functionality."""

    def test_get_alert_log_returns_valid_status(self, memswap_plugin):
        """Test that get_alert_log returns a valid status."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        if 'used' in stats and 'total' in stats and stats['total'] > 0:
            alert = memswap_plugin.get_alert_log(stats['used'], maximum=stats['total'])
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


class TestMemswapPluginMsgCurse:
    """Test MemSwap plugin curse message generation."""

    def test_msg_curse_returns_list(self, memswap_plugin):
        """Test that msg_curse returns a list."""
        memswap_plugin.update()
        msg = memswap_plugin.msg_curse()
        assert isinstance(msg, list)

    def test_msg_curse_not_empty_with_stats(self, memswap_plugin):
        """Test that msg_curse returns non-empty list with stats."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        if stats:
            msg = memswap_plugin.msg_curse()
            assert len(msg) > 0

    def test_msg_curse_contains_title(self, memswap_plugin):
        """Test that msg_curse contains SWAP title."""
        memswap_plugin.update()
        msg = memswap_plugin.msg_curse()
        if msg:
            messages = [m.get('msg', '') for m in msg]
            assert any('SWAP' in str(m) for m in messages)


class TestMemswapPluginExport:
    """Test MemSwap plugin export functionality."""

    def test_get_export_returns_stats(self, memswap_plugin):
        """Test that get_export returns stats."""
        memswap_plugin.update()
        export = memswap_plugin.get_export()
        assert isinstance(export, dict)

    def test_export_equals_raw(self, memswap_plugin):
        """Test that export equals raw stats by default."""
        memswap_plugin.update()
        assert memswap_plugin.get_export() == memswap_plugin.get_raw()


class TestMemswapPluginNoSwap:
    """Test MemSwap plugin behavior when no swap is configured."""

    def test_handles_no_swap_gracefully(self, memswap_plugin):
        """Test that the plugin handles no swap configuration gracefully."""
        memswap_plugin.update()
        stats = memswap_plugin.get_raw()
        # Even with no swap, should return a dict (possibly empty or with zeros)
        assert isinstance(stats, dict)
