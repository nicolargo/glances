#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Zeroconf announcement and discovery (P3-5)."""

from __future__ import annotations

import logging

import pytest

from glances import servers_list_v5 as sl
from glances import zeroconf_v5 as zc
from glances.servers_list_v5 import ServerEntry
from tests.test_servers_list_v5 import _V5, _Config, _Server, network  # noqa: F401 -- fixture

_V5_TXT = {b"api": b"5", b"protocol": b"rest"}


def test_discovery_lists_the_v5_announcements_only():
    servers: list[ServerEntry] = []
    discovery = zc.Discovery(servers)
    discovery.add("alpha:61208._glances._tcp.local.", "192.168.1.10", 61208, _V5_TXT)
    discovery.add("oldbox:61209._glances._tcp.local.", "192.168.1.11", 61209, {b"protocol": b"rpc"})
    discovery.add("weird:61208._glances._tcp.local.", "192.168.1.12", 61208, {b"api": b"4"})
    discovery.add("noaddr:61208._glances._tcp.local.", None, 61208, _V5_TXT)
    assert [(s.name, s.port, s.alias, s.source) for s in servers] == [("192.168.1.10", 61208, "alpha", "zeroconf")]


def test_an_announcement_that_moves_or_leaves_updates_the_list():
    servers = [ServerEntry(name="static", port=61208)]
    discovery = zc.Discovery(servers)
    name = "alpha:61208._glances._tcp.local."
    discovery.add(name, "192.168.1.10", 61208, _V5_TXT)
    discovery.add(name, "192.168.1.10", 61208, _V5_TXT)  # the same again: no duplicate
    assert len(servers) == 2
    discovery.add(name, "192.168.1.20", 61208, _V5_TXT)
    assert [s.name for s in servers] == ["static", "192.168.1.20"]
    discovery.remove(name)
    discovery.remove("never-seen._glances._tcp.local.")
    assert [s.name for s in servers] == ["static"]


def test_an_announced_name_is_shown_printable_and_short():
    servers: list[ServerEntry] = []
    zc.Discovery(servers).add("ev\x1b[31mil" + "x" * 200 + ":61208._glances._tcp.local.", "10.0.0.1", 61208, _V5_TXT)
    alias = servers[0].alias
    assert "\x1b" not in alias and len(alias) == 64


# ------------------------------------------------ CVE-2026-32634


def test_a_discovered_server_is_sent_no_configured_credential(network):  # noqa: F811
    """Anyone can announce under a trusted name: the name proves nothing.

    The discovered entry claims `alpha`, which has a password in [passwords]
    (and there is a `default`). None of them is sent: no token request, no
    Authorization header. It shows PROTECTED, and the user types one.
    """
    network.servers["http://192.168.1.66:61208"] = _Server(dict(_V5), password="s3cret")
    servers: list[ServerEntry] = []
    zc.Discovery(servers).add("alpha:61208._glances._tcp.local.", "192.168.1.66", 61208, _V5_TXT)
    poller = sl.ServersPoller(
        servers, _Config(passwords={"alpha": "s3cret", "default": "s3cret"}), [sl.Column("cpu", "total")]
    )
    assert poller.password_for(servers[0]) is None
    poller.poll_round()
    assert servers[0].status == sl.PROTECTED
    assert not [url for url, _ in network.sent if url.endswith("/api/5/token")], "no credential offered"
    assert all(not (sent or {}).get("Authorization") for url, sent in network.sent if isinstance(sent, dict))


def test_a_discovered_server_never_shares_a_static_servers_connection(network):  # noqa: F811
    """Same address as a static entry, announced: its own connection, without the static one's password."""
    network.servers["http://192.168.1.10:61208"] = _Server(dict(_V5), password="s3cret")
    static = ServerEntry(name="192.168.1.10", port=61208)
    servers = [static]
    zc.Discovery(servers).add("fake:61208._glances._tcp.local.", "192.168.1.10", 61208, _V5_TXT)
    poller = sl.ServersPoller(servers, _Config(passwords={"192.168.1.10": "s3cret"}), [sl.Column("cpu", "total")])
    poller.poll_round()
    assert [s.status for s in servers] == [sl.ONLINE, sl.PROTECTED]
    assert servers[0].key != servers[1].key


# ------------------------------------------------------ announcement


def test_what_address_a_server_announces(monkeypatch):
    import glances.globals

    assert zc._announced_address("127.0.0.1") is None, "loopback: the LAN cannot reach it"
    assert zc._announced_address("192.168.1.5") == "192.168.1.5"
    monkeypatch.setattr(glances.globals, "get_ip_address", lambda: ("192.168.1.7", "255.255.255.0"))
    assert zc._announced_address("0.0.0.0") == "192.168.1.7"
    assert zc._announced_address("no-such-host.invalid") is None


def test_a_loopback_server_announces_nothing(monkeypatch):
    monkeypatch.setattr(zc, "Zeroconf", lambda **kw: pytest.fail("no Zeroconf for a loopback server"))
    assert zc.Announcer().start("127.0.0.1", 61208) is False


def test_without_the_zeroconf_library_both_sides_say_so_and_go_on(monkeypatch, caplog):
    monkeypatch.setattr(zc, "Zeroconf", None)
    with caplog.at_level(logging.INFO, logger="glances.zeroconf_v5"):
        assert zc.Discovery([]).start() is False
        assert zc.Announcer().start("192.168.1.5", 61208) is False
    assert "pip install glances[browser]" in caplog.text


def test_disable_autodiscover_starts_no_discovery():
    from glances.main_v5 import build_parser, start_discovery

    args = build_parser().parse_args(["--browser", "--disable-autodiscover"])
    assert start_discovery(sl.ServersPoller([], _Config(), []), args) is None
