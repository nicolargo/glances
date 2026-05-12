#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the REST API routes (Phase 1.6).

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- /api/5/pluginslist: sorted plugin names; empty when no registration
- /api/5/all: returns store.as_dict() verbatim; excludes unregistered plugins
- /api/5/<plugin>: 200 + payload (with _levels); 200 + null on cycle 0; 404 unknown
- /api/5/<plugin>/info: 200 + fields_description; 404 unknown
- /api/5/alert: 200 + history; 404 when alerts is None
- /api/5/config: 200 + redacted via as_dict_secure()
- /api/5/token: Basic round-trip → JWT usable on other routes; wrong creds → 401;
  missing creds → 401; auth not configured → 404; token is exempt from global auth
- Auth integration: token endpoint reachable when password is set; protected
  routes require Bearer or Basic; minted token unlocks /api/5/all
- register_plugin: rejects duplicate registrations
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.security_v5 import hash_password
from glances.stats_store_v5 import StatsStoreV5
from glances.webserver_v5 import build_app, register_plugin

# ------------------------------------------------------- fake plugins


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name: ClassVar[str] = "fakescalar"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "percent": {"description": "Usage percentage.", "unit": "percent"},
        "total": {"description": "Total.", "unit": "bytes"},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 42.0, "total": 1024}


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "fakecollection"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {"description": "Item name.", "unit": "string", "primary_key": True},
        "rx": {"description": "Received bytes.", "unit": "bytes"},
    }

    async def _grab_stats(self) -> list:
        return [{"name": "eth0", "rx": 100}, {"name": "lo", "rx": 0}]


# ------------------------------------------------------- fixtures


