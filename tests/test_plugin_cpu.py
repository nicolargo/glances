#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the CPU plugin."""

import json
import time

import pytest

from glances.globals import WINDOWS


@pytest.fixture
def cpu_plugin(glances_stats):
    """Return the CPU plugin instance from glances_stats."""
    return glances_stats.get_plugin('cpu')


class TestCpuPluginBasics:
    """Test basic CPU plugin functionality."""

    def test_plugin_name(self, cpu_plugin):
        """Test plugin name is correctly set."""
        assert cpu_plugin.plugin_name == 'cpu'

    def test_plugin_is_enabled(self, cpu_plugin):
        """Test that the plugin is enabled by default."""
        assert cpu_plugin.is_enabled() is True

    def test_display_curse_enabled(self, cpu_plugin):
        """Test that curse display is enabled."""
        assert cpu_plugin.display_curse is True

    def test_history_items_defined(self, cpu_plugin):
        """Test that history items are properly defined."""
        items = cpu_plugin.get_items_history_list()
        assert items is not None
        assert len(items) >= 2
        item_names = [item['name'] for item in items]
        assert 'user' in item_names
        assert 'system' in item_names


class TestCpuPluginUpdate:
    """Test CPU plugin update functionality."""

    def test_update_returns_dict(self, cpu_plugin):
        """Test that update returns a dictionary."""
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        assert isinstance(stats, dict)

    def test_update_contains_mandatory_keys(self, cpu_plugin):
        """Test that stats contain mandatory keys."""
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        mandatory_keys = ['total', 'system', 'user', 'idle']
        for key in mandatory_keys:
            assert key in stats, f"Missing mandatory key: {key}"

    def test_cpu_percentages_in_valid_range(self, cpu_plugin):
        """Test that CPU percentages are within valid range."""
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        percentage_keys = ['total', 'system', 'user', 'idle']
        for key in percentage_keys:
            if key in stats and stats[key] is not None:
                assert 0 <= stats[key] <= 100, f"{key} percentage out of range: {stats[key]}"

    def test_total_cpu_calculation(self, cpu_plugin):
        """Test that total CPU is correctly calculated."""
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        assert 'total' in stats
        assert stats['total'] >= 0

    def test_cpucore_count(self, cpu_plugin):
        """Test that CPU core count is reported."""
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        assert 'cpucore' in stats
        assert stats['cpucore'] >= 1


class TestCpuPluginContextSwitches:
    """Test CPU context switches and interrupts stats."""

    def test_ctx_switches_present(self, cpu_plugin):
        """Test that context switches stat is present."""
        cpu_plugin.update()
        time.sleep(0.1)
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        assert 'ctx_switches' in stats

    def test_interrupts_present(self, cpu_plugin):
        """Test that interrupts stat is present."""
        cpu_plugin.update()
        time.sleep(0.1)
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        assert 'interrupts' in stats

    @pytest.mark.skipif(WINDOWS, reason="soft_interrupts not available on Windows")
    def test_soft_interrupts_present(self, cpu_plugin):
        """Test that soft interrupts stat is present on non-Windows."""
        cpu_plugin.update()
        time.sleep(0.1)
        cpu_plugin.update()
        stats = cpu_plugin.get_raw()
        assert 'soft_interrupts' in stats


class TestCpuPluginViews:
    """Test CPU plugin views functionality."""

    def test_update_views_creates_views(self, cpu_plugin):
        """Test that update_views creates views dictionary."""
        cpu_plugin.update()
        cpu_plugin.update_views()
        views = cpu_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_contain_decoration(self, cpu_plugin):
        """Test that views contain decoration for total CPU."""
        cpu_plugin.update()
        cpu_plugin.update_views()
        views = cpu_plugin.get_views()
        assert 'total' in views
        assert 'decoration' in views['total']


class TestCpuPluginJSON:
    """Test CPU plugin JSON serialization."""

    def test_get_stats_returns_json(self, cpu_plugin):
        """Test that get_stats returns valid JSON."""
        cpu_plugin.update()
        stats_json = cpu_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, dict)

    def test_json_contains_expected_fields(self, cpu_plugin):
        """Test that JSON output contains expected fields."""
        cpu_plugin.update()
        stats_json = cpu_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert 'total' in parsed
        assert 'user' in parsed
        assert 'system' in parsed


