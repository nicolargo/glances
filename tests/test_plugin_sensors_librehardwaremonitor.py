#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the LibreHardwareMonitor sensors (Windows temperatures and fans)."""

from __future__ import annotations

import copy

import pytest

pytest.importorskip("librehardwaremonitor_api")

from librehardwaremonitor_api import LibreHardwareMonitorConnectionError  # noqa: E402
from librehardwaremonitor_api.parser import LibreHardwareMonitorParser  # noqa: E402

from glances.config import GlancesConfig  # noqa: E402
from glances.plugins.sensors import model  # noqa: E402
from glances.plugins.sensors.model import PluginModel  # noqa: E402
from glances.plugins.sensors.sensor.glances_librehardwaremonitor import GlancesGrabLHM  # noqa: E402
from glances.stats_store import StatsStore  # noqa: E402

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
            "Text": "DESKTOP-TEST",
            "ImageURL": "images_icon/computer.png",
            "Children": [
                {
                    "id": 2,
                    "Text": "MSI PRO B660M-A",
                    "HardwareId": "/motherboard",
                    "ImageURL": "images_icon/mainboard.png",
                    "Children": [
                        {
                            "id": 3,
                            "Text": "Nuvoton NCT6687D",
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
                                            "SensorId": "/lpc/nct6687d/0/voltage/0",
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
                                            "SensorId": "/lpc/nct6687d/0/temperature/3",
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
                                            "SensorId": "/lpc/nct6687d/0/fan/1",
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
                    "Text": "Intel Core i5-12400",
                    "HardwareId": "/intelcpu/0",
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
                    "Text": "Crucial P3 1TB",
                    "HardwareId": "/nvme/0",
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


def _parse(data=None):
    """Parse a data.json tree with the lib, then convert it to sensors plugin rows."""
    lhm_data = LibreHardwareMonitorParser().parse_data(data or DATA_JSON_SAMPLE)
    return GlancesGrabLHM.parse(lhm_data.sensor_data.values())


def _by_label(rows):
    return {r['label']: r for r in rows}


# ---------------------------------------------------------------- parsing


def test_core_temperatures():
    rows = _by_label(_parse()['temperature_core'])
    assert set(rows) == {'CPU Package (Intel Core i5-12400)', 'SYSTIN (MSI PRO B660M-A)'}
    assert rows['CPU Package (Intel Core i5-12400)'] == {
        'label': 'CPU Package (Intel Core i5-12400)',
        'unit': 'C',
        'value': 35.5,
        'warning': None,
        'critical': None,
    }


def test_locale_decimal_separator():
    """LHM formats the values with the system locale ('29,5 °C')."""
    assert _by_label(_parse()['temperature_core'])['SYSTIN (MSI PRO B660M-A)']['value'] == 29.5


def test_pseudo_and_empty_sensors_are_excluded():
    labels = {r['label'] for rows in _parse().values() for r in rows}
    # 'Distance to TjMax' is a thermal margin, not a reading
    assert not any('TjMax' in label for label in labels)
    # 'CPU Core #1' has no value ('-')
    assert not any(label.startswith('CPU Core #1') for label in labels)
    # NVMe thresholds are not readings
    assert not any(label.startswith(('Warning', 'Critical')) for label in labels)
    # Other sensor types (voltage...) are not grabbed
    assert not any(label.startswith('Vcore') for label in labels)


def test_disk_temperatures_carry_the_nvme_thresholds():
    rows = _parse()['temperature_hdd']
    assert rows == [
        {
            'label': 'Temperature (Crucial P3 1TB)',
            'unit': 'C',
            'value': 43.0,
            'warning': 83.0,
            'critical': 87.0,
        }
    ]


def test_fans():
    rows = _parse()['fan_speed']
    assert rows == [
        {'label': 'CPU Fan (MSI PRO B660M-A)', 'unit': 'R', 'value': 1200.0, 'warning': None, 'critical': None}
    ]


def test_labels_are_unique():
    """The label is the primary key of the sensors plugin: two identical drives must not collide."""
    data = copy.deepcopy(DATA_JSON_SAMPLE)
    devices = data['Children'][0]['Children']
    disk = copy.deepcopy(devices[-1])
    disk['HardwareId'] = '/nvme/1'
    for category in disk['Children']:
        for sensor in category['Children']:
            sensor['SensorId'] = sensor['SensorId'].replace('/nvme/0/', '/nvme/1/')
    devices.append(disk)
    labels = [r['label'] for r in _parse(data)['temperature_hdd']]
    assert labels == ['Temperature (Crucial P3 1TB)', 'Temperature (Crucial P3 1TB) 2']


# ------------------------------------------------------------------ fetch


class _FakeClient:
    def __init__(self, result):
        self.result = result

    async def get_data(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.asyncio
async def test_get_returns_rows_grouped_by_type():
    grab = GlancesGrabLHM()
    grab.client = _FakeClient(LibreHardwareMonitorParser().parse_data(DATA_JSON_SAMPLE))
    rows = await grab.get()
    assert set(rows) == {'temperature_core', 'temperature_hdd', 'fan_speed'}
    assert grab.last_fetch_ok is True


@pytest.mark.asyncio
async def test_get_connection_error_returns_nothing(caplog):
    grab = GlancesGrabLHM()
    grab.client = _FakeClient(LibreHardwareMonitorConnectionError('refused'))
    with caplog.at_level('DEBUG'):
        assert await grab.get() == {}
        assert await grab.get() == {}
    assert grab.last_fetch_ok is False
    # Logged on state change only, not at each refresh
    assert len([r for r in caplog.records if 'LibreHardwareMonitor' in r.getMessage()]) == 1


# ------------------------------------------------------------ sensors plugin


@pytest.fixture
def store() -> StatsStore:
    return StatsStore()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfig()


def test_not_built_outside_windows(store, config, monkeypatch):
    monkeypatch.setattr(model, 'WINDOWS', False)
    p = PluginModel(store, config)
    p._build_grabbers()
    assert p._grab_lhm is None


def test_built_on_windows(store, config, monkeypatch):
    monkeypatch.setattr(model, 'WINDOWS', True)
    p = PluginModel(store, config)
    p._build_grabbers()
    assert p._grab_lhm.url == 'http://127.0.0.1:8085/data.json'


def test_disabled_from_the_config(store, config, monkeypatch):
    monkeypatch.setattr(model, 'WINDOWS', True)
    monkeypatch.setitem(config._merged, 'librehardwaremonitor', {'disable': 'True'})
    p = PluginModel(store, config)
    p._build_grabbers()
    assert p._grab_lhm is None


def test_not_built_without_the_lib(store, config, monkeypatch):
    monkeypatch.setattr(model, 'WINDOWS', True)
    monkeypatch.setattr(model.glances_librehardwaremonitor, 'LibreHardwareMonitorClient', None)
    p = PluginModel(store, config)
    p._build_grabbers()
    assert p._grab_lhm is None


@pytest.mark.asyncio
async def test_grab_stats_merges_the_lhm_sensors(store, config, monkeypatch):
    monkeypatch.setattr(model, 'WINDOWS', True)
    p = PluginModel(store, config)
    p._build_grabbers()
    p._grab_lhm.client = _FakeClient(LibreHardwareMonitorParser().parse_data(DATA_JSON_SAMPLE))
    rows = _by_label(await p._grab_stats())
    assert rows['CPU Package (Intel Core i5-12400)']['type'] == 'temperature_core'
    assert rows['Temperature (Crucial P3 1TB)']['type'] == 'temperature_hdd'
    assert rows['CPU Fan (MSI PRO B660M-A)']['type'] == 'fan_speed'


@pytest.mark.asyncio
async def test_lhm_failure_does_not_drop_the_other_sensors(store, config, monkeypatch):
    monkeypatch.setattr(model, 'WINDOWS', True)
    p = PluginModel(store, config)
    p._build_grabbers()

    async def _boom():
        raise RuntimeError('boom')

    monkeypatch.setattr(p._grab_lhm, 'get', _boom)
    monkeypatch.setattr(p, '_collect', lambda: [{'label': 'Battery', 'unit': '%', 'value': 80, 'type': 'battery'}])
    rows = await p._grab_stats()
    assert [r['label'] for r in rows] == ['Battery']


@pytest.mark.parametrize(('value', 'level'), [(43.0, 'ok'), (84.0, 'warning'), (88.0, 'critical')])
def test_nvme_thresholds_drive_the_alert_level(store, config, value, level):
    """Without temperature_hdd limits in the config, the drive's own thresholds apply."""
    p = PluginModel(store, config)
    row = dict(_parse()['temperature_hdd'][0], value=value, type='temperature_hdd')
    assert p._resolve_level(row) == level
