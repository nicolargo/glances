#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the ProcessCount plugin."""

import json

import pytest


@pytest.fixture
def processcount_plugin(glances_stats):
    """Return the ProcessCount plugin instance from glances_stats."""
    return glances_stats.get_plugin('processcount')


class TestProcesscountPluginBasics:
    """Test basic ProcessCount plugin functionality."""

    def test_plugin_name(self, processcount_plugin):
        """Test plugin name is correctly set."""
        assert processcount_plugin.plugin_name == 'processcount'

    def test_plugin_is_enabled(self, processcount_plugin):
        """Test that the plugin is enabled by default."""
        assert processcount_plugin.is_enabled() is True

    def test_display_curse_enabled(self, processcount_plugin):
        """Test that curse display is enabled."""
        assert processcount_plugin.display_curse is True

    def test_history_items_defined(self, processcount_plugin):
        """Test that history items are properly defined."""
        items = processcount_plugin.get_items_history_list()
        assert items is not None
        item_names = [item['name'] for item in items]
        assert 'total' in item_names
        assert 'running' in item_names


class TestProcesscountPluginUpdate:
    """Test ProcessCount plugin update functionality."""

    def test_update_returns_dict(self, processcount_plugin):
        """Test that update returns a dictionary."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        assert isinstance(stats, dict)

    def test_update_contains_total(self, processcount_plugin):
        """Test that stats contain total count."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        assert 'total' in stats

    def test_total_positive(self, processcount_plugin):
        """Test that total process count is positive."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        assert stats['total'] > 0

    def test_running_present(self, processcount_plugin):
        """Test that running count is present."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        assert 'running' in stats

    def test_sleeping_present(self, processcount_plugin):
        """Test that sleeping count is present."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        assert 'sleeping' in stats

    def test_thread_count_present(self, processcount_plugin):
        """Test that thread count is present."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        assert 'thread' in stats


