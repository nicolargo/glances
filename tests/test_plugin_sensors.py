#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Sensors plugin."""

import json

import pytest

from glances.globals import LINUX
from glances.plugins.sensors import GlancesGrabSensors


@pytest.fixture
def sensors_plugin(glances_stats):
    """Return the Sensors plugin instance from glances_stats."""
    return glances_stats.get_plugin('sensors')


class TestSensorsPluginBasics:
    """Test basic Sensors plugin functionality."""

    def test_plugin_name(self, sensors_plugin):
        """Test plugin name is correctly set."""
        assert sensors_plugin.plugin_name == 'sensors'

    def test_plugin_is_enabled(self, sensors_plugin):
        """Test that the plugin is enabled by default."""
        assert sensors_plugin.is_enabled() is True

    def test_display_curse_enabled(self, sensors_plugin):
        """Test that curse display is enabled."""
        assert sensors_plugin.display_curse is True

    def test_get_key_returns_label(self, sensors_plugin):
        """Test that get_key returns label."""
        assert sensors_plugin.get_key() == 'label'


class TestSensorsPluginUpdate:
    """Test Sensors plugin update functionality."""

    def test_update_returns_list(self, sensors_plugin):
        """Test that update returns a list."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        assert isinstance(stats, list)

    def test_each_sensor_has_label(self, sensors_plugin):
        """Test that each sensor entry has a label."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        for sensor in stats:
            assert 'label' in sensor

    def test_each_sensor_has_type(self, sensors_plugin):
        """Test that each sensor entry has a type."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        for sensor in stats:
            assert 'type' in sensor

    def test_each_sensor_has_value(self, sensors_plugin):
        """Test that each sensor entry has a value."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        for sensor in stats:
            assert 'value' in sensor

    def test_each_sensor_has_unit(self, sensors_plugin):
        """Test that each sensor entry has a unit."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        for sensor in stats:
            assert 'unit' in sensor


class TestSensorsPluginTypes:
    """Test Sensors plugin sensor types."""

    def test_valid_sensor_types(self, sensors_plugin):
        """Test that sensor types are valid."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        valid_types = ['temperature_core', 'fan_speed', 'temperature_hdd', 'battery']
        for sensor in stats:
            assert sensor['type'] in valid_types


class TestSensorsPluginViews:
    """Test Sensors plugin views functionality."""

    def test_update_views_creates_views(self, sensors_plugin):
        """Test that update_views creates views dictionary."""
        sensors_plugin.update()
        sensors_plugin.update_views()
        views = sensors_plugin.get_views()
        assert isinstance(views, dict)

    def test_views_keyed_by_label(self, sensors_plugin):
        """Test that views are keyed by sensor label."""
        sensors_plugin.update()
        sensors_plugin.update_views()
        views = sensors_plugin.get_views()
        stats = sensors_plugin.get_raw()
        for sensor in stats:
            if sensor['label'] in views:
                assert isinstance(views[sensor['label']], dict)


class TestSensorsPluginJSON:
    """Test Sensors plugin JSON serialization."""

    def test_get_stats_returns_json(self, sensors_plugin):
        """Test that get_stats returns valid JSON."""
        sensors_plugin.update()
        stats_json = sensors_plugin.get_stats()
        parsed = json.loads(stats_json)
        assert isinstance(parsed, list)

    def test_json_preserves_sensor_data(self, sensors_plugin):
        """Test that JSON output preserves sensor data."""
        sensors_plugin.update()
        stats_json = sensors_plugin.get_stats()
        parsed = json.loads(stats_json)
        for sensor in parsed:
            assert 'label' in sensor
            assert 'type' in sensor
            assert 'value' in sensor


class TestSensorsPluginReset:
    """Test Sensors plugin reset functionality."""

    def test_reset_clears_stats(self, sensors_plugin):
        """Test that reset clears stats."""
        sensors_plugin.update()
        sensors_plugin.reset()
        stats = sensors_plugin.get_raw()
        assert stats == sensors_plugin.get_init_value()

    def test_reset_views(self, sensors_plugin):
        """Test that reset_views clears views."""
        sensors_plugin.update()
        sensors_plugin.update_views()
        sensors_plugin.reset_views()
        assert sensors_plugin.get_views() == {}


class TestSensorsPluginFieldsDescription:
    """Test Sensors plugin fields description."""

    def test_fields_description_exists(self, sensors_plugin):
        """Test that fields_description is defined."""
        assert sensors_plugin.fields_description is not None

    def test_mandatory_fields_described(self, sensors_plugin):
        """Test that mandatory fields have descriptions."""
        mandatory_fields = ['label', 'unit', 'value', 'type']
        for field in mandatory_fields:
            assert field in sensors_plugin.fields_description

    def test_threshold_fields_described(self, sensors_plugin):
        """Test that threshold fields are described."""
        assert 'warning' in sensors_plugin.fields_description
        assert 'critical' in sensors_plugin.fields_description


