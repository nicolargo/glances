#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the browser's server list, its poller and `/api/5/serverslist` (P3-4)."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
import requests

from glances import servers_list_v5 as sl
from glances.servers_list_v5 import Column, ServerEntry, parse_columns


class _Config:
    def __init__(self, **sections: dict[str, Any]) -> None:
        self._sections = sections

    def get(self, section, key, default=None):
        return self._sections.get(section, {}).get(key, default)

    def get_value(self, section, key):
        return self._sections.get(section, {}).get(key)


class _Response:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status_code = status
        self.ok = 200 <= status < 300
        self._body = body

    def json(self) -> Any:
        return self._body


class _Server:
    """What one fake server answers, by path."""

    def __init__(self, routes=None, password=None, down=False):
        self.routes = routes or {}
        self.password = password
        self.down = down


class _Network:
    """Every fake server, by base URL; stands in for each connection's `requests.Session`."""

    def __init__(self, servers: dict[str, _Server]) -> None:
        self.servers = servers
        self.sent: list[tuple[str, Any]] = []

    def session(self, base_url: str):
        network = self

        class _Session:
            verify = True

            def post(self, url, auth=None, headers=None, timeout=None):
                network.sent.append((url, auth))
                server = network.servers[base_url]
                if server.password is None:
                    return _Response(404)
                return (
                    _Response(200, {"access_token": "tok"}) if auth and auth[1] == server.password else _Response(401)
                )

            def get(self, url, headers=None, timeout=None):
                network.sent.append((url, headers))
                server = network.servers[base_url]
                if server.down:
                    raise requests.ConnectionError("refused")
                path = url[len(base_url) :]
                if server.password and path != "/status" and (headers or {}).get("Authorization") != "Bearer tok":
                    return _Response(401)
                return _Response(200, server.routes[path]) if path in server.routes else _Response(404)

        return _Session()


@pytest.fixture
def network(monkeypatch):
    net = _Network({})
    real = sl.RemoteConnection

    def connection(base_url, **kwargs):
        conn = real(base_url, **kwargs)
        conn._session = net.session(base_url)
        return conn

    monkeypatch.setattr(sl, "RemoteConnection", connection)
    return net


_V5 = {
    "/status": {"version": "5"},
    "/api/5/cpu": {"total": 12.5, "_levels": {"total": {"level": "careful"}}},
    "/api/5/sensors": {
        "data": [{"label": "Ambient", "value": 41}],
        "_key": "label",
        "_levels": {"Ambient": {"value": {"level": "warning"}}},
    },
}
_COLUMNS = [Column("cpu", "total"), Column("sensors", "value", "ambient"), Column("gpu", "proc")]


# ------------------------------------------------------------- the list


def test_the_static_list_reads_v4s_layout(caplog):
    config = _Config(
        serverlist={
            "server_1_name": "alpha",
            "server_1_alias": "Alpha box",
            "server_2_name": "beta",
            "server_2_port": "61237",
            "server_2_protocol": "rpc",
            "server_4_name": "https://gamma.example/glances",
            "server_5_name": "delta",
            "server_5_port": "not-a-port",
        }
    )
    with caplog.at_level(logging.WARNING, logger="glances.servers_list_v5"):
        servers = sl.load_static_servers(config)
    assert [(s.name, s.port, s.alias) for s in servers] == [
        ("alpha", 61208, "Alpha box"),
        ("beta", 61237, None),
        ("https://gamma.example/glances", 61208, None),
    ]
    assert [s.target for s in servers] == ["alpha:61208", "beta:61237", "https://gamma.example/glances"]
    assert all(s.status == sl.UNKNOWN for s in servers), "nothing is known before the first round"
    assert "server_2_protocol is ignored" in caplog.text
    assert "server_5 skipped" in caplog.text


def test_columns_parse_v4s_syntax(caplog):
    with caplog.at_level(logging.WARNING, logger="glances.servers_list_v5"):
        columns = parse_columns("system:hr_name, sensors:value:Ambient,oops,cpu:")
    assert columns == [Column("system", "hr_name"), Column("sensors", "value", "Ambient")]
    assert columns[1].label == "sensors:value:Ambient"
    assert caplog.text.count("skipped") == 2


# ----------------------------------------------------------- the poller


