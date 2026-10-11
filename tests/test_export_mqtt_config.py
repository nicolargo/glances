# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""Regression tests for the optional keys of the MQTT export configuration."""

from unittest import mock

import pytest

paho = pytest.importorskip("paho.mqtt.client")

from glances.exports.glances_mqtt import Export  # noqa: E402


class FakeConfig:
    """Minimal config exposing only the [mqtt] keys given to it."""

    def __init__(self, values):
        self.values = values

    def get_value(self, section, option, default=None):
        return self.values.get(option, default) if section == 'mqtt' else default

    def get_list_value(self, section, option, default=None, separator=','):
        return default


def make_export(values):
    with mock.patch('glances.exports.glances_mqtt.paho.Client') as client_cls:
        exporter = Export(config=FakeConfig(values))
    return exporter, client_cls


def test_port_and_callback_api_version_are_optional():
    exporter, client_cls = make_export({'host': 'localhost', 'password': 'secret', 'tls': 'false'})

    assert exporter.port == 8883
    assert exporter.callback_api_version == paho.CallbackAPIVersion.VERSION2
    client_cls.return_value.connect.assert_called_once_with(host='localhost', port=8883)


def test_configured_port_and_callback_api_version_are_used():
    exporter, client_cls = make_export(
        {'host': 'localhost', 'password': 'secret', 'tls': 'false', 'port': '1883', 'callback_api_version': '1'}
    )

    assert exporter.port == 1883
    assert exporter.callback_api_version == paho.CallbackAPIVersion.VERSION1
    client_cls.return_value.connect.assert_called_once_with(host='localhost', port=1883)
