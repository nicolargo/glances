#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — wave A exporters (P3-3): graphite, statsd, opentsdb, riemann.

Each client library is faked: the tests assert on what reaches it.
"""

from __future__ import annotations

import pytest

from tests.export_fakes_v5 import HOSTILE_NAME, fake_module, make_config, missing_module, plugins


class _Recorder:
    """A client that records every call, by method name."""

    instances: list[_Recorder] = []

    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs
        self.calls: list[tuple[str, tuple, dict]] = []
        _Recorder.instances.append(self)

    def __getattr__(self, method):
        return lambda *args, **kwargs: self.calls.append((method, args, kwargs))


@pytest.fixture(autouse=True)
def _reset():
    _Recorder.instances = []


# --------------------------------------------------------------- graphite


def test_graphite_sends_numbers_under_v4_names(monkeypatch):
    fake_module(monkeypatch, "graphitesend", GraphiteClient=_Recorder)
    from glances.exports.glances_graphite.export_v5 import Export

    config = make_config({"graphite": {"host": "carbon", "port": "2003", "system_name": "box"}})
    Export(config).update(plugins(config))
    client = _Recorder.instances[0]
    assert client.kwargs == {
        "graphite_server": "carbon",
        "graphite_port": 2003,
        "prefix": "glances",
        "lowercase_metric_names": True,
        "system_name": "box",
    }
    sent = {k: v for method, args, _ in client.calls if method == "send_dict" for k, v in args[0].items()}
    assert sent["fakescalar.total"] == 12.5
    assert "fakescalar.label" not in sent and "fakescalar.missing" not in sent, "numbers only"
    assert sent["fakecollection.eth0.rx"] == 10
    assert all(" " not in name for name in sent), "no space in a Graphite name"


# ----------------------------------------------------------------- statsd


def test_statsd_sends_one_gauge_per_number(monkeypatch):
    fake_module(monkeypatch, "statsd", StatsClient=_Recorder)
    from glances.exports.glances_statsd.export_v5 import Export

    config = make_config({"statsd": {"host": "sd", "port": "8125", "prefix": "g"}})
    Export(config).update(plugins(config))
    client = _Recorder.instances[0]
    assert client.args == ("sd", 8125) and client.kwargs == {"prefix": "g"}
    gauges = {args[0]: args[1] for method, args, _ in client.calls if method == "gauge"}
    assert gauges["fakescalar.total"] == 12.5
    assert gauges["fakecollection.eth0.rx"] == 10
    assert all(":" not in n and "%" not in n and " " not in n for n in gauges), "v4 #1068"


# --------------------------------------------------------------- opentsdb


def test_opentsdb_sends_prefixed_points_with_tags_and_drains_on_exit(monkeypatch):
    fake_module(monkeypatch, "potsdb", Client=_Recorder)
    from glances.exports.glances_opentsdb.export_v5 import Export

    config = make_config({"opentsdb": {"host": "tsdb", "port": "4242", "tags": "env:prod,dc:par"}})
    exporter = Export(config)
    exporter.update(plugins(config))
    client = _Recorder.instances[0]
    assert client.args == ("tsdb",) and client.kwargs == {"port": 4242, "check_host": True}
    sends = [(args, kwargs) for method, args, kwargs in client.calls if method == "send"]
    assert (("glances.fakescalar.total", 12.5), {"env": "prod", "dc": "par"}) in sends
    exporter.exit()
    assert client.calls[-1][0] == "wait"


# ---------------------------------------------------------------- riemann


def test_riemann_sends_one_event_per_number(monkeypatch):
    fake_module(monkeypatch, "bernhard", Client=_Recorder)
    from glances.exports.glances_riemann.export_v5 import Export

    config = make_config({"riemann": {"host": "rie", "port": "5555"}})
    exporter = Export(config)
    exporter.update(plugins(config))
    client = _Recorder.instances[0]
    assert client.kwargs == {"host": "rie", "port": 5555}
    events = [args[0] for method, args, _ in client.calls if method == "send"]
    assert {"host": exporter.hostname, "service": "fakescalar total", "metric": 12.5} in events
    assert {"host": exporter.hostname, "service": f"fakecollection {HOSTILE_NAME}.rx", "metric": 20} in events


# ------------------------------------------------------------------ common


@pytest.mark.parametrize(
    ("name", "library"),
    [("graphite", "graphitesend"), ("statsd", "statsd"), ("opentsdb", "potsdb"), ("riemann", "bernhard")],
)
def test_a_missing_section_or_library_is_fatal_and_says_so(monkeypatch, caplog, name, library):
    import importlib

    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    with pytest.raises(SystemExit):
        module.Export(make_config({}))
    missing_module(monkeypatch, library)
    with pytest.raises(SystemExit):
        module.Export(make_config({name: {"host": "h", "port": "1"}}))
    assert library in caplog.text


def test_a_failing_send_is_a_warning_not_a_crash(monkeypatch, caplog):
    class Broken(_Recorder):
        def gauge(self, *args):
            raise OSError("network down")

    fake_module(monkeypatch, "statsd", StatsClient=Broken)
    from glances.exports.glances_statsd.export_v5 import Export

    config = make_config({"statsd": {"host": "sd", "port": "8125"}})
    Export(config).update(plugins(config))
    assert "Cannot export fakescalar stats to StatsD" in caplog.text


def test_the_exporters_are_discovered_by_export(monkeypatch):
    from glances.main_v5 import apply_export_flags, build_parser, discover_exporters

    for library, attr in (
        ("graphitesend", "GraphiteClient"),
        ("statsd", "StatsClient"),
        ("potsdb", "Client"),
        ("bernhard", "Client"),
    ):
        fake_module(monkeypatch, library, **{attr: _Recorder})
    args = build_parser().parse_args(["--export", "graphite,statsd,opentsdb,riemann"])
    apply_export_flags(args)
    sections = {n: {"host": "h", "port": "1"} for n in ("graphite", "statsd", "opentsdb", "riemann")}
    assert sorted(e.export_name for e in discover_exporters(make_config(sections), args)) == [
        "graphite",
        "opentsdb",
        "riemann",
        "statsd",
    ]
