#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the LibreHardwareMonitor sensor (Windows temperatures)."""

from glances.plugins.sensors.sensor.glances_librehardwaremonitor import GlancesGrabLHM

# Sample of the data.json tree returned by the LibreHardwareMonitor web server
DATA_JSON_SAMPLE = {
    "id": 0,
    "Text": "Sensor",
    "Min": "Min",
    "Value": "Value",
    "Max": "Max",
    "ImageURL": "",
    "Children": [
        {
            "id": 1,
            "Text": "MY-PC",
            "ImageURL": "images_icon/computer.png",
            "Children": [
                {
                    "id": 2,
                    "Text": "ASUS PRIME B250M-C",
                    "ImageURL": "images_icon/mainboard.png",
                    "Children": [
                        {
                            "id": 3,
                            "Text": "Nuvoton NCT6793D",
                            "ImageURL": "images_icon/chip.png",
                            "Children": [
                                {
                                    "id": 4,
                                    "Text": "Voltages",
                                    "ImageURL": "images_icon/voltage.png",
                                    "Children": [
                                        {
                                            "id": 5,
                                            "Text": "Vcore",
                                            "Children": [],
                                            "Min": "0,960 V",
                                            "Value": "1,032 V",
                                            "Max": "1,144 V",
                                            "ImageURL": "images/transparent.png",
                                            "SensorId": "/lpc/nct6793d/0/voltage/0",
                                            "Type": "Voltage",
                                        },
                                    ],
                                },
                                {
                                    "id": 6,
                                    "Text": "Temperatures",
                                    "ImageURL": "images_icon/temperature.png",
                                    "Children": [
                                        {
                                            "id": 7,
                                            "Text": "SYSTIN",
                                            "Children": [],
                                            "Min": "27,0 °C",
                                            "Value": "29,5 °C",
                                            "Max": "33,0 °C",
                                            "ImageURL": "images/transparent.png",
                                            "SensorId": "/lpc/nct6793d/0/temperature/3",
                                            "Type": "Temperature",
                                        },
                                    ],
                                },
                                {
                                    "id": 8,
                                    "Text": "Fans",
                                    "ImageURL": "images_icon/fan.png",
                                    "Children": [
                                        {
                                            "id": 9,
                                            "Text": "CPU Fan",
                                            "Children": [],
                                            "Min": "1100 RPM",
                                            "Value": "1200 RPM",
                                            "Max": "1300 RPM",
                                            "ImageURL": "images/transparent.png",
                                            "SensorId": "/lpc/nct6793d/0/fan/1",
                                            "Type": "Fan",
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": 10,
                    "Text": "Intel Core i7-7700",
                    "ImageURL": "images_icon/cpu.png",
                    "Children": [
                        {
                            "id": 11,
                            "Text": "Temperatures",
                            "ImageURL": "images_icon/temperature.png",
                            "Children": [
                                {
                                    "id": 12,
                                    "Text": "CPU Package",
                                    "Children": [],
                                    "Min": "29,0 °C",
                                    "Value": "35,5 °C",
                                    "Max": "45,0 °C",
                                    "ImageURL": "images/transparent.png",
                                    "SensorId": "/intelcpu/0/temperature/8",
                                    "Type": "Temperature",
                                },
                                {
                                    "id": 13,
                                    "Text": "CPU Core #1",
                                    "Children": [],
                                    "Min": "28,0 °C",
                                    "Value": "-",
                                    "Max": "44,0 °C",
                                    "ImageURL": "images/transparent.png",
                                    "SensorId": "/intelcpu/0/temperature/0",
                                    "Type": "Temperature",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ],
}


class TestGlancesGrabLHMParsing:
    """Test the data.json parsing."""

    def test_get_returns_temperatures_only(self):
        """Test that only the temperature sensors are returned."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        stats = lhm.get()
        labels = [i['label'] for i in stats]
        assert 'Nuvoton NCT6793D SYSTIN' in labels
        assert 'Intel Core i7-7700 CPU Package' in labels
        # Voltages and fans are not temperatures
        assert not any('Vcore' in label for label in labels)
        assert not any('Fan' in label for label in labels)

    def test_sensor_fields(self):
        """Test that each sensor entry has the expected fields."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        for sensor in lhm.get():
            assert isinstance(sensor['label'], str)
            assert sensor['unit'] == 'C'
            assert isinstance(sensor['value'], float)
            assert sensor['warning'] is None
            assert sensor['critical'] is None

    def test_locale_decimal_separator(self):
        """Test that values with a comma decimal separator are parsed."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        stats = lhm.get()
        systin = next(i for i in stats if i['label'] == 'Nuvoton NCT6793D SYSTIN')
        assert systin['value'] == 29.5

    def test_sensor_without_value_is_skipped(self):
        """Test that a sensor with a non numeric value ('-') is skipped."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        labels = [i['label'] for i in lhm.get()]
        assert 'Intel Core i7-7700 CPU Core #1' not in labels

    def test_fetch_failure_returns_empty_list(self):
        """Test that a web server connection failure returns an empty list."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: None
        assert lhm.get() == []


class TestGlancesGrabLHMValueParsing:
    """Test the sensor value parsing."""

    def test_parse_value_comma(self):
        assert GlancesGrabLHM._parse_value('44,5 °C') == 44.5

    def test_parse_value_dot(self):
        assert GlancesGrabLHM._parse_value('44.5 °C') == 44.5

    def test_parse_value_invalid(self):
        assert GlancesGrabLHM._parse_value('-') is None

    def test_parse_value_none(self):
        assert GlancesGrabLHM._parse_value(None) is None


class TestGlancesGrabLHMSensorDetection:
    """Test the temperature sensor detection."""

    def test_type_field(self):
        assert GlancesGrabLHM._is_temperature({'Type': 'Temperature', 'Value': '44,5 °C'})
        assert not GlancesGrabLHM._is_temperature({'Type': 'Voltage', 'Value': '1,032 V'})

    def test_fallback_on_value_unit(self):
        # Older LibreHardwareMonitor releases do not expose the Type field
        assert GlancesGrabLHM._is_temperature({'Value': '44,5 °C'})
        assert not GlancesGrabLHM._is_temperature({'Value': '1200 RPM'})
        assert not GlancesGrabLHM._is_temperature({})