@pytest.fixture
def config_factory(tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("GLANCES_CONFIG_FILE", raising=False)
    for env_key in list(__import__("os").environ):
        if env_key.startswith("GLANCES_"):
            monkeypatch.delenv(env_key, raising=False)

    def make(**outputs) -> GlancesConfigV5:
        for key, value in outputs.items():
            monkeypatch.setenv(f"GLANCES_OUTPUTS__{key.upper()}", str(value))
        return GlancesConfigV5()

    return make


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


def _make_app_with_plugins(config, store, *, alerts=None, plugins=()):
    app = build_app(config=config, store=store, alerts=alerts)
    for plugin in plugins:
        register_plugin(app, plugin)
    return app


def _populate(store, plugin) -> None:
    """Drive ``plugin.update()`` once so the store has fresh data."""
    asyncio.run(plugin.update())


def _basic_header(user: str, password: str) -> dict[str, str]:
    encoded = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {encoded}"}


# ------------------------------------------------------- pluginslist


def test_pluginslist_empty(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/pluginslist")
    assert r.status_code == 200
    assert r.json() == []


def test_pluginslist_sorted(config_factory, store):
    config = config_factory()
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[collection, scalar])
    with TestClient(app) as client:
        r = client.get("/api/5/pluginslist")
    assert r.status_code == 200
    assert r.json() == ["fakecollection", "fakescalar"]


# ------------------------------------------------------- /all


def test_all_returns_store_dict(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/all")
    body = r.json()
    assert r.status_code == 200
    assert "fakescalar" in body
    assert body["fakescalar"]["percent"] == 42.0


def test_all_excludes_unwritten_plugins(config_factory, store):
    config = config_factory()
    written = FakeScalarPlugin(store, config)
    unwritten = FakeCollectionPlugin(store, config)
    _populate(store, written)
    app = _make_app_with_plugins(config, store, plugins=[written, unwritten])
    with TestClient(app) as client:
        body = client.get("/api/5/all").json()
    assert "fakescalar" in body
    assert "fakecollection" not in body  # never updated → not in store


# ------------------------------------------------------- /<plugin>


def test_plugin_payload_scalar(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakescalar")
    assert r.status_code == 200
    payload = r.json()
    assert payload["percent"] == 42.0
    assert payload["total"] == 1024
    assert "_levels" in payload  # baseline contract: levels included
    assert "time_since_update" in payload


def test_plugin_payload_collection(config_factory, store):
    config = config_factory()
    plugin = FakeCollectionPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakecollection")
    assert r.status_code == 200
    payload = r.json()
    assert isinstance(payload["data"], list)
    assert payload["data"][0]["name"] == "eth0"
    assert "_levels" in payload


def test_plugin_payload_cycle_zero_returns_null(config_factory, store):
    """Registered but never-updated plugin → 200 null (transient, not error)."""
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakescalar")
    assert r.status_code == 200
    assert r.json() is None


def test_plugin_payload_unknown_404(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/doesnotexist")
    assert r.status_code == 404
    assert "doesnotexist" in r.json()["detail"]


# ------------------------------------------------------- /<plugin>/info


def test_plugin_info_returns_schema(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakescalar/info")
    assert r.status_code == 200
    body = r.json()
    assert "percent" in body
    assert body["percent"]["unit"] == "percent"


def test_plugin_info_unknown_404(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/missing/info")
    assert r.status_code == 404


# ------------------------------------------------------- /alert


def test_alert_404_when_disabled(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store, alerts=None)
    with TestClient(app) as client:
        r = client.get("/api/5/alert")
    assert r.status_code == 404


def test_alert_returns_history(config_factory, store):
    config = config_factory()
    alerts = GlancesAlerts(config)
    # Inject a fake event directly into the ring buffer.
    fake_event = {
        "ts": "2026-05-12T10:00:00+00:00",
        "plugin": "mem",
        "key": None,
        "field": "percent",
        "level": "warning",
        "previous_level": "ok",
        "value": 75.0,
        "prominent": True,
        "hostname": "test-host",
    }
    alerts._history.append(fake_event)
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert")
    assert r.status_code == 200
    body = r.json()
    assert body == [fake_event]


def test_alert_empty_history(config_factory, store):
    config = config_factory()
    alerts = GlancesAlerts(config)
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert")
    assert r.status_code == 200
    assert r.json() == []


# ------------------------------------------------------- /config


def test_config_returns_redacted_dict(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = _make_app_with_plugins(config, store)
    # /api/5/config is *behind* the auth middleware since password is set —
    # authenticate to fetch it.
    with TestClient(app) as client:
        r = client.get("/api/5/config", headers=_basic_header("glances", "hunter2"))
    assert r.status_code == 200
    body = r.json()
    # Secret-bearing keys are present but redacted.
    assert body["outputs"]["password"] == "***"


def test_config_open_when_no_auth(config_factory, store):
    config = config_factory()
    app = _make_app_with_plugins(config, store)
    with TestClient(app) as client:
        r = client.get("/api/5/config")
    assert r.status_code == 200
    # Still no secret on this conf, just sanity-check we got something.
    assert isinstance(r.json(), dict)


# ------------------------------------------------------- /token


def test_token_404_when_auth_not_configured(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.post("/api/5/token")
    assert r.status_code == 404
    assert "JWT auth not configured" in r.json()["detail"]


def test_token_401_without_credentials(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = _make_app_with_plugins(config, store)
    with TestClient(app) as client:
        r = client.post("/api/5/token")
    assert r.status_code == 401
    assert "Basic" in r.headers.get("WWW-Authenticate", "")


def test_token_401_with_wrong_password(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = _make_app_with_plugins(config, store)
    with TestClient(app) as client:
        r = client.post("/api/5/token", headers=_basic_header("glances", "wrong"))
    assert r.status_code == 401


def test_token_round_trip(config_factory, store):
    config = config_factory(password=hash_password("hunter2"), jwt_secret_key="stable")
    app = _make_app_with_plugins(config, store)
    with TestClient(app) as client:
        r = client.post("/api/5/token", headers=_basic_header("glances", "hunter2"))
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["expires_in"], int) and body["expires_in"] > 0
    # The minted token must be accepted on a protected route.
    with TestClient(app) as client:
        r2 = client.get("/api/5/all", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r2.status_code == 200


def test_token_endpoint_exempt_from_global_auth(config_factory, store):
    """``/api/5/token`` must NOT 401 because of the global auth middleware.

    Without an exemption, the middleware would short-circuit the request
    before the route's own ``Depends(HTTPBasic)`` can read credentials.
    """
    config = config_factory(password=hash_password("hunter2"))
    app = _make_app_with_plugins(config, store)
    with TestClient(app) as client:
        # No credentials at all → the *route* (not the middleware) emits 401.
        r = client.post("/api/5/token")
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate", "").startswith("Basic")


# ------------------------------------------------------- auth integration


def test_protected_route_requires_auth(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        assert client.get("/api/5/all").status_code == 401
        assert client.get("/api/5/all", headers=_basic_header("glances", "hunter2")).status_code == 200


# ------------------------------------------------------- register_plugin


def test_register_plugin_rejects_duplicate(config_factory, store):
    config = config_factory()
    app = build_app(config=config, store=store)
    plugin = FakeScalarPlugin(store, config)
    register_plugin(app, plugin)
    with pytest.raises(ValueError, match="already registered"):
        register_plugin(app, plugin)
