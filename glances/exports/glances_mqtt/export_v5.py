#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — MQTT export module (P3-3, wave B).

Ported from the v4 module in this directory: same `[mqtt]` section, same
topics and payloads. `topic_structure=per-metric` publishes each value on
`<topic>/<devicename>/<plugin>/<field parts>` (field parts whitelisted to
`[A-Za-z0-9_-]`); `per-plugin` publishes one JSON document per plugin on
`<topic>/<devicename>/<plugin>`, the dotted columns nested as objects. The
retained `<topic>/<devicename>/availability` topic says "online" / "offline".
`paho-mqtt` (and `certifi`, for TLS) is imported when the exporter starts,
so this module stays importable without them.
"""

from __future__ import annotations

import socket
import string
import sys
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.globals import json_dumps
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5

WHITELIST = "_-" + string.ascii_letters + string.digits


def whitelisted(s: str) -> str:
    """A topic level holds no MQTT wildcard or separator (v4)."""
    return "".join(c if c in WHITELIST else "_" for c in s)


class Export(GlancesExportBase):
    """Publish Glances stats to an MQTT broker."""

    export_name = "mqtt"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.password: str | None = None
        self.user: str | None = None
        self.topic: str | None = None
        self.devicename: str | None = None
        self.tls: Any = None
        self.topic_structure: str | None = None
        self.callback_api_version: Any = None
        if not self.load_conf(
            "mqtt",
            mandatories=("host", "password"),
            options=("port", "devicename", "user", "topic", "tls", "topic_structure", "callback_api_version"),
        ):
            logger.critical("Missing mqtt config")
            sys.exit(2)

        self.devicename = self.devicename or socket.gethostname()
        # v4 wrote `int(self.port) or 8883`, which crashed on an unset key;
        # the default it meant is applied instead. Same for callback_api_version.
        self.port = int(self.port or 8883)
        self.topic = self.topic or "glances"
        self.user = self.user or "glances"
        # An unset `tls` means NO TLS: v4 initialised it to 'true', then its
        # load_conf() overwrote it with None. Kept, so an existing plain-text
        # broker set up without the key keeps working.
        self.tls = str(self.tls).lower() == "true"
        self.topic_structure = (self.topic_structure or "per-metric").lower()
        if self.topic_structure not in ("per-metric", "per-plugin"):
            logger.critical("topic_structure must be either 'per-metric' or 'per-plugin'.")
            sys.exit(2)
        self.availability_topic = "/".join([self.topic, self.devicename, "availability"])
        self.client = self.init()

    def init(self) -> Any:
        try:
            import paho.mqtt.client as paho
        except ImportError as e:
            logger.critical("Export mqtt needs the paho-mqtt library (%s)", e)
            sys.exit(2)
        ca_file = None
        if self.tls:
            try:
                import certifi
            except ImportError as e:
                logger.critical("Export mqtt with tls=true needs the certifi library (%s)", e)
                sys.exit(2)
            ca_file = certifi.where()

        if int(self.callback_api_version or 2) == 1:
            api_version = paho.CallbackAPIVersion.VERSION1
        else:
            api_version = paho.CallbackAPIVersion.VERSION2

        # The callbacks take *args: their signature differs between callback
        # API versions 1 and 2, and v4's fixed 5-argument form failed under 1.
        def on_connect(client: Any, *args: Any) -> None:
            client.publish(topic=self.availability_topic, payload="online", retain=True)

        def on_disconnect(client: Any, *args: Any) -> None:
            client.publish(topic=self.availability_topic, payload="offline", retain=True)

        try:
            client = paho.Client(
                callback_api_version=api_version,
                client_id="glances_" + self.devicename,
                clean_session=False,
            )
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.will_set(topic=self.availability_topic, payload="offline", retain=True)
            client.username_pw_set(username=self.user, password=self.password)
            if self.tls:
                client.tls_set(ca_file)
            client.connect(host=self.host, port=self.port)
            client.loop_start()
        except Exception as e:
            logger.critical("Connection to the MQTT server %s:%s failed (%s)", self.host, self.port, e)
            sys.exit(2)
        logger.info("Stats will be exported to the MQTT server %s:%s", self.host, self.port)
        return client

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        try:
            if self.topic_structure == "per-metric":
                for column, value in zip(columns, points):
                    levels = [self.topic, self.devicename, name] + [whitelisted(part) for part in column.split(".")]
                    self.client.publish("/".join(levels), value)
            else:
                self.client.publish("/".join([self.topic, self.devicename, name]), json_dumps(nest(columns, points)))
        except Exception as e:
            logger.warning("Cannot export %s stats to MQTT (%s)", name, e)
        else:
            logger.debug("Export %s stats to MQTT", name)

    def exit(self) -> None:
        # The barrier first (see the base class). A clean disconnect does not
        # fire the will, so "offline" is published explicitly first — v4 never
        # disconnected and relied on the broker firing the will at process exit.
        super().exit()
        self.client.publish(topic=self.availability_topic, payload="offline", retain=True)
        self.client.disconnect()
        self.client.loop_stop()


def nest(columns: list[str], points: list[Any]) -> dict[str, Any]:
    """Turn `{"eth0.rx": 10}` into `{"eth0": {"rx": 10}}` (v4 per-plugin payload)."""
    output: dict[str, Any] = {}
    for column, value in zip(columns, points):
        *parents, leaf = column.split(".")
        level = output
        for parent in parents:
            level = level.setdefault(parent, {})
        level[leaf] = value
    return output
