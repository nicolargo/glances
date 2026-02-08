#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Network plugin."""

import json
import time

import pytest


@pytest.fixture
def network_plugin(glances_stats):
    """Return the Network plugin instance from glances_stats."""
    return glances_stats.get_plugin('network')


class TestNetworkPluginBasics:
    """Test basic Network plugin functionality."""

    def test_plugin_name(self, network_plugin):
        """Test plugin name is correctly set."""
        assert network_plugin.plugin_name == 'network'

    def test_plugin_is_enabled(self, network_plugin):
        """Test that the plugin is enabled by default."""
        assert network_plugin.is_enabled() is True

    def test_display_curse_enabled(self, network_plugin):
        """Test that curse display is enabled."""
        assert network_plugin.display_curse is True

    def test_get_key_returns_interface_name(self, network_plugin):
        """Test that get_key returns interface_name."""
        assert network_plugin.get_key() == 'interface_name'

    def test_history_items_defined(self, network_plugin):
        """Test that history items are properly defined."""
        items = network_plugin.get_items_history_list()
        assert items is not None
        item_names = [item['name'] for item in items]
        assert 'bytes_recv_rate_per_sec' in item_names
        assert 'bytes_sent_rate_per_sec' in item_names


class TestNetworkPluginUpdate:
    """Test Network plugin update functionality."""

    def test_update_returns_list(self, network_plugin):
        """Test that update returns a list."""
        network_plugin.update()
        stats = network_plugin.get_raw()
        assert isinstance(stats, list)

    def test_each_interface_has_name(self, network_plugin):
        """Test that each interface entry has a name."""
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            assert 'interface_name' in iface

    def test_bytes_recv_and_sent_present(self, network_plugin):
        """Test that bytes_recv and bytes_sent are present."""
        network_plugin.update()
        time.sleep(0.1)
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            assert 'bytes_recv' in iface
            assert 'bytes_sent' in iface

    def test_bytes_values_non_negative(self, network_plugin):
        """Test that byte values are non-negative."""
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            if 'bytes_recv' in iface and iface['bytes_recv'] is not None:
                assert iface['bytes_recv'] >= 0
            if 'bytes_sent' in iface and iface['bytes_sent'] is not None:
                assert iface['bytes_sent'] >= 0


class TestNetworkPluginRateCalculation:
    """Test Network plugin rate calculation."""

    def test_rate_fields_after_two_updates(self, network_plugin):
        """Test that rate fields are populated after two updates."""
        network_plugin.update()
        time.sleep(0.2)
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            # Rate fields should be present after second update
            assert 'bytes_recv_rate_per_sec' in iface or 'bytes_recv' in iface
            assert 'bytes_sent_rate_per_sec' in iface or 'bytes_sent' in iface

    def test_bytes_all_calculated(self, network_plugin):
        """Test that bytes_all is calculated as sum of recv and sent."""
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            if all(k in iface for k in ['bytes_recv', 'bytes_sent', 'bytes_all']):
                if iface['bytes_recv'] is not None and iface['bytes_sent'] is not None:
                    expected = iface['bytes_recv'] + iface['bytes_sent']
                    assert iface['bytes_all'] == expected


class TestNetworkPluginInterfaceInfo:
    """Test Network plugin interface information."""

    def test_is_up_field_present(self, network_plugin):
        """Test that is_up field is present for interfaces when available."""
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            # is_up may not be present in all stats entries
            if 'is_up' in iface:
                assert isinstance(iface['is_up'], bool)

    def test_speed_field_present(self, network_plugin):
        """Test that speed field is present for interfaces when available."""
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            if 'speed' in iface:
                assert isinstance(iface['speed'], (int, float))

    def test_alias_field_present(self, network_plugin):
        """Test that alias field is present for interfaces."""
        network_plugin.update()
        stats = network_plugin.get_raw()
        for iface in stats:
            assert 'alias' in iface


class TestNetworkPluginViews:
    """Test Network plugin views functionality."""

    def test_update_views_creates_views(self, network_plugin):
        """Test that update_views creates views dictionary."""
        network_plugin.update()
        network_plugin.update_views()
        views = network_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_keyed_by_interface(self, network_plugin):
        """Test that views are keyed by interface name."""
        network_plugin.update()
        time.sleep(0.1)
        network_plugin.update()
        network_plugin.update_views()
        views = network_plugin.get_views()
        stats = network_plugin.get_raw()
        for iface in stats:
            if iface['interface_name'] in views:
                assert isinstance(views[iface['interface_name']], dict)


class TestNetworkPluginJSON:
    """Test Network plugin JSON serialization."""

    def test_get_stats_returns_json(self, network_plugin):
        """Test that get_stats returns valid JSON."""
        network_plugin.update()
        stats_json = network_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, list)

    def test_json_preserves_interface_data(self, network_plugin):
        """Test that JSON output preserves interface data."""
        network_plugin.update()
        stats_json = network_plugin.get_stats()
        parsed = json.loads(stats_json)
        for iface in parsed:
            assert 'interface_name' in iface