def _poll(network, server: _Server, config=None, name="alpha") -> ServerEntry:
    network.servers[f"http://{name}:61208"] = server
    entry = ServerEntry(name=name, port=61208)
    sl.ServersPoller([entry], config or _Config(), _COLUMNS).poll_round()
    return entry


def test_an_online_server_gets_its_columns_and_their_levels(network):
    entry = _poll(network, _Server(dict(_V5)))
    assert entry.status == sl.ONLINE
    assert entry.columns == {
        "cpu:total": {"value": 12.5, "level": "careful"},
        # The key matches case-insensitively, as in v4.
        "sensors:value:ambient": {"value": 41, "level": "warning"},
    }, "gpu is not served (404): its column stays empty, the server stays online"


@pytest.mark.parametrize(
    ("server", "status"),
    [
        (_Server(down=True), sl.OFFLINE),
        (_Server({"/status": {"version": "4"}}), sl.UNSUPPORTED),
        (_Server({}), sl.UNSUPPORTED),  # a v4 server has no /status
        (_Server(dict(_V5), password="secret"), sl.PROTECTED),
    ],
)
def test_the_status_of_a_server(network, server, status):
    assert _poll(network, server).status == status


def test_a_configured_password_opens_a_protected_server(network):
    config = _Config(passwords={"alpha": "secret"})
    assert _poll(network, _Server(dict(_V5), password="secret"), config).status == sl.ONLINE
    config = _Config(passwords={"default": "secret"})
    assert _poll(network, _Server(dict(_V5), password="secret"), config, name="beta").status == sl.ONLINE
    # No -u: the token request names v4's default user.
    assert {auth for url, auth in network.sent if url.endswith("/api/5/token")} == {("glances", "secret")}


def test_a_typed_password_is_used_from_the_next_round(network):
    network.servers["http://alpha:61208"] = _Server(dict(_V5), password="secret")
    entry = ServerEntry(name="alpha", port=61208)
    poller = sl.ServersPoller([entry], _Config(), _COLUMNS)
    poller.poll_round()
    assert entry.status == sl.PROTECTED
    poller.set_password(entry, "secret")
    assert poller.password_for(entry) == "secret"
    poller.poll_round()
    assert entry.status == sl.ONLINE


def test_a_non_static_server_gets_no_configured_password():
    """The rule P3-5 relies on (CVE-2026-32634): only static entries read [passwords]."""
    poller = sl.ServersPoller([], _Config(passwords={"alpha": "secret", "default": "x"}), [])
    assert poller.password_for(ServerEntry(name="alpha", port=61208)) == "secret"
    assert poller.password_for(ServerEntry(name="alpha", port=61208, source="zeroconf")) is None


def test_without_a_default_password_an_unlisted_host_gets_none():
    poller = sl.ServersPoller([], _Config(passwords={"alpha": "x"}), [])
    assert poller.password_for(ServerEntry(name="beta", port=61208)) is None


# ------------------------------------------------ /api/5/serverslist


def _app(config, store, poller=None):
    from glances.webserver_v5 import build_app

    app = build_app(config=config, store=store)
    if poller is not None:
        app.state.servers_poller = poller
    return app


def test_serverslist_never_carries_a_credential(network, tmp_path, monkeypatch):
    """CVE-2026-32633: v4 served each server's `uri`, which carried the password hash."""
    from fastapi.testclient import TestClient

    from glances.config_v5 import GlancesConfigV5
    from glances.stats_store_v5 import StatsStoreV5

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    network.servers["http://alpha:61208"] = _Server(dict(_V5), password="s3cr3t-pw")
    config = _Config(serverlist={"server_1_name": "alpha", "server_1_alias": "A"}, passwords={"alpha": "s3cr3t-pw"})
    poller = sl.build_poller(config)
    poller.columns = _COLUMNS
    poller.poll_round()

    with TestClient(_app(GlancesConfigV5(), StatsStoreV5(), poller)) as client:
        response = client.get("/api/5/serverslist")
    assert response.status_code == 200
    [item] = response.json()
    assert set(item) == {"name", "alias", "port", "status", "source", "columns"}
    assert item["status"] == sl.ONLINE and item["columns"]["cpu:total"]["value"] == 12.5
    text = json.dumps(response.json())
    for leak in ("s3cr3t-pw", "password", "uri", "username", "Bearer", "tok"):
        assert leak not in text, leak


