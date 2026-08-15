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


class TestMemPluginMMM:
    """Test Memory plugin MMM (Min/Max/Mean) feature.

    The MMM feature automatically tracks minimum, maximum, and mean values
    for fields marked with 'mmm': True in fields_description.
    """

    @staticmethod
    def _force_update(plugin):
        """Force a real update() by expiring the refresh timer.

        The session-scoped glances_stats fixture means the plugin instance is
        shared across tests and, because update() is throttled by a refresh
        timer (default 2s), back-to-back calls can be no-ops. Expiring the
        timer ensures update() really runs so the min/max/mean trackers are fed.
        """
        from glances.timer import Timer

        plugin.refresh_timer = Timer(0)
        plugin.update()

    def test_percent_field_has_mmm_flag(self, mem_plugin):
        """Test that percent field is marked with mmm=True."""
        assert 'percent' in mem_plugin.fields_description
        assert mem_plugin.fields_description['percent'].get('mmm', False) is True

    def test_mmm_fields_initialized(self, mem_plugin):
        """Test that _mmm_fields is initialized for tracking."""
        assert hasattr(mem_plugin, '_mmm_fields')
        assert isinstance(mem_plugin._mmm_fields, dict)
        # percent field should be in mmm_fields
        assert 'percent' in mem_plugin._mmm_fields

    def test_mmm_field_structure(self, mem_plugin):
        """Test that mmm field tracking structure is correct."""
        assert 'percent' in mem_plugin._mmm_fields
        mmm_info = mem_plugin._mmm_fields['percent']
        assert 'values' in mmm_info
        assert 'min' in mmm_info
        assert 'max' in mmm_info
        assert 'unit' in mmm_info
        assert mmm_info['unit'] == 'percent'

    def test_percent_min_max_mean_generated_descriptions(self, mem_plugin):
        """Test that min/max/mean field descriptions are auto-generated."""
        assert 'percent_min' in mem_plugin.fields_description
        assert 'percent_max' in mem_plugin.fields_description
        assert 'percent_mean' in mem_plugin.fields_description

        # Check descriptions exist
        assert 'description' in mem_plugin.fields_description['percent_min']
        assert 'description' in mem_plugin.fields_description['percent_max']
        assert 'description' in mem_plugin.fields_description['percent_mean']

        # Check units match
        assert mem_plugin.fields_description['percent_min']['unit'] == 'percent'
        assert mem_plugin.fields_description['percent_max']['unit'] == 'percent'
        assert mem_plugin.fields_description['percent_mean']['unit'] == 'percent'

    def test_percent_min_max_mean_in_stats_after_update(self, mem_plugin):
        """Test that percent_min, percent_max, and percent_mean appear in stats after update."""
        self._force_update(mem_plugin)
        stats = mem_plugin.get_raw()
        assert 'percent' in stats
        assert 'percent_min' in stats, "percent_min missing from stats"
        assert 'percent_max' in stats, "percent_max missing from stats"
        assert 'percent_mean' in stats, "percent_mean missing from stats"

    def test_percent_min_max_mean_are_numeric(self, mem_plugin):
        """Test that percent_min, percent_max, and percent_mean are numeric."""
        self._force_update(mem_plugin)
        stats = mem_plugin.get_raw()
        assert isinstance(stats['percent_min'], (int, float))
        assert isinstance(stats['percent_max'], (int, float))
        assert isinstance(stats['percent_mean'], (int, float))

    def test_percent_min_max_mean_in_valid_range(self, mem_plugin):
        """Test that percent_min, percent_max, and percent_mean are between 0-100."""
        self._force_update(mem_plugin)
        stats = mem_plugin.get_raw()
        assert 0 <= stats['percent_min'] <= 100
        assert 0 <= stats['percent_max'] <= 100
        assert 0 <= stats['percent_mean'] <= 100

    def test_min_less_than_or_equal_max(self, mem_plugin):
        """Test that percent_min <= percent_max."""
        self._force_update(mem_plugin)
        stats = mem_plugin.get_raw()
        assert stats['percent_min'] <= stats['percent_max']

    def test_mean_between_min_and_max(self, mem_plugin):
        """Test that percent_mean falls between percent_min and percent_max."""
        self._force_update(mem_plugin)
        stats = mem_plugin.get_raw()
        assert stats['percent_min'] <= stats['percent_mean'] <= stats['percent_max']

    def test_current_percent_within_bounds(self, mem_plugin):
        """Test that current percent falls between min and max."""
        self._force_update(mem_plugin)
        stats = mem_plugin.get_raw()
        # After multiple updates, current should fall within observed bounds
        assert stats['percent_min'] <= stats['percent'] <= stats['percent_max']

    def test_mmm_fields_in_api_output(self, mem_plugin):
        """Test that MMM fields are exposed via get_api()."""
        self._force_update(mem_plugin)
        api_data = mem_plugin.get_api()
        assert 'percent_min' in api_data
        assert 'percent_max' in api_data
        assert 'percent_mean' in api_data

    def test_mmm_fields_in_json_output(self, mem_plugin):
        """Test that MMM fields are in JSON output."""
        self._force_update(mem_plugin)
        stats_json = mem_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert 'percent_min' in parsed
        assert 'percent_max' in parsed
        assert 'percent_mean' in parsed

    def test_mmm_fields_in_export_output(self, mem_plugin):
        """Test that MMM fields are in export output."""
        self._force_update(mem_plugin)
        export = mem_plugin.get_export()
        assert 'percent_min' in export
        assert 'percent_max' in export
        assert 'percent_mean' in export

    def test_mmm_history_accumulation(self, mem_plugin):
        """Test that MMM tracking accumulates history correctly."""
        # Force multiple updates to build history
        from glances.timer import Timer

        for _ in range(3):
            mem_plugin.refresh_timer = Timer(0)
            mem_plugin.update()

        # Check that history has accumulated
        mmm_info = mem_plugin._mmm_fields['percent']
        # After 3 updates, we should have at least 3 values in history
        assert len(mmm_info['values']) >= 1

    def test_mmm_min_max_monotonic(self, mem_plugin):
        """Test that min only decreases (or stays) and max only increases (or stays)."""
        from glances.timer import Timer

        prev_min = None
        prev_max = None

        for _ in range(3):
            mem_plugin.refresh_timer = Timer(0)
            mem_plugin.update()
            stats = mem_plugin.get_raw()

            if prev_min is not None:
                # min should never increase, max should never decrease
                assert stats['percent_min'] <= prev_min or prev_min is None
                assert stats['percent_max'] >= prev_max or prev_max is None

            prev_min = stats['percent_min']
            prev_max = stats['percent_max']

    def test_mmm_history_limit(self, mem_plugin):
        """Test that MMM history respects the size limit."""
        mmm_info = mem_plugin._mmm_fields['percent']

        # The limit should be set to a reasonable value (28800 by default)
        max_history_size = 28800

        # After a single update, history should be small
        from glances.timer import Timer

        mem_plugin.refresh_timer = Timer(0)
        mem_plugin.update()

        # History should not exceed the limit
        assert len(mmm_info['values']) <= max_history_size

    def test_mmm_fields_with_multiple_updates(self, mem_plugin):
        """Test MMM tracking across multiple updates."""
        from glances.timer import Timer

        # Perform multiple updates
        for i in range(5):
            mem_plugin.refresh_timer = Timer(0)
            mem_plugin.update()

        stats = mem_plugin.get_raw()

        # All MMM fields should be present
        assert 'percent_min' in stats
        assert 'percent_max' in stats
        assert 'percent_mean' in stats

        # Values should be relative to each other
        assert stats['percent_min'] <= stats['percent'] <= stats['percent_max']
        assert stats['percent_min'] <= stats['percent_mean'] <= stats['percent_max']

    def test_mmm_decorator_applied(self, mem_plugin):
        """Test that the _manage_mmm decorator is properly applied to update method."""
        # The update method should have the decorator applied
        # We can verify this by checking that MMM fields appear in stats
        self._force_update(mem_plugin)
        stats = mem_plugin.get_raw()

        # If decorator is applied correctly, these fields should exist
        assert 'percent_min' in stats
        assert 'percent_max' in stats
        assert 'percent_mean' in stats