class TestProcesscountPluginValues:
    """Test ProcessCount plugin values validity."""

    def test_counts_non_negative(self, processcount_plugin):
        """Test that all counts are non-negative."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        count_keys = ['total', 'running', 'sleeping', 'thread']
        for key in count_keys:
            if key in stats:
                assert stats[key] >= 0

    def test_running_sleeping_less_than_total(self, processcount_plugin):
        """Test that running + sleeping <= total."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        if all(k in stats for k in ['running', 'sleeping', 'total']):
            assert stats['running'] + stats['sleeping'] <= stats['total']

    def test_thread_count_reasonable(self, processcount_plugin):
        """Test that thread count is reasonable."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        if 'thread' in stats and 'total' in stats:
            # Thread count should be >= process count
            assert stats['thread'] >= stats['total']


class TestProcesscountPluginViews:
    """Test ProcessCount plugin views functionality."""

    def test_update_views_returns_dict(self, processcount_plugin):
        """Test that update_views returns a dictionary."""
        processcount_plugin.update()
        views = processcount_plugin.update_views()
        assert isinstance(views, dict)


class TestProcesscountPluginJSON:
    """Test ProcessCount plugin JSON serialization."""

    def test_get_stats_returns_json(self, processcount_plugin):
        """Test that get_stats returns valid JSON."""
        processcount_plugin.update()
        stats_json = processcount_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, dict)

    def test_json_contains_expected_fields(self, processcount_plugin):
        """Test that JSON output contains expected fields."""
        processcount_plugin.update()
        stats_json = processcount_plugin.get_stats()
        parsed = json.loads(stats_json)
        expected_fields = ['total', 'running', 'sleeping', 'thread']
        for field in expected_fields:
            assert field in parsed


class TestProcesscountPluginHistory:
    """Test ProcessCount plugin history functionality."""

    def test_history_enable_check(self, processcount_plugin):
        """Test that history_enable returns a boolean."""
        result = processcount_plugin.history_enable()
        assert isinstance(result, bool)

    def test_get_items_history_list(self, processcount_plugin):
        """Test that get_items_history_list returns the history items."""
        items = processcount_plugin.get_items_history_list()
        if items is not None:
            assert isinstance(items, list)
            item_names = [item['name'] for item in items]
            assert 'total' in item_names


class TestProcesscountPluginReset:
    """Test ProcessCount plugin reset functionality."""

    def test_reset_clears_stats(self, processcount_plugin):
        """Test that reset clears stats."""
        processcount_plugin.update()
        processcount_plugin.reset()
        stats = processcount_plugin.get_raw()
        assert stats == processcount_plugin.get_init_value()

    def test_reset_views(self, processcount_plugin):
        """Test that reset_views clears views."""
        processcount_plugin.update()
        processcount_plugin.update_views()
        processcount_plugin.reset_views()
        assert processcount_plugin.get_views() == {}


class TestProcesscountPluginFieldsDescription:
    """Test ProcessCount plugin fields description."""

    def test_fields_description_exists(self, processcount_plugin):
        """Test that fields_description is defined."""
        assert processcount_plugin.fields_description is not None

    def test_mandatory_fields_described(self, processcount_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['total', 'running', 'sleeping', 'thread']
        for field in mandatory_fields:
            assert field in processcount_plugin.fields_description

    def test_field_has_description(self, processcount_plugin):
        """Test that each field has a description."""
        for field, info in processcount_plugin.fields_description.items():
            assert 'description' in info, f"Field {field} missing description"

    def test_field_has_unit(self, processcount_plugin):
        """Test that fields have unit defined."""
        for field, info in processcount_plugin.fields_description.items():
            assert 'unit' in info, f"Field {field} missing unit"


class TestProcesscountPluginMsgCurse:
    """Test ProcessCount plugin curse message generation."""

    def test_msg_curse_with_args(self, processcount_plugin):
        """Test that msg_curse returns a list when args provided."""
        processcount_plugin.update()
        # msg_curse requires args with disable_process attribute
        if hasattr(processcount_plugin, 'args') and processcount_plugin.args:
            msg = processcount_plugin.msg_curse(args=processcount_plugin.args)
            assert isinstance(msg, list)

    def test_msg_curse_format_with_args(self, processcount_plugin):
        """Test that msg_curse returns properly formatted entries."""
        processcount_plugin.update()
        if hasattr(processcount_plugin, 'args') and processcount_plugin.args:
            msg = processcount_plugin.msg_curse(args=processcount_plugin.args)
            if msg:
                for entry in msg:
                    assert isinstance(entry, dict)
                    assert 'msg' in entry

    def test_msg_curse_content_with_args(self, processcount_plugin):
        """Test msg_curse output content."""
        processcount_plugin.update()
        stats = processcount_plugin.get_raw()
        if stats and hasattr(processcount_plugin, 'args') and processcount_plugin.args:
            if not getattr(processcount_plugin.args, 'disable_process', True):
                msg = processcount_plugin.msg_curse(args=processcount_plugin.args)
                if msg:
                    assert len(msg) > 0


class TestProcesscountPluginExport:
    """Test ProcessCount plugin export functionality."""

    def test_get_export_returns_dict(self, processcount_plugin):
        """Test that get_export returns a dict."""
        processcount_plugin.update()
        export = processcount_plugin.get_export()
        assert isinstance(export, dict)

    def test_export_equals_raw(self, processcount_plugin):
        """Test that export equals raw stats by default."""
        processcount_plugin.update()
        assert processcount_plugin.get_export() == processcount_plugin.get_raw()


class TestProcesscountPluginExtended:
    """Test ProcessCount plugin extended stats functionality."""

    def test_enable_extended_method_exists(self, processcount_plugin):
        """Test that enable_extended method exists."""
        assert hasattr(processcount_plugin, 'enable_extended')
        assert callable(processcount_plugin.enable_extended)

    def test_disable_extended_method_exists(self, processcount_plugin):
        """Test that disable_extended method exists."""
        assert hasattr(processcount_plugin, 'disable_extended')
        assert callable(processcount_plugin.disable_extended)


class TestProcesscountPluginPidMax:
    """Test ProcessCount plugin pid_max field."""

    def test_pid_max_in_fields_description(self, processcount_plugin):
        """Test that pid_max is in fields description."""
        assert 'pid_max' in processcount_plugin.fields_description

    def test_pid_max_description(self, processcount_plugin):
        """Test that pid_max has a description."""
        assert 'description' in processcount_plugin.fields_description['pid_max']