class TestCpuPluginHistory:
    """Test CPU plugin history functionality."""

    def test_history_enable_check(self, cpu_plugin):
        """Test that history_enable returns a boolean."""
        result = cpu_plugin.history_enable()
        assert isinstance(result, bool)

    def test_get_items_history_list(self, cpu_plugin):
        """Test that get_items_history_list returns the history items."""
        items = cpu_plugin.get_items_history_list()
        if items is not None:
            assert isinstance(items, list)
            assert len(items) >= 2


class TestCpuPluginReset:
    """Test CPU plugin reset functionality."""

    def test_reset_clears_stats(self, cpu_plugin):
        """Test that reset clears stats."""
        cpu_plugin.update()
        cpu_plugin.reset()
        stats = cpu_plugin.get_raw()
        assert stats == cpu_plugin.get_init_value()

    def test_reset_views(self, cpu_plugin):
        """Test that reset_views clears views."""
        cpu_plugin.update()
        cpu_plugin.update_views()
        cpu_plugin.reset_views()
        assert cpu_plugin.get_views() == {}


class TestCpuPluginFieldsDescription:
    """Test CPU plugin fields description."""

    def test_fields_description_exists(self, cpu_plugin):
        """Test that fields_description is defined."""
        assert cpu_plugin.fields_description is not None

    def test_mandatory_fields_described(self, cpu_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['total', 'system', 'user', 'idle']
        for field in mandatory_fields:
            assert field in cpu_plugin.fields_description

    def test_field_has_description(self, cpu_plugin):
        """Test that each field has a description."""
        for field, info in cpu_plugin.fields_description.items():
            assert 'description' in info, f"Field {field} missing description"


class TestCpuPluginAlerts:
    """Test CPU plugin alert functionality."""

    def test_get_alert_returns_valid_status(self, cpu_plugin):
        """Test that get_alert returns a valid status."""
        cpu_plugin.update()
        alert = cpu_plugin.get_alert(50, minimum=0, maximum=100, header='total')
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

    def test_alert_levels(self, cpu_plugin):
        """Test different alert levels based on CPU usage."""
        cpu_plugin.update()
        # Low usage should be OK
        alert_low = cpu_plugin.get_alert(10, minimum=0, maximum=100, header='total')
        # The result depends on config, but should not be CRITICAL for 10%
        assert not alert_low.startswith('CRITICAL')


class TestCpuPluginMsgCurse:
    """Test CPU plugin curse message generation."""

    def test_msg_curse_returns_list(self, cpu_plugin):
        """Test that msg_curse returns a list."""
        cpu_plugin.update()
        msg = cpu_plugin.msg_curse()
        assert isinstance(msg, list)

    def test_msg_curse_format(self, cpu_plugin):
        """Test that msg_curse returns properly formatted entries."""
        cpu_plugin.update()
        # Ensure args.percpu is not set to get output
        if hasattr(cpu_plugin.args, 'percpu'):
            original_percpu = cpu_plugin.args.percpu
            cpu_plugin.args.percpu = False
        msg = cpu_plugin.msg_curse()
        if msg:  # May be empty if percpu mode or disabled
            for entry in msg:
                assert isinstance(entry, dict)
                assert 'msg' in entry
        if hasattr(cpu_plugin.args, 'percpu'):
            cpu_plugin.args.percpu = original_percpu

    def test_msg_curse_has_title_when_enabled(self, cpu_plugin):
        """Test that msg_curse contains CPU title when not in percpu mode."""
        cpu_plugin.update()
        if hasattr(cpu_plugin.args, 'percpu'):
            original_percpu = cpu_plugin.args.percpu
            cpu_plugin.args.percpu = False
        msg = cpu_plugin.msg_curse()
        if msg:
            messages = [m.get('msg', '') for m in msg]
            assert any('CPU' in str(m) for m in messages)
        if hasattr(cpu_plugin.args, 'percpu'):
            cpu_plugin.args.percpu = original_percpu