def test_serverslist_stays_stable_and_clean_over_rounds(network, tmp_path, monkeypatch):
    """v4 `TestServersListStability`: the count does not drift round after
    round, and a password typed after the first round never shows either."""
    from fastapi.testclient import TestClient

    from glances.config_v5 import GlancesConfigV5
    from glances.stats_store_v5 import StatsStoreV5

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    network.servers["http://alpha:61208"] = _Server(dict(_V5), password="s3cr3t-pw")
    network.servers["http://beta:61208"] = _Server(dict(_V5), password="typed-pw")
    config = _Config(serverlist={"server_1_name": "alpha", "server_2_name": "beta"}, passwords={"alpha": "s3cr3t-pw"})
    poller = sl.build_poller(config)
    poller.columns = _COLUMNS

    with TestClient(_app(GlancesConfigV5(), StatsStoreV5(), poller)) as client:
        poller.poll_round()
        poller.set_password(poller.servers[1], "typed-pw")
        for _ in range(3):
            poller.poll_round()
            items = client.get("/api/5/serverslist").json()
            assert len(items) == 2
            assert [i["status"] for i in items] == [sl.ONLINE, sl.ONLINE]
            text = json.dumps(items)
            for leak in ("s3cr3t-pw", "typed-pw", "password", "Bearer", "tok"):
                assert leak not in text, leak


def test_serverslist_is_404_without_browser_mode(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from glances.config_v5 import GlancesConfigV5
    from glances.stats_store_v5 import StatsStoreV5

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with TestClient(_app(GlancesConfigV5(), StatsStoreV5())) as client:
        response = client.get("/api/5/serverslist")
    assert response.status_code == 404
    assert "--browser" in response.json()["detail"]


# ------------------------------------------------------------------ CLI


@pytest.mark.parametrize("extra", [["-c", "srv"], ["--stdout", "cpu"], ["--fetch"], ["--issue"]])
def test_browser_runs_on_its_own_or_with_server(extra):
    from glances.main_v5 import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(["--browser", *extra]))
    validate_args(build_parser().parse_args(["--browser"]))
    validate_args(build_parser().parse_args(["-s", "--browser"]))


def test_username_goes_with_client_or_browser_and_password_with_client_only():
    from glances.main_v5 import build_parser, validate_args

    validate_args(build_parser().parse_args(["--browser", "-u", "admin"]))
    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(["--browser", "--password"]))


# ---------------------------------------------------------- the screen


def _entries():
    return [
        ServerEntry(
            name="alpha",
            port=61208,
            alias="Alpha box",
            status=sl.ONLINE,
            columns={"cpu:total": {"value": 92.25, "level": "critical"}},
        ),
        ServerEntry(name="beta", port=61208, status=sl.OFFLINE),
        ServerEntry(name="gamma", port=61208, status=sl.PROTECTED),
    ]


def test_the_screen_is_v4s_layout_in_the_tuis_colours():
    from glances.outputs.browser_curses_v5 import build_lines
    from glances.outputs.curses_renderer_v5 import ColorRole

    lines = build_lines(_entries(), [Column("cpu", "total"), Column("sensors", "value", "Ambient")], cursor=1)
    text = ["".join(c.text for c in line).rstrip() for line in lines]
    assert text[0] == "3 Glances servers available"
    assert text[1] == "ONLINE: 1  OFFLINE: 1  PROTECTED: 1"
    assert text[2].split() == ["CPU", "SENSORS"]
    assert text[3].split() == ["NAME", "STATUS", "TOTAL", "VALUE", "AMBIENT"]
    assert text[4].split() == ["Alpha", "box", "ONLINE", "92.2", "?"], "the alias, else the name"
    assert text[5].startswith("> beta"), "the cursor"
    cells = {c.text.strip(): c.color for c in lines[4]}
    assert cells["ONLINE"] == ColorRole.OK and cells["92.2"] == ColorRole.CRITICAL
    assert {c.text.strip(): c.color for c in lines[5]}["OFFLINE"] == ColorRole.CRITICAL
    assert {c.text.strip(): c.color for c in lines[6]}["PROTECTED"] == ColorRole.WARNING


def test_an_empty_list_and_a_message():
    from glances.outputs.browser_curses_v5 import build_lines

    lines = build_lines([], [], cursor=0, message="alpha: refused")
    assert [c.text for c in lines[0]] == ["No Glances server available"]
    assert lines[1][-1].text == "alpha: refused"