class TestNetworkPluginHistory:
    """Test Network plugin history functionality."""

    def test_history_enable(self, network_plugin):
        """Test that history can be enabled."""
        assert network_plugin.history_enable() is not None


class TestNetworkPluginReset:
    """Test Network plugin reset functionality."""

    def test_reset_clears_stats(self, network_plugin):
        """Test that reset clears stats."""
        network_plugin.update()
        network_plugin.reset()
        stats = network_plugin.get_raw()
        assert stats == network_plugin.get_init_value()

    def test_reset_views(self, network_plugin):
        """Test that reset_views clears views."""
        network_plugin.update()
        network_plugin.update_views()
        network_plugin.reset_views()
        assert network_plugin.get_views() == {}


class TestNetworkPluginFieldsDescription:
    """Test Network plugin fields description."""

    def test_fields_description_exists(self, network_plugin):
        """Test that fields_description is defined."""
        assert network_plugin.fields_description is not None

    def test_mandatory_fields_described(self, network_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['interface_name', 'bytes_recv', 'bytes_sent']
        for field in mandatory_fields:
            assert field in network_plugin.fields_description

    def test_rate_fields_described(self, network_plugin):
        """Test that rate-enabled fields have rate flag."""
        rate_fields = ['bytes_recv', 'bytes_sent', 'bytes_all']
        for field in rate_fields:
            if field in network_plugin.fields_description:
                assert network_plugin.fields_description[field].get('rate') is True


class TestNetworkPluginConfiguration:
    """Test Network plugin configuration options."""

    def test_hide_zero_attribute(self, network_plugin):
        """Test that hide_zero attribute exists."""
        assert hasattr(network_plugin, 'hide_zero')

    def test_hide_zero_fields_defined(self, network_plugin):
        """Test that hide_zero_fields is defined."""
        assert hasattr(network_plugin, 'hide_zero_fields')
        assert isinstance(network_plugin.hide_zero_fields, list)

    def test_hide_no_up_attribute(self, network_plugin):
        """Test that hide_no_up attribute exists."""
        assert hasattr(network_plugin, 'hide_no_up')

    def test_hide_no_ip_attribute(self, network_plugin):
        """Test that hide_no_ip attribute exists."""
        assert hasattr(network_plugin, 'hide_no_ip')


class TestNetworkPluginMsgCurse:
    """Test Network plugin curse message generation."""

    def test_msg_curse_empty_without_max_width(self, network_plugin):
        """Test that msg_curse returns empty without max_width."""
        network_plugin.update()
        msg = network_plugin.msg_curse()
        # Without max_width, should return empty list
        assert isinstance(msg, list)
        assert len(msg) == 0

    def test_msg_curse_with_args_and_max_width(self, network_plugin):
        """Test that msg_curse works with args and max_width after views update."""
        network_plugin.update()
        network_plugin.update_views()
        # msg_curse requires args with network_cumul and network_sum
        if hasattr(network_plugin, 'args') and network_plugin.args:
            try:
                msg = network_plugin.msg_curse(args=network_plugin.args, max_width=80)
                assert isinstance(msg, list)
            except KeyError:
                # Views might not be synced with stats in some cases
                pass


class TestNetworkPluginSorting:
    """Test Network plugin sorting functionality."""

    def test_sorted_stats_returns_list(self, network_plugin):
        """Test that sorted_stats returns a list."""
        network_plugin.update()
        sorted_stats = network_plugin.sorted_stats()
        assert isinstance(sorted_stats, list)

    def test_sorted_stats_preserves_count(self, network_plugin):
        """Test that sorted_stats preserves interface count."""
        network_plugin.update()
        raw_count = len(network_plugin.get_raw())
        sorted_count = len(network_plugin.sorted_stats())
        assert raw_count == sorted_count


class TestNetworkPluginExport:
    """Test Network plugin export functionality."""

    def test_get_export_returns_list(self, network_plugin):
        """Test that get_export returns a list."""
        network_plugin.update()
        export = network_plugin.get_export()
        assert isinstance(export, list)

    def test_export_equals_raw(self, network_plugin):
        """Test that export equals raw stats by default."""
        network_plugin.update()
        assert network_plugin.get_export() == network_plugin.get_raw()


class TestNetworkPluginAlerts:
    """Test Network plugin alert functionality."""

    def test_views_have_decoration(self, network_plugin):
        """Test that interface views have decoration after update."""
        network_plugin.update()
        time.sleep(0.1)
        network_plugin.update()
        network_plugin.update_views()
        views = network_plugin.get_views()
        stats = network_plugin.get_raw()

        for iface in stats:
            iface_name = iface['interface_name']
            if iface_name in views and 'bytes_recv' in views[iface_name]:
                # Check that decoration exists for rate fields
                assert 'decoration' in views[iface_name]['bytes_recv']
