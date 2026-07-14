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
                                {
                                    "id": 14,
                                    "Text": "CPU Core #1 Distance to TjMax",
                                    "Children": [],
                                    "Min": "55,0 °C",
                                    "Value": "62,0 °C",
                                    "Max": "71,0 °C",
                                    "ImageURL": "images/transparent.png",
                                    "SensorId": "/intelcpu/0/temperature/10",
                                    "Type": "Temperature",
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": 15,
                    "Text": "Samsung SSD 980 1TB",
                    "ImageURL": "images_icon/hdd.png",
                    "Children": [
                        {
                            "id": 16,
                            "Text": "Temperatures",
                            "ImageURL": "images_icon/temperature.png",
                            "Children": [
                                {
                                    "id": 17,
                                    "Text": "Temperature",
                                    "Children": [],
                                    "Min": "38,0 °C",
                                    "Value": "43,0 °C",
                                    "Max": "51,0 °C",
                                    "ImageURL": "images/transparent.png",
                                    "SensorId": "/nvme/0/temperature/0",
                                    "Type": "Temperature",
                                },
                                {
                                    "id": 18,
                                    "Text": "Warning Temperature",
                                    "Children": [],
                                    "Min": "83,0 °C",
                                    "Value": "83,0 °C",
                                    "Max": "83,0 °C",
                                    "ImageURL": "images/transparent.png",
                                    "SensorId": "/nvme/0/temperature/10",
                                    "Type": "Temperature",
                                },
                                {
                                    "id": 19,
                                    "Text": "Critical Temperature",
                                    "Children": [],
                                    "Min": "87,0 °C",
                                    "Value": "87,0 °C",
                                    "Max": "87,0 °C",
                                    "ImageURL": "images/transparent.png",
                                    "SensorId": "/nvme/0/temperature/11",
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
        assert 'SYSTIN (Nuvoton NCT6793D)' in labels
        assert 'CPU Package (Intel Core i7-7700)' in labels
        # Voltages and fans are not temperatures
        assert not any('Vcore' in label for label in labels)
        assert not any('Fan' in label for label in labels)

    def test_pseudo_sensors_are_excluded(self):
        """Test that thresholds constants and thermal margins are not readings."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        labels = [i['label'] for i in lhm.get()]
        # NVMe thresholds constants (would trigger a permanent CRITICAL alert)
        assert not any('Warning Temperature' in label for label in labels)
        assert not any('Critical Temperature' in label for label in labels)
        # Inverted thermal margin (higher means cooler)
        assert not any('Distance to TjMax' in label for label in labels)

    def test_disks_are_excluded_by_default(self):
        """Test that the disks temperatures are not in the default (core) instance."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        labels = [i['label'] for i in lhm.get()]
        assert not any('Samsung' in label for label in labels)

    def test_storage_instance_returns_disks_only(self):
        """Test that the storage instance returns only the disks temperatures."""
        lhm = GlancesGrabLHM(storage=True)
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        stats = lhm.get()
        assert [i['label'] for i in stats] == ['Temperature (Samsung SSD 980 1TB)']
        assert stats[0]['value'] == 43.0

    def test_nvme_thresholds_are_used_as_warning_critical(self):
        """Test that the NVMe thresholds constants fill the warning/critical fields."""
        lhm = GlancesGrabLHM(storage=True)
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        disk = lhm.get()[0]
        assert disk['warning'] == 83
        assert disk['critical'] == 87

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
        systin = next(i for i in stats if i['label'] == 'SYSTIN (Nuvoton NCT6793D)')
        assert systin['value'] == 29.5

    def test_sensor_without_value_is_skipped(self):
        """Test that a sensor with a non numeric value ('-') is skipped."""
        lhm = GlancesGrabLHM()
        lhm.fetch = lambda: DATA_JSON_SAMPLE
        labels = [i['label'] for i in lhm.get()]
        assert 'CPU Core #1 (Intel Core i7-7700)' not in labels

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


class TestHddSystemThresholds:
    """Test that the disks own thresholds are used by the alert logic.

    NVMe drives declare their thresholds (e.g. warning 83 / critical 87):
    a healthy internal sensor at 59.9C must not be flagged against the
    generic temperature_hdd limits (see #3265).
    """

    @staticmethod
    def _views_decoration(sensors_plugin, value):
        sensors_plugin.stats = [
            {
                'label': 'Temperature #1 (WD_BLACK SN770 500GB)',
                'unit': 'C',
                'value': value,
                'warning': 83,
                'critical': 87,
                'type': 'temperature_hdd',
                'key': 'label',
            }
        ]
        sensors_plugin.update_views()
        return sensors_plugin.get_views()['Temperature #1 (WD_BLACK SN770 500GB)']['value']['decoration']

    def test_healthy_value_is_ok(self, glances_stats):
        sensors_plugin = glances_stats.get_plugin('sensors')
        assert self._views_decoration(sensors_plugin, 59.9) == 'OK'

    def test_value_over_drive_warning_is_warning(self, glances_stats):
        sensors_plugin = glances_stats.get_plugin('sensors')
        assert self._views_decoration(sensors_plugin, 84.0) == 'WARNING'

    def test_value_over_drive_critical_is_critical(self, glances_stats):
        sensors_plugin = glances_stats.get_plugin('sensors')
        assert self._views_decoration(sensors_plugin, 90.0) == 'CRITICAL'


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
