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
import logging
from typing import Any

import pytest
import requests

from glances import client_v5
from glances.client_v5 import (
    AuthError,
    NotAGlancesV5Server,
    RemoteAlerts,
    RemoteConnection,
    RemoteError,
    RemoteSource,
    parse_target,
)
from glances.stats_store_v5 import StatsStoreV5

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


class _Response:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status_code = status
        self.ok = 200 <= status < 300
        self._body = body

    def json(self) -> Any:
        if self._body is ValueError:
            raise ValueError("not JSON")
        return self._body


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

    def post(self, url, auth=None, headers=None, timeout=None):
        self.requests.append(("POST", url, auth))
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
            return _Response(200, {"access_token": "tok", "token_type": "bearer"})
        return _Response(401)

    def get(self, url, headers=None, timeout=None):
        self.requests.append(("GET", url, headers))
        if self.down:
            raise requests.ConnectionError("connection refused")
        if self.password is not None and (headers or {}).get("Authorization") != "Bearer tok" or self.expired:
            return _Response(401)
        path = url.split("61208", 1)[1]
        return _Response(200, self.routes[path]) if path in self.routes else _Response(404)


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


def test_plain_http_with_credentials_to_a_remote_host_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="glances.client_v5"):
        RemoteConnection("http://10.0.0.5:61208", password="x")
        RemoteConnection("http://localhost:61208", password="x")
        RemoteConnection("https://10.0.0.5:61208", password="x")
    assert caplog.text.count("plain HTTP") == 1


# ------------------------------------------------------------------ source


def _source(session: _FakeSession, **kw) -> RemoteSource:
    return RemoteSource(_connection(session), StatsStoreV5(), "srv", **kw)


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


def test_a_non_v5_server_is_refused():
    session = _FakeSession()
    session.routes["/status"] = {"status": "ok", "version": "4"}
    with pytest.raises(NotAGlancesV5Server, match="not a Glances v5 server"):
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
    with caplog.at_level(logging.WARNING, logger="glances.client_v5"):
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
    from glances.outputs.curses_renderer_v5 import ColorRole
    from glances.plugins.system.render_curses_v5 import render

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

    from glances.outputs.curses_renderer_v5 import ColorRole
    from glances.plugins.system.render_curses_v5 import render

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
    from glances.main_v5 import build_parser

    args = build_parser().parse_args(["-c", "srv:61208", "-u", "admin", "--password"])
    assert (args.client, args.username, args.password_prompt) == ("srv:61208", "admin", True)


@pytest.mark.parametrize("extra", [["-s"], ["--stdout", "cpu"], ["--fetch"], ["--issue"]])
def test_client_runs_on_its_own(extra):
    from glances.main_v5 import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(["-c", "srv", *extra]))


def test_client_accepts_export():
    """Issue #1527: the client exports the server's stats (P3-2)."""
    from glances.main_v5 import build_parser, validate_args

    validate_args(build_parser().parse_args(["-c", "srv", "--export", "csv"]))


@pytest.mark.parametrize("flags", [["-u", "admin"], ["--password"]])
def test_credentials_need_client(flags):
    from glances.main_v5 import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(flags))


def test_a_wrong_password_is_fatal_before_the_tui(monkeypatch, capsys, tmp_path):
    """A clear message and exit 2, not a TUI saying "Disconnected"."""
    from glances import client_v5, main_v5
    from glances.config_v5 import GlancesConfigV5

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    def refuse(self):
        raise client_v5.AuthError("http://srv:61208 refused the username or password")

    monkeypatch.setattr(client_v5.RemoteSource, "connect", refuse)
    args = main_v5.build_parser().parse_args(["-c", "srv"])
    assert main_v5.run_client(args, GlancesConfigV5()) == 2
    assert "refused the username or password" in capsys.readouterr().err


# ------------------------------------------------------ alerts (P3-2)


