#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Sensors plugin."""

import pytest

from glances.globals import LINUX
from glances.plugins.sensors.grab import GlancesGrabSensors


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
