#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 ip plugin model (Task 1 — scalar foundation)."""

from __future__ import annotations

import socket

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.main_v5 import build_parser
from glances.plugins.ip.model_v5 import PluginModel, _ip_to_cidr, _public_api_allowed
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    # Also isolate the user config search path (XDG_CONFIG_HOME) — otherwise
    # a real ~/.config/glances/glances.conf on the dev machine leaks in,
    # which now matters since Task 3's _grab_stats can trigger a real public
    # IP fetch when [ip] public_api is set there.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    # Mirror tests/test_plugin_sensors_v5.py::_cfg_with — load an [ip] body
    # via an XDG-discovered glances.conf.
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "ip"
    assert p.IS_COLLECTION is False
    assert p._primary_key is None
    assert p.EMITS_ALERTS is False


def test_fields_description():
    fd = PluginModel.fields_description
    assert set(fd) >= {"address", "mask", "mask_cidr", "gateway", "public_address", "public_info_human"}
    assert fd["mask_cidr"]["unit"] == "number"
    for schema in fd.values():
        assert schema.get("watched", False) is False


def test_ip_to_cidr():
    assert _ip_to_cidr("255.255.255.0") == 24
    assert _ip_to_cidr(None) == 0


@pytest.mark.asyncio
async def test_grab_private_merges_address(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr(
        "glances.plugins.ip.model_v5.get_ip_address",
        lambda: ("192.168.1.10", "255.255.255.0"),
    )
    result = await p._grab_stats()
    assert result == {"address": "192.168.1.10", "mask": "255.255.255.0", "mask_cidr": 24}
    assert "gateway" not in result


@pytest.mark.asyncio
async def test_grab_private_no_interface(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr(
        "glances.plugins.ip.model_v5.get_ip_address",
        lambda: (None, None),
    )
    result = await p._grab_stats()
    assert result == {"address": None, "mask": None, "mask_cidr": 0}


# ------------------------------------------------------------------ SSRF gate
# CVE-2026-35587: _public_api_allowed locks the security contract described
# in glances/plugins/ip/model_v5.py (scheme allowlist + DNS-resolved
# internal-IP rejection, fail-closed on resolution errors).


def _getaddrinfo(*ips):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 80)) for ip in ips]


def test_ssrf_scheme_rejected():
    assert _public_api_allowed("file:///etc/passwd", False) is False


def test_ssrf_loopback_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("127.0.0.1"))
    assert _public_api_allowed("http://127.0.0.1/json", False) is False


def test_ssrf_metadata_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("169.254.169.254"))
    assert _public_api_allowed("http://169.254.169.254/latest/meta-data/", False) is False


def test_ssrf_private_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("10.0.0.5"))
    assert _public_api_allowed("http://10.0.0.5/json", False) is False


def test_ssrf_reserved_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("240.0.0.1"))
    assert _public_api_allowed("http://240.0.0.1/json", False) is False


def test_ssrf_public_allowed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("93.184.216.34"))
    assert _public_api_allowed("http://example.com/json", False) is True


def test_ssrf_dns_alias_to_internal_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("169.254.169.254"))
    assert _public_api_allowed("http://evil.example.com/json", False) is False


def test_ssrf_mixed_resolution_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("93.184.216.34", "10.0.0.5"))
    assert _public_api_allowed("http://example.com/json", False) is False


def test_ssrf_allow_internal_opt_in(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("127.0.0.1"))
    assert _public_api_allowed("http://127.0.0.1/json", True) is True


def test_ssrf_unresolvable_fails_closed(monkeypatch):
    def _raise(*a, **k):
        raise socket.gaierror("name not known")

    monkeypatch.setattr(socket, "getaddrinfo", _raise)
    assert _public_api_allowed("http://unresolvable.example.com/json", False) is False


# ------------------------------------------------------------- public IP fetch
# Task 3: cadenced public-IP fetch (guarded, credential non-forwarding).


@pytest.mark.asyncio
async def test_public_disabled_skips_fetch(tmp_path, monkeypatch):
    # _cfg_with (not the bare `config` fixture) isolates XDG_CONFIG_HOME so
    # this doesn't pick up a real ~/.config/glances/glances.conf.
    config = _cfg_with(tmp_path, monkeypatch, "")
    store = StatsStoreV5()
    p = PluginModel(store, config)
    assert p.public_disabled is True
    monkeypatch.setattr(
        "glances.plugins.ip.model_v5.get_ip_address",
        lambda: ("192.168.1.10", "255.255.255.0"),
    )
    called = False

    def _spy():
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(p, "_fetch_public_ip_info", _spy)
    result = await p._grab_stats()
    assert "public_address" not in result
    assert called is False


@pytest.mark.asyncio
async def test_public_fetch_merges(tmp_path, monkeypatch):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[ip]\npublic_disabled=False\npublic_api=http://example.com/json\npublic_field=ip\npublic_template={country}\n",
    )
    store = StatsStoreV5()
    p = PluginModel(store, config)
    monkeypatch.setattr(
        "glances.plugins.ip.model_v5.get_ip_address",
        lambda: ("192.168.1.10", "255.255.255.0"),
    )
    monkeypatch.setattr(p, "_fetch_public_ip_info", lambda: {"ip": "1.2.3.4", "country": "Wonderland"})
    result = await p._grab_stats()
    assert result["public_address"] == "1.2.3.4"
    assert result["public_info_human"] == "Wonderland"