def _server_incidents(history, ongoing, since, top):
    """What `/api/5/alert/incidents` serves for this engine state (routes_v5)."""
    from glances.alerts_incidents_v5 import derive_incidents, incident_duration

    incidents = derive_incidents(history, ongoing=ongoing, ongoing_since=since, ongoing_top=top)
    for incident in incidents:
        incident["duration"] = incident_duration(incident)
    return {"is_initializing": False, "incidents": incidents}


def test_the_mirrored_alerts_derive_the_servers_incidents():
    """The TUI derives its block from the adapter: it must find the server's own incidents,
    including the cases the engine's maps exist for (an evicted opening, a live top)."""
    from glances.alerts_incidents_v5 import derive_incidents

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
    store = StatsStoreV5()
    asyncio.run(store.set("mem", {"percent": 42.0, "total": 16, "_levels": {"percent": {"level": "ok"}}}))
    asyncio.run(
        store.set("network", {"data": [{"interface_name": "eth0", "bytes_recv": 10}], "_key": "interface_name"})
    )
    procs = [{"pid": 1, "name": "nginx", "cmdline": ["nginx"]}, {"pid": 2, "name": "python3", "cmdline": ["python3"]}]
    asyncio.run(store.set("processlist", {"data": procs}))
    return store


def test_remote_plugins_export_what_the_server_published():
    plugins = {p.plugin_name: p for p in client_v5.remote_plugins(_SCHEMA, _remote_store(), _config(), {"version"})}
    assert set(plugins) == {"mem", "network", "processlist"}, "a plugin not exportable locally is not either here"
    assert plugins["mem"].get_export() == {"percent": 42.0, "total": 16}, "no `_levels`"
    assert plugins["network"].IS_COLLECTION and plugins["network"]._primary_key == "interface_name"
    assert plugins["network"].get_export() == [{"interface_name": "eth0", "bytes_recv": 10}]
    assert plugins["processlist"].get_export() == [], "no process exported by default (v4 #794)"


def test_remote_processlist_export_follows_the_export_filter():
    config = _config(processlist={"export": "python.*"})
    plugins = {p.plugin_name: p for p in client_v5.remote_plugins(_SCHEMA, _remote_store(), config, set())}
    assert [p["pid"] for p in plugins["processlist"].get_export()] == [2]


def test_client_exports_only_while_connected_and_exits_the_exporters():
    from glances.main_v5 import _client_exports

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
        return client_v5.remote_plugins(_SCHEMA, store, _config(), set())

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
    with caplog.at_level(logging.WARNING, logger="glances.client_v5"):
        source.unpin_on_exit()  # the server is gone: a warning, not a crash
    assert "Cannot unpin pid 1001" in caplog.text


def _client_tui(monkeypatch, source):
    from unittest.mock import MagicMock

    from glances.outputs import glances_curses_v5 as tui_mod

    engine = tui_mod.glances_processes
    for attr, value in (("extended_pid", None), ("extended_process", None), ("disable_extended_tag", True)):
        monkeypatch.setattr(engine, attr, value, raising=False)
    monkeypatch.setattr(engine, "process_filter", None)
    config = MagicMock()
    config.get.side_effect = lambda section, key, default=None: default
    tui = tui_mod.TuiV5(store=source.store, alerts=None, config=config, registry=[], fields_by_plugin={}, remote=source)
    tui._cursor_items = [{"pid": 1000, "name": "nginx"}, {"pid": 1001, "name": "python"}]
    tui._cursor_max = 2
    popups: list[str] = []
    monkeypatch.setattr(tui, "_popup_info", lambda stdscr, message: popups.append(message))
    monkeypatch.setattr(tui, "_popup_yesno", lambda stdscr, message: pytest.fail("no confirmation expected"))
    return tui, popups