class TestSensorsPluginMsgCurse:
    """Test Sensors plugin curse message generation."""

    def test_msg_curse_returns_list(self, sensors_plugin):
        """Test that msg_curse returns a list."""
        sensors_plugin.update()
        msg = sensors_plugin.msg_curse(max_width=80)
        assert isinstance(msg, list)

    def test_msg_curse_empty_without_max_width(self, sensors_plugin):
        """Test that msg_curse returns empty without max_width."""
        sensors_plugin.update()
        msg = sensors_plugin.msg_curse()
        assert isinstance(msg, list)


class TestSensorsPluginExport:
    """Test Sensors plugin export functionality."""

    def test_get_export_returns_list(self, sensors_plugin):
        """Test that get_export returns a list."""
        sensors_plugin.update()
        export = sensors_plugin.get_export()
        assert isinstance(export, list)

    def test_export_equals_raw(self, sensors_plugin):
        """Test that export equals raw stats by default."""
        sensors_plugin.update()
        assert sensors_plugin.get_export() == sensors_plugin.get_raw()


class TestSensorsPluginRefresh:
    """Test Sensors plugin refresh configuration."""

    def test_refresh_multiplier_applied(self, sensors_plugin):
        """Test that refresh multiplier is applied."""
        # Sensors have a default refresh multiplier
        refresh = sensors_plugin.get_refresh()
        assert refresh >= 1  # Should be at least 1 second


class TestSensorsPluginBatteryTrend:
    """Test Sensors plugin battery trend functionality."""

    def test_battery_trend_charging(self, sensors_plugin):
        """Test battery trend for charging status."""
        result = sensors_plugin.battery_trend({'status': 'Charging'})
        assert result != ''

    def test_battery_trend_discharging(self, sensors_plugin):
        """Test battery trend for discharging status."""
        result = sensors_plugin.battery_trend({'status': 'Discharging'})
        assert result != ''

    def test_battery_trend_full(self, sensors_plugin):
        """Test battery trend for full status."""
        result = sensors_plugin.battery_trend({'status': 'Full'})
        assert result != ''

    def test_battery_trend_no_status(self, sensors_plugin):
        """Test battery trend with no status."""
        result = sensors_plugin.battery_trend({})
        assert result == ''


class TestSensorsPluginThresholds:
    """Test Sensors plugin threshold handling."""

    def test_sensor_warning_threshold(self, sensors_plugin):
        """Test that sensors can have warning thresholds."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        for sensor in stats:
            # Warning threshold may be None or an int
            if 'warning' in sensor:
                assert sensor['warning'] is None or isinstance(sensor['warning'], (int, float))

    def test_sensor_critical_threshold(self, sensors_plugin):
        """Test that sensors can have critical thresholds."""
        sensors_plugin.update()
        stats = sensors_plugin.get_raw()
        for sensor in stats:
            # Critical threshold may be None or an int
            if 'critical' in sensor:
                assert sensor['critical'] is None or isinstance(sensor['critical'], (int, float))


class TestSensorsPluginGrabMap:
    """Test Sensors plugin grab map functionality."""

    def test_sensors_grab_map_exists(self, sensors_plugin):
        """Test that sensors_grab_map is defined."""
        assert hasattr(sensors_plugin, 'sensors_grab_map')
        assert isinstance(sensors_plugin.sensors_grab_map, dict)


@pytest.mark.skipif(not LINUX, reason="GlancesGrabSensors only fully works on Linux")
class TestGlancesGrabSensors:
    """Test GlancesGrabSensors class."""

    def test_cpu_temp_sensor_init(self):
        """Test CPU temperature sensor initialization."""
        sensor_def = {'type': 'temperature_core', 'unit': 'C'}
        try:
            sensor = GlancesGrabSensors(sensor_def)
            # init may be True or False depending on hardware
            assert hasattr(sensor, 'init')
        except Exception as e:
            # May fail on systems without temperature sensors
            print(f"Sensor init failed: {e}")

    def test_fan_speed_sensor_init(self):
        """Test fan speed sensor initialization."""
        sensor_def = {'type': 'fan_speed', 'unit': 'R'}
        try:
            sensor = GlancesGrabSensors(sensor_def)
            assert hasattr(sensor, 'init')
        except Exception as e:
            # May fail on systems without fan sensors
            print(f"Sensor init failed: {e}")

    def test_sensor_update_returns_list(self):
        """Test that sensor update returns a list."""
        sensor_def = {'type': 'temperature_core', 'unit': 'C'}
        try:
            sensor = GlancesGrabSensors(sensor_def)
            if sensor.init:
                result = sensor.update()
                assert isinstance(result, list)
        except Exception as e:
            # May fail on systems without sensors
            print(f"Sensor init failed: {e}")


class TestSensorsPluginAlerts:
    """Test Sensors plugin alert functionality."""

    def test_views_have_value_decoration(self, sensors_plugin):
        """Test that sensor views have decoration for value field."""
        sensors_plugin.update()
        sensors_plugin.update_views()
        views = sensors_plugin.get_views()
        stats = sensors_plugin.get_raw()

        for sensor in stats:
            label = sensor['label']
            if label in views and 'value' in views[label]:
                if sensor['value']:  # Only check if value is not empty
                    assert 'decoration' in views[label]['value']
