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


@pytest.mark.parametrize('callback, payload', [('on_connect', 'online'), ('on_disconnect', 'offline')])
def test_callback_firing_before_init_returns_uses_callback_client(callback, payload):
    """Regression test for https://github.com/nicolargo/glances/issues/3843.

    loop_start() spawns the paho network thread inside init(), so a callback
    can fire before self.client is bound. The callback must publish on the
    client paho hands it, not on self.client.
    """
    with mock.patch('glances.exports.glances_mqtt.paho.Client') as client_cls:
        client_instance = client_cls.return_value

        def fire_callback(*args, **kwargs):
            getattr(client_instance, callback)(client_instance, None, {}, 0, None)

        client_instance.loop_start.side_effect = fire_callback
        exporter = Export(config=FakeConfig({'host': 'localhost', 'password': 'secret', 'tls': 'false'}))

    assert exporter.client is client_instance
    client_instance.publish.assert_called_once_with(
        topic='/'.join(['glances', exporter.devicename, 'availability']), payload=payload, retain=True
    )