@pytest.mark.parametrize("key", ["k", "+", "-"])
def test_client_mode_refuses_the_keys_that_would_act_on_this_machine(monkeypatch, key):
    """v4 #3221: `k`, `+`, `-` would hit the CLIENT's pids. Refused, and said."""
    from glances.outputs import glances_curses_v5 as tui_mod

    for action in ("kill", "nice_increase", "nice_decrease"):
        monkeypatch.setattr(tui_mod.glances_processes, action, lambda pid: pytest.fail("acted locally"))
    tui, popups = _client_tui(monkeypatch, _source(_FakeSession()))
    assert tui._handle_key(ord(key)) == "modal"
    tui._run_pending(None)
    assert popups and "client mode" in popups[0]


def test_client_mode_e_pins_on_the_server_and_shows_its_extended_stats(monkeypatch):
    session = _FakeSession()
    source = _source(session)
    tui, popups = _client_tui(monkeypatch, source)
    assert tui._handle_key(ord("e")) == "modal"
    tui._run_pending(None)
    assert popups == []
    assert ("POST", "http://srv:61208/api/5/processes/extended/1000", None) in session.requests
    assert tui._view.extended
    assert tui._extended_payload() is None, "until the server publishes it"
    extended = {"pid": 1000, "name": "nginx", "extended_stats": True}
    asyncio.run(source.store.set("processlist", {"data": [], "extended": extended}))
    assert tui._extended_payload() == extended
    # `e` again unpins, on the server.
    tui._handle_key(ord("e"))
    tui._run_pending(None)
    assert ("POST", "http://srv:61208/api/5/processes/extended/disable", None) in session.requests
    assert not tui._view.extended


def test_client_mode_e_reports_a_refusal_from_the_server(monkeypatch):
    tui, popups = _client_tui(monkeypatch, _source(_FakeSession()))
    tui._cursor_items = [{"pid": 4242, "name": "gone"}]
    tui._handle_key(ord("e"))
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

    def get(self, url: str, headers: dict | None = None, timeout: float | None = None) -> _Response:
        return self._wrap(self._http.get(url, headers=headers))

    def post(self, url: str, auth: Any = None, headers: dict | None = None, timeout: float | None = None) -> _Response:
        return self._wrap(self._http.post(url, auth=auth, headers=headers))


def test_against_a_real_v5_app(tmp_path, monkeypatch):
    """The source reads what a real `build_app` serves, through `requests`' API."""
    from fastapi.testclient import TestClient

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.mem.model_v5 import PluginModel as Mem
    from glances.webserver_v5 import build_app, register_plugin

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config = GlancesConfigV5()
    server_store = StatsStoreV5()
    mem = Mem(server_store, config)
    asyncio.run(mem.update())
    app = build_app(config=config, store=server_store)
    register_plugin(app, mem)

    with TestClient(app, base_url="http://srv:61208") as http:
        conn = RemoteConnection("http://srv:61208")
        conn._session = _TestClientSession(http)
        source = RemoteSource(conn, StatsStoreV5(), "srv")
        source.connect()
        asyncio.run(source.poll_once())
    assert ("mem", False) in source.registry
    assert source.store.get("mem")["percent"] == server_store.get("mem")["percent"]
    assert "_levels" in source.store.get("mem"), "the server's levels colour the client"


def test_run_client_reads_passwords_from_a_real_config(tmp_path, monkeypatch):
    """P3-1 regression: `[passwords] <host>` set in the file made `config.get(..., None)` raise."""
    from glances import main_v5
    from glances.config_v5 import GlancesConfigV5

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    conf = tmp_path / "glances.conf"
    conf.write_text("[passwords]\nsrv=pw\n")
    seen = []
    monkeypatch.setattr(main_v5, "open_client", lambda args, config, target, user, password: seen.append(password))
    args = main_v5.build_parser().parse_args(["-c", "srv"])
    assert main_v5.run_client(args, GlancesConfigV5(str(conf))) == 0
    assert seen == ["pw"]
