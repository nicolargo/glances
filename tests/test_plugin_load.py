#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Load plugin."""

import json

import pytest

from glances.globals import WINDOWS
from glances.plugins.load import load_average, log_core, phys_core


@pytest.fixture
def load_plugin(glances_stats):
    """Return the Load plugin instance from glances_stats."""
    return glances_stats.get_plugin('load')


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginBasics:
    """Test basic Load plugin functionality."""

    def test_plugin_name(self, load_plugin):
        """Test plugin name is correctly set."""
        assert load_plugin.plugin_name == 'load'

    def test_plugin_is_enabled(self, load_plugin):
        """Test that the plugin is enabled by default."""
        assert load_plugin.is_enabled() is True

    def test_display_curse_enabled(self, load_plugin):
        """Test that curse display is enabled."""
        assert load_plugin.display_curse is True

    def test_history_items_defined(self, load_plugin):
        """Test that history items are properly defined."""
        items = load_plugin.get_items_history_list()
        assert items is not None
        item_names = [item['name'] for item in items]
        assert 'min1' in item_names
        assert 'min5' in item_names
        assert 'min15' in item_names


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginUpdate:
    """Test Load plugin update functionality."""

    def test_update_returns_dict(self, load_plugin):
        """Test that update returns a dictionary."""
        load_plugin.update()
        stats = load_plugin.get_raw()
        assert isinstance(stats, dict)

    def test_update_contains_mandatory_keys(self, load_plugin):
        """Test that stats contain mandatory keys."""
        load_plugin.update()
        stats = load_plugin.get_raw()
        mandatory_keys = ['min1', 'min5', 'min15', 'cpucore']
        for key in mandatory_keys:
            assert key in stats, f"Missing mandatory key: {key}"

    def test_load_values_non_negative(self, load_plugin):
        """Test that load values are non-negative."""
        load_plugin.update()
        stats = load_plugin.get_raw()
        for key in ['min1', 'min5', 'min15']:
            if key in stats and stats[key] is not None:
                assert stats[key] >= 0, f"{key} should be non-negative"

    def test_cpucore_positive(self, load_plugin):
        """Test that CPU core count is positive."""
        load_plugin.update()
        stats = load_plugin.get_raw()
        assert 'cpucore' in stats
        assert stats['cpucore'] >= 1


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginViews:
    """Test Load plugin views functionality."""

    def test_update_views_creates_views(self, load_plugin):
        """Test that update_views creates views dictionary."""
        load_plugin.update()
        load_plugin.update_views()
        views = load_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_contain_min15_decoration(self, load_plugin):
        """Test that views contain decoration for min15."""
        load_plugin.update()
        load_plugin.update_views()
        views = load_plugin.get_views()
        if views:  # Views might be empty if no stats
            assert 'min15' in views
            assert 'decoration' in views['min15']

    def test_views_contain_min5_decoration(self, load_plugin):
        """Test that views contain decoration for min5."""
        load_plugin.update()
        load_plugin.update_views()
        views = load_plugin.get_views()
        if views:
            assert 'min5' in views
            assert 'decoration' in views['min5']


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginJSON:
    """Test Load plugin JSON serialization."""

    def test_get_stats_returns_json(self, load_plugin):
        """Test that get_stats returns valid JSON."""
        load_plugin.update()
        stats_json = load_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, dict)

    def test_json_contains_expected_fields(self, load_plugin):
        """Test that JSON output contains expected fields."""
        load_plugin.update()
        stats_json = load_plugin.get_stats()
        parsed = json.loads(stats_json)
        expected_fields = ['min1', 'min5', 'min15', 'cpucore']
        for field in expected_fields:
            assert field in parsed


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginHistory:
    """Test Load plugin history functionality."""

    def test_history_enable_check(self, load_plugin):
        """Test that history_enable returns a boolean."""
        result = load_plugin.history_enable()
        assert isinstance(result, bool)

    def test_get_items_history_list(self, load_plugin):
        """Test that get_items_history_list returns the history items."""
        items = load_plugin.get_items_history_list()
        if items is not None:
            assert isinstance(items, list)
            item_names = [item['name'] for item in items]
            assert 'min1' in item_names


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginReset:
    """Test Load plugin reset functionality."""

    def test_reset_clears_stats(self, load_plugin):
        """Test that reset clears stats."""
        load_plugin.update()
        load_plugin.reset()
        stats = load_plugin.get_raw()
        assert stats == load_plugin.get_init_value()

    def test_reset_views(self, load_plugin):
        """Test that reset_views clears views."""
        load_plugin.update()
        load_plugin.update_views()
        load_plugin.reset_views()
        assert load_plugin.get_views() == {}


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginFieldsDescription:
    """Test Load plugin fields description."""

    def test_fields_description_exists(self, load_plugin):
        """Test that fields_description is defined."""
        assert load_plugin.fields_description is not None

    def test_mandatory_fields_described(self, load_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['min1', 'min5', 'min15', 'cpucore']
        for field in mandatory_fields:
            assert field in load_plugin.fields_description

    def test_field_has_description(self, load_plugin):
        """Test that each field has a description."""
        for field, info in load_plugin.fields_description.items():
            assert 'description' in info, f"Field {field} missing description"


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginMsgCurse:
    """Test Load plugin curse message generation."""

    def test_msg_curse_returns_list(self, load_plugin):
        """Test that msg_curse returns a list."""
        load_plugin.update()
        msg = load_plugin.msg_curse()
        assert isinstance(msg, list)

    def test_msg_curse_format(self, load_plugin):
        """Test that msg_curse returns properly formatted entries."""
        load_plugin.update()
        msg = load_plugin.msg_curse()
        if msg:
            for entry in msg:
                assert isinstance(entry, dict)
                assert 'msg' in entry

    def test_msg_curse_structure(self, load_plugin):
        """Test msg_curse output structure when stats available."""
        load_plugin.update()
        stats = load_plugin.get_raw()
        if stats and not load_plugin.is_disabled():
            msg = load_plugin.msg_curse()
            if msg:
                assert len(msg) > 0


class TestLoadHelperFunctions:
    """Test Load plugin helper functions."""

    def test_log_core_returns_int(self):
        """Test that log_core returns an integer."""
        cores = log_core()
        assert isinstance(cores, int)
        assert cores >= 1

    def test_phys_core_returns_int(self):
        """Test that phys_core returns an integer."""
        cores = phys_core()
        assert isinstance(cores, int)
        assert cores >= 1

    @pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
    def test_load_average_returns_tuple(self):
        """Test that load_average returns a tuple."""
        load = load_average()
        if load is not None:
            assert isinstance(load, tuple)
            assert len(load) == 3

    @pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
    def test_load_average_values_non_negative(self):
        """Test that load_average values are non-negative."""
        load = load_average()
        if load is not None:
            for value in load:
                assert value >= 0

    @pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
    def test_load_average_percent_mode(self):
        """Test load_average in percent mode."""
        load = load_average(percent=True)
        if load is not None:
            assert isinstance(load, tuple)
            assert len(load) == 3
            # Values can exceed 100% if load is high


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginAlerts:
    """Test Load plugin alert functionality."""

    def test_alert_based_on_cpucore(self, load_plugin):
        """Test that alerts are calculated based on CPU cores."""
        load_plugin.update()
        stats = load_plugin.get_raw()
        if 'cpucore' in stats and 'min15' in stats:
            # Maximum is 100 * cpucore
            alert = load_plugin.get_alert_log(stats['min15'], maximum=100 * stats['cpucore'])
            assert alert is not None


@pytest.mark.skipif(WINDOWS, reason="Load average not available on Windows")
class TestLoadPluginExport:
    """Test Load plugin export functionality."""

    def test_get_export_returns_dict(self, load_plugin):
        """Test that get_export returns a dict."""
        load_plugin.update()
        export = load_plugin.get_export()
        assert isinstance(export, dict)

    def test_export_equals_raw(self, load_plugin):
        """Test that export equals raw stats by default."""
        load_plugin.update()
        assert load_plugin.get_export() == load_plugin.get_raw()

    def test_export_contains_load_values_when_available(self, load_plugin):
        """Test that export contains load values when available."""
        load_plugin.update()
        export = load_plugin.get_export()
        if export:
            assert 'min1' in export
            assert 'min5' in export
            assert 'min15' in export
