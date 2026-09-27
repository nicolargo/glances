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
