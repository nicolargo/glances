#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — wave B exporters (P3-3): kafka, mqtt, nats, rabbitmq, zeromq.

Each client library is faked: the tests assert on what reaches it.
"""

from __future__ import annotations

import importlib
import json
import logging
import re
import types

import pytest

from tests.export_fakes_v5 import HOSTILE_NAME, fake_module, make_config, missing_module, plugins

# HOSTILE_NAME as one MQTT topic level: everything outside [A-Za-z0-9_-] is "_".
HOSTILE_LEVEL = re.sub(r"[^A-Za-z0-9_-]", "_", HOSTILE_NAME)

SECTIONS = {
    "kafka": {"host": "kb", "port": "9092", "topic": "glances"},
    "mqtt": {"host": "broker", "password": "pw-from-config"},
    "nats": {"host": "nats://a:4222"},
    "rabbitmq": {"host": "rmq", "port": "5672", "user": "guest", "password": "pw-from-config", "queue": "q"},
    "zeromq": {"host": "*", "port": "5678", "prefix": "G"},
}


class _Recorder:
    """A client that records every call, by method name."""

    instances: list[_Recorder] = []
    failing: frozenset[str] = frozenset()

    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs
        self.calls: list[tuple[str, tuple, dict]] = []
        _Recorder.instances.append(self)

    def __getattr__(self, method):
        def call(*args, **kwargs):
            self.calls.append((method, args, kwargs))
            if method in self.failing:
                raise OSError("network down")

        return call

    def sent(self, method):
        return [(args, kwargs) for name, args, kwargs in self.calls if name == method]


class _Broken(_Recorder):
    failing = frozenset({"send", "publish", "basic_publish", "send_multipart"})


class _FakeNats:
    """nats.aio.client.Client: every method is a coroutine."""

    instances: list[_FakeNats] = []
    fail_publish = False

    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []
        _FakeNats.instances.append(self)

    def __getattr__(self, method):
        async def call(*args, **kwargs):
            self.calls.append((method, args, kwargs))
            if method == "publish" and self.fail_publish:
                raise OSError("network down")

        return call


@pytest.fixture(autouse=True)
def _reset():
    _Recorder.instances = []
    _FakeNats.instances = []


def _values(recorder, method):
    return [kwargs.get("value") for _, kwargs in recorder.sent(method)]


# ------------------------------------------------------------------ fakes


def _fake_kafka(monkeypatch, cls=_Recorder):
    fake_module(monkeypatch, "kafka", KafkaProducer=cls)


def _fake_mqtt(monkeypatch, cls=_Recorder):
    versions = types.SimpleNamespace(VERSION1="v1", VERSION2="v2")
    fake_module(monkeypatch, "paho.mqtt.client", Client=cls, CallbackAPIVersion=versions)
    fake_module(monkeypatch, "certifi", where=lambda: "/ca.pem")


def _fake_nats(monkeypatch, cls=_FakeNats):
    fake_module(monkeypatch, "nats.aio.client", Client=cls)
    # Only for the v4 package __init__, which imports these at module level.
    fake_module(monkeypatch, "nats.errors", ConnectionClosedError=OSError, TimeoutError=TimeoutError)


def _fake_rabbitmq(monkeypatch, cls=_Recorder):
    class Connection(_Recorder):
        def channel(self):
            return cls()

    fake_module(monkeypatch, "pika", URLParameters=_Recorder, BlockingConnection=Connection)


def _fake_zeromq(monkeypatch, cls=_Recorder):
    class Context(_Recorder):
        def socket(self, kind):
            assert kind == "PUB"
            return cls()

    fake_module(monkeypatch, "zmq", Context=Context, PUB="PUB")


FAKES = {
    "kafka": _fake_kafka,
    "mqtt": _fake_mqtt,
    "nats": _fake_nats,
    "rabbitmq": _fake_rabbitmq,
    "zeromq": _fake_zeromq,
}


def _exporter(name, overrides=None):
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    config = make_config({name: {**SECTIONS[name], **(overrides or {})}})
    return module.Export(config), config


# ------------------------------------------------------------------ kafka


def test_kafka_sends_one_json_message_per_plugin_keyed_by_name(monkeypatch):
    _fake_kafka(monkeypatch)
    exporter, config = _exporter("kafka", {"compression": "gzip", "tags": "env:prod"})
    exporter.update(plugins(config))
    producer = _Recorder.instances[0]
    assert producer.kwargs["bootstrap_servers"] == "kb:9092"
    assert producer.kwargs["compression_type"] == "gzip"
    assert producer.kwargs["value_serializer"]({"a": 1}) == b'{"a": 1}'

    sends = producer.sent("send")
    assert [args for args, _ in sends] == [("glances",), ("glances",)]
    assert [kwargs["key"] for _, kwargs in sends] == [b"fakescalar", b"fakecollection"]
    scalar, collection = _values(producer, "send")
    assert {k: scalar[k] for k in ("total", "label", "missing", "env")} == {
        "total": 12.5,
        "label": "busy host",
        "missing": None,
        "env": "prod",
    }
    assert collection["eth0.rx"] == 10 and collection[f"{HOSTILE_NAME}.rx"] == 20
    assert collection["eth0.name"] == "eth0" and collection["eth0.key"] == "name"

    exporter.exit()
    assert [c[0] for c in producer.calls[-2:]] == ["flush", "close"]


# ------------------------------------------------------------------- mqtt


def test_mqtt_client_is_built_from_the_config(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    _fake_mqtt(monkeypatch)
    _exporter("mqtt", {"port": "1883", "devicename": "box", "user": "u", "tls": "True"})
    client = _Recorder.instances[0]
    assert client.kwargs == {"callback_api_version": "v2", "client_id": "glances_box", "clean_session": False}
    assert [c[0] for c in client.calls] == ["will_set", "username_pw_set", "tls_set", "connect", "loop_start"]
    assert client.sent("will_set") == [
        ((), {"topic": "glances/box/availability", "payload": "offline", "retain": True})
    ]
    assert client.sent("username_pw_set") == [((), {"username": "u", "password": "pw-from-config"})]
    assert client.sent("tls_set") == [(("/ca.pem",), {})]
    assert client.sent("connect") == [((), {"host": "broker", "port": 1883})]
    assert "pw-from-config" not in caplog.text


def test_mqtt_defaults_match_v4(monkeypatch):
    _fake_mqtt(monkeypatch)
    exporter, _ = _exporter("mqtt", {"callback_api_version": "1"})
    client = _Recorder.instances[0]
    assert client.kwargs["callback_api_version"] == "v1"
    assert client.sent("connect") == [((), {"host": "broker", "port": 8883})]
    assert client.sent("username_pw_set")[0][1]["username"] == "glances"
    assert not client.sent("tls_set"), "an unset tls key means no TLS, as in v4"
    assert exporter.availability_topic.startswith("glances/")


def test_mqtt_per_metric_publishes_one_topic_per_field(monkeypatch):
    _fake_mqtt(monkeypatch)
    exporter, config = _exporter("mqtt", {"devicename": "box"})
    exporter.update(plugins(config))
    published = {args[0]: args[1] for args, _ in _Recorder.instances[0].sent("publish")}
    assert published["glances/box/fakescalar/total"] == 12.5
    assert published["glances/box/fakescalar/label"] == "busy host"
    assert published["glances/box/fakescalar/missing"] is None
    assert published["glances/box/fakecollection/eth0/rx"] == 10
    assert published[f"glances/box/fakecollection/{HOSTILE_LEVEL}/rx"] == 20
    assert all(topic.count("/") in (3, 4) for topic in published), "no level injected by a hostile name"


def test_mqtt_per_plugin_publishes_one_nested_json_per_plugin(monkeypatch):
    _fake_mqtt(monkeypatch)
    exporter, config = _exporter("mqtt", {"devicename": "box", "topic": "t", "topic_structure": "Per-Plugin"})
    exporter.update(plugins(config))
    published = {args[0]: json.loads(args[1]) for args, _ in _Recorder.instances[0].sent("publish")}
    assert set(published) == {"t/box/fakescalar", "t/box/fakecollection"}
    scalar = published["t/box/fakescalar"]
    assert (scalar["total"], scalar["label"], scalar["missing"]) == (12.5, "busy host", None)
    collection = published["t/box/fakecollection"]
    assert collection["eth0"]["rx"] == 10 and collection[HOSTILE_NAME]["rx"] == 20


def test_mqtt_rejects_an_unknown_topic_structure(monkeypatch):
    _fake_mqtt(monkeypatch)
    with pytest.raises(SystemExit):
        _exporter("mqtt", {"topic_structure": "flat"})


def test_mqtt_exit_says_offline_then_disconnects(monkeypatch):
    _fake_mqtt(monkeypatch)
    exporter, _ = _exporter("mqtt", {"devicename": "box"})
    exporter.exit()
    client = _Recorder.instances[0]
    assert client.calls[-3:] == [
        ("publish", (), {"topic": "glances/box/availability", "payload": "offline", "retain": True}),
        ("disconnect", (), {}),
        ("loop_stop", (), {}),
    ]


# ------------------------------------------------------------------- nats


def test_nats_publishes_json_on_prefixed_subjects_from_a_worker_thread(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    _fake_nats(monkeypatch)
    exporter, config = _exporter("nats", {"host": "nats://u:pw-from-config@a:4222, nats://b:4222", "prefix": "g"})
    try:
        exporter.update(plugins(config))
    finally:
        exporter.exit()
    client = _FakeNats.instances[0]
    connect = client.calls[0]
    assert connect[0] == "connect"
    assert connect[2]["servers"] == ["nats://u:pw-from-config@a:4222", "nats://b:4222"]
    assert "pw-from-config" not in caplog.text

    published = {args[0]: json.loads(args[1]) for name, args, _ in client.calls if name == "publish"}
    assert set(published) == {"g.fakescalar", "g.fakecollection"}
    scalar = published["g.fakescalar"]
    assert (scalar["total"], scalar["label"], scalar["missing"]) == (12.5, "busy host", None)
    assert published["g.fakecollection"][f"{HOSTILE_NAME}.rx"] == 20
    assert [name for name, _, _ in client.calls[-2:]] == ["drain", "close"]
    assert not exporter._thread.is_alive() and exporter._loop.is_closed()


def test_nats_unreachable_at_start_is_not_fatal(monkeypatch, caplog):
    class Unreachable(_FakeNats):
        async def connect(self, **kwargs):
            raise OSError("no servers")

    _fake_nats(monkeypatch, Unreachable)
    exporter, config = _exporter("nats")
    try:
        exporter.update(plugins(config))
    finally:
        exporter.exit()
    assert "Cannot export fakescalar stats to NATS (not connected)" in caplog.text
    assert [name for name, _, _ in _FakeNats.instances[0].calls] == ["close"]


# --------------------------------------------------------------- rabbitmq


def test_rabbitmq_publishes_the_v4_text_line_to_the_queue(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    _fake_rabbitmq(monkeypatch)
    exporter, config = _exporter("rabbitmq", {"protocol": "AMQPS"})
    exporter.update(plugins(config))
    parameters, connection, channel = _Recorder.instances
    assert parameters.args == ("amqps://guest:pw-from-config@rmq:5672/",)
    assert connection.args == (parameters,)
    assert "pw-from-config" not in caplog.text

    bodies = []
    for args, kwargs in channel.sent("basic_publish"):
        assert args == () and kwargs["exchange"] == "" and kwargs["routing_key"] == "q"
        bodies.append(kwargs["body"])
    scalar, collection = bodies
    assert re.match(rf"hostname={re.escape(exporter.hostname)}, name=fakescalar, dateinfo=\d{{4}}-[^,+]+, ", scalar)
    assert ", total=12.5" in scalar and "label" not in scalar and "missing" not in scalar, "numbers only"
    assert ", eth0.rx=10" in collection and f", {HOSTILE_NAME}.rx=20" in collection

    exporter.exit()
    assert connection.calls[-1][0] == "close"


# ----------------------------------------------------------------- zeromq


def test_zeromq_publishes_three_frames_per_plugin(monkeypatch):
    _fake_zeromq(monkeypatch)
    exporter, config = _exporter("zeromq")
    exporter.update(plugins(config))
    context, socket = _Recorder.instances
    assert socket.sent("bind") == [(("tcp://*:5678",), {})]

    frames = [args[0] for args, _ in socket.sent("send_multipart")]
    assert [f[:2] for f in frames] == [[b"G", b"fakescalar"], [b"G", b"fakecollection"]]
    scalar, collection = (json.loads(f[2]) for f in frames)
    assert (scalar["total"], scalar["label"], scalar["missing"]) == (12.5, "busy host", None)
    assert collection["eth0.rx"] == 10 and collection[f"{HOSTILE_NAME}.rx"] == 20

    exporter.exit()
    assert socket.calls[-1][0] == "close" and context.calls[-1][0] == "destroy"


# ------------------------------------------------------------------ common


@pytest.mark.parametrize(
    ("name", "library", "logged"),
    [
        ("kafka", "kafka", "kafka-python"),
        ("mqtt", "paho.mqtt.client", "paho-mqtt"),
        ("nats", "nats.aio.client", "nats-py"),
        ("rabbitmq", "pika", "pika"),
        ("zeromq", "zmq", "pyzmq"),
    ],
)
def test_a_missing_section_or_library_is_fatal_and_says_so(monkeypatch, caplog, name, library, logged):
    # The fake is needed to import the module at all: the v4 package
    # __init__.py next to it imports the library at module level.
    FAKES[name](monkeypatch)
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    with pytest.raises(SystemExit):
        module.Export(make_config({}))
    assert f"Missing {name} config" in caplog.text
    missing_module(monkeypatch, library)
    with pytest.raises(SystemExit):
        module.Export(make_config({name: SECTIONS[name]}))
    assert logged in caplog.text


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_a_missing_mandatory_key_is_fatal(monkeypatch, name):
    FAKES[name](monkeypatch)
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    section = dict(SECTIONS[name])
    section.pop(next(iter(section)))
    with pytest.raises(SystemExit):
        module.Export(make_config({name: section}))


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_a_failing_send_is_one_warning_per_plugin_not_a_crash(monkeypatch, caplog, name):
    if name == "nats":
        monkeypatch.setattr(_FakeNats, "fail_publish", True)
        _fake_nats(monkeypatch)
    else:
        FAKES[name](monkeypatch, _Broken)
    exporter, config = _exporter(name)
    try:
        exporter.update(plugins(config))
    finally:
        if name == "nats":
            exporter.exit()  # stops the loop thread
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    for plugin in ("fakescalar", "fakecollection"):
        assert sum(m.startswith(f"Cannot export {plugin} stats to ") for m in warnings) == 1, warnings


def test_the_exporters_are_discovered_by_export(monkeypatch):
    from glances.main_v5 import apply_export_flags, build_parser, discover_exporters

    for fake in FAKES.values():
        fake(monkeypatch)
    args = build_parser().parse_args(["--export", ",".join(SECTIONS)])
    apply_export_flags(args)
    exporters = discover_exporters(make_config(SECTIONS), args)
    try:
        assert sorted(e.export_name for e in exporters) == sorted(SECTIONS)
    finally:
        for exporter in exporters:
            exporter.exit()