@pytest.mark.asyncio
async def test_public_fetch_cadence_reuses_cache(tmp_path, monkeypatch):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[ip]\npublic_disabled=False\npublic_api=http://example.com/json\npublic_field=ip\npublic_template={country}\n",
    )
    store = StatsStoreV5()
    p = PluginModel(store, config)
    monkeypatch.setattr(
        "glances.plugins.ip.model_v5.get_ip_address",
        lambda: ("192.168.1.10", "255.255.255.0"),
    )
    calls = {"n": 0}

    def _fetch():
        calls["n"] += 1
        return {"ip": "1.2.3.4"}

    monkeypatch.setattr(p, "_fetch_public_ip_info", _fetch)

    p._monotonic = lambda: 1000.0
    result = await p._grab_stats()
    assert calls["n"] == 1
    assert result["public_address"] == "1.2.3.4"

    p._monotonic = lambda: 1000.0 + 10
    result = await p._grab_stats()
    assert calls["n"] == 1
    assert result["public_address"] == "1.2.3.4"

    p._monotonic = lambda: 1000.0 + 301
    result = await p._grab_stats()
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_public_info_human_bad_template(tmp_path, monkeypatch):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[ip]\npublic_disabled=False\npublic_api=http://example.com/json\npublic_field=ip\npublic_template={missing}\n",
    )
    store = StatsStoreV5()
    p = PluginModel(store, config)
    monkeypatch.setattr(
        "glances.plugins.ip.model_v5.get_ip_address",
        lambda: ("192.168.1.10", "255.255.255.0"),
    )
    monkeypatch.setattr(p, "_fetch_public_ip_info", lambda: {"ip": "1.2.3.4"})
    result = await p._grab_stats()
    assert result["public_info_human"] == ""
    assert result["public_address"] == "1.2.3.4"


def test_credentials_never_sent_to_blocked_host(tmp_path, monkeypatch):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[ip]\npublic_disabled=False\npublic_api=http://169.254.169.254/json\npublic_field=ip\n"
        "public_username=alice\npublic_password=secret\n",
    )
    store = StatsStoreV5()
    p = PluginModel(store, config)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("169.254.169.254"))

    urlopen_called = False
    urlopen_auth_called = False

    def _urlopen_spy(*a, **k):
        nonlocal urlopen_called
        urlopen_called = True
        raise AssertionError("urlopen must not be called for a blocked host")

    def _urlopen_auth_spy(*a, **k):
        nonlocal urlopen_auth_called
        urlopen_auth_called = True
        raise AssertionError("urlopen_auth must not be called for a blocked host")

    monkeypatch.setattr("glances.plugins.ip.model_v5.urlopen", _urlopen_spy)
    monkeypatch.setattr("glances.plugins.ip.model_v5.urlopen_auth", _urlopen_auth_spy)

    result = p._fetch_public_ip_info()
    assert result == {}
    assert urlopen_called is False
    assert urlopen_auth_called is False


def test_fetch_uses_basic_auth_when_credentials_set(tmp_path, monkeypatch):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[ip]\npublic_disabled=False\npublic_api=http://example.com/json\npublic_field=ip\n"
        "public_username=alice\npublic_password=secret\n",
    )
    store = StatsStoreV5()
    p = PluginModel(store, config)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("93.184.216.34"))

    class _Response:
        def read(self):
            return b'{"ip":"1.2.3.4"}'

    calls = {"auth": 0, "plain": 0}

    def _urlopen_auth_spy(*a, **k):
        calls["auth"] += 1
        return _Response()

    def _urlopen_spy(*a, **k):
        calls["plain"] += 1
        raise AssertionError("urlopen must not be called when credentials are set")

    monkeypatch.setattr("glances.plugins.ip.model_v5.urlopen_auth", _urlopen_auth_spy)
    monkeypatch.setattr("glances.plugins.ip.model_v5.urlopen", _urlopen_spy)

    result = p._fetch_public_ip_info()
    assert result == {"ip": "1.2.3.4"}
    assert calls["auth"] == 1
    assert calls["plain"] == 0


def test_hide_public_info_flag_parses():
    parser = build_parser()
    assert parser.parse_args([]).hide_public_info is False
    assert parser.parse_args(["--hide-public-info"]).hide_public_info is True


def test_fetch_network_error_keeps_last_good(tmp_path, monkeypatch):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[ip]\npublic_disabled=False\npublic_api=http://example.com/json\npublic_field=ip\n",
    )
    store = StatsStoreV5()
    p = PluginModel(store, config)
    p._public_cache = {"ip": "9.9.9.9"}
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _getaddrinfo("93.184.216.34"))

    def _raise(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr("glances.plugins.ip.model_v5.urlopen", _raise)

    result = p._fetch_public_ip_info()
    assert result == {"ip": "9.9.9.9"}