def test_the_browser_keys():
    import curses

    from glances.outputs.browser_curses_v5 import BrowserTui, order_servers

    servers = _entries()
    tui = BrowserTui(poller=None)
    assert tui.handle_key(curses.KEY_UP, servers) is None and tui.cursor == 0
    for _ in range(5):
        tui.handle_key(curses.KEY_DOWN, servers)
    assert tui.cursor == 2
    assert tui.handle_key(10, servers) == "open"
    assert tui.handle_key(ord("q"), servers) == "quit"
    assert tui.handle_key(27, servers) == "quit"
    assert tui.handle_key(10, []) is None, "nothing to open"
    tui.handle_key(ord("2"), servers)
    assert (tui.order, tui.cursor) == ("status", 0)
    assert [s.status for s in order_servers(servers, "status")] == [sl.OFFLINE, sl.PROTECTED, sl.ONLINE]
    assert [s.status for s in order_servers(servers, "status-reversed")] == [sl.ONLINE, sl.PROTECTED, sl.OFFLINE]
    assert order_servers(servers, "list") == servers


def test_run_browser_opens_servers_and_comes_back_to_the_list(monkeypatch):
    from glances import main_v5
    from glances.outputs import browser_curses_v5

    entries = _entries()
    alpha, gamma = entries[0], entries[2]
    poller = sl.ServersPoller(entries, _Config(passwords={"alpha": "pw-alpha"}), [])
    monkeypatch.setattr(sl, "build_poller", lambda config: poller)
    monkeypatch.setattr(poller, "start", lambda interval: None)
    picks = iter([alpha, gamma, gamma, None])
    messages = []

    def select(self, message=None):
        messages.append(message)
        return next(picks)

    monkeypatch.setattr(browser_curses_v5.BrowserTui, "select", select)
    typed = iter(["wrong", "right"])
    monkeypatch.setattr(main_v5.getpass, "getpass", lambda prompt: next(typed))
    opened = []

    def open_client(args, config, target, username, password):
        opened.append((target, username, password))
        return "refused the username or password" if password == "wrong" else None

    monkeypatch.setattr(main_v5, "open_client", open_client)
    args = main_v5.build_parser().parse_args(["--browser"])
    assert main_v5.run_browser(args, _Config()) == 0
    assert opened == [
        ("alpha:61208", "glances", "pw-alpha"),  # [passwords], no prompt
        ("gamma:61208", "glances", "wrong"),  # PROTECTED, nothing configured: asked
        ("gamma:61208", "glances", "right"),
    ]
    assert messages == [None, None, "gamma: refused the username or password", None]
    assert poller.password_for(gamma) == "right", "kept for the session, in the poller"
    assert poller._stop.is_set()


def test_an_arrow_key_sent_as_a_bare_escape_does_not_quit():
    """ncurses may not translate `\\x1b[B`: the browser reads it as the TUI does."""
    import curses

    from glances.outputs.browser_curses_v5 import BrowserTui

    class _Window:
        def __init__(self, keys):
            self.keys = list(keys)

        def getch(self):
            return self.keys.pop(0) if self.keys else -1

        def nodelay(self, flag):
            pass

    assert BrowserTui(poller=None)._read_key(_Window([27, ord("["), ord("B")])) == curses.KEY_DOWN
    assert BrowserTui(poller=None)._read_key(_Window([27])) == 27


def test_a_real_config_file_with_passwords_and_protocols(tmp_path, monkeypatch, caplog):
    """`GlancesConfigV5.get(..., None)` raises on a value that IS set: read raw values with `get_value`."""
    from glances.config_v5 import GlancesConfigV5

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    conf = tmp_path / "glances.conf"
    conf.write_text("[serverlist]\nserver_1_name=alpha\nserver_1_protocol=rest\n[passwords]\nalpha=pw\ndefault=dflt\n")
    config = GlancesConfigV5(str(conf))
    with caplog.at_level(logging.WARNING, logger="glances.servers_list_v5"):
        poller = sl.build_poller(config)
    assert "protocol is ignored" in caplog.text
    assert poller.password_for(poller.servers[0]) == "pw"
    assert poller.password_for(ServerEntry(name="beta", port=61208)) == "dflt"
