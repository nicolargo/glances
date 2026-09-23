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
- /api/5/all/info: every registered schema, published or not; {} when empty
- /api/5/alert: 200 + history; 404 when alerts is None
- /api/5/alert/incidents: 200 + derive_incidents() synthesis; partial flag
  preserved; every incident carries a `duration` (`>`-prefixed when partial);
  404 when alerts is None
- /api/5/config: 200 + redacted via as_dict_secure()
- /api/5/token: Basic round-trip → JWT usable on other routes; wrong creds → 401;
  missing creds → 401; auth not configured → 404; token is exempt from global auth
- Auth integration: token endpoint reachable when password is set; protected
  routes require Bearer or Basic; minted token unlocks /api/5/all
- register_plugin: rejects duplicate registrations
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from glances.alerts_v5 import GlancesAlerts, _AlertState
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
        "secret": {"description": "Not for export.", "unit": "string", "exportable": False},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 42.0, "total": 1024, "secret": "hunter2"}


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "fakecollection"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {"description": "Item name.", "unit": "string", "primary_key": True},
        "rx": {"description": "Received bytes.", "unit": "bytes"},
        "secret": {"description": "Not for export.", "unit": "string", "exportable": False},
    }

    async def _grab_stats(self) -> list:
        return [
            {"name": "eth0", "rx": 100, "secret": "hunter2"},
            {"name": "lo", "rx": 0, "secret": "hunter2"},
        ]


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


def test_all_info_returns_every_registered_schema(config_factory, store):
    """One request for every schema: the WebUI resolves its labels once at
    page load instead of one /info call per plugin (G9-5 spec §6.2).

    Neither plugin is populated. Unlike /api/5/all, which skips a plugin that
    has not published, a schema is static and must be served regardless --
    otherwise a plugin still at cycle 0 when the tab opens would keep
    field-name labels for the tab's whole life.

    Also the route-ordering guard: before the handler exists, `all` is read as
    a plugin name by /{plugin_name}/info and the request 404s.
    """
    config = config_factory()
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[scalar, collection])
    with TestClient(app) as client:
        r = client.get("/api/5/all/info")
    assert r.status_code == 200
    assert r.json() == {
        "fakescalar": FakeScalarPlugin.fields_description,
        "fakecollection": FakeCollectionPlugin.fields_description,
    }


def test_all_info_empty_registry(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/all/info")
    assert r.status_code == 200
    assert r.json() == {}


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


def test_alert_route_exposes_top_processes(config_factory, store):
    """`/api/5/alert` returns `get_history()` verbatim, so the top-process
    keys added by the alert engine reach the API with no route change."""
    config = config_factory()
    alerts = GlancesAlerts(config)
    # Inject a fake event directly into the ring buffer, same as
    # test_alert_returns_history, but carrying the top-process keys an
    # opening event on the field allowlist would hold.
    fake_event = {
        "ts": "2026-05-12T10:00:00+00:00",
        "plugin": "cpu",
        "key": None,
        "field": "total",
        "level": "warning",
        "previous_level": "ok",
        "value": 92.0,
        "prominent": True,
        "hostname": "test-host",
        "top": ["python3", "chrome", "node"],
        "top_sort": "cpu_percent",
    }
    alerts._history.append(fake_event)
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert")
    assert r.status_code == 200
    payload = r.json()
    assert payload[0]["top"] == ["python3", "chrome", "node"]
    assert payload[0]["top_sort"] == "cpu_percent"


def test_alert_empty_history(config_factory, store):
    config = config_factory()
    alerts = GlancesAlerts(config)
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert")
    assert r.status_code == 200
    assert r.json() == []


# ------------------------------------------------------- /alert/incidents


def test_alert_incidents_serves_the_synthesis(config_factory, store):
    """Same function the TUI calls (glances/alerts_incidents_v5.py), so the
    browser cannot drift from the terminal."""
    config = config_factory()
    alerts = GlancesAlerts(config)
    # A resolved incident: opening and closing transitions both in history.
    alerts._history.append(
        {
            "ts": "2026-05-12T09:00:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "warning",
            "previous_level": "ok",
            "value": 90.0,
            "prominent": True,
            "hostname": "test-host",
        }
    )
    alerts._history.append(
        {
            "ts": "2026-05-12T09:05:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "ok",
            "previous_level": "warning",
            "value": 10.0,
            "prominent": False,
            "hostname": "test-host",
        }
    )
    # An ongoing incident: opening transition in history, engine still active.
    alerts._history.append(
        {
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
    )
    alerts._state[("mem", None, "percent")] = _AlertState(
        committed_level="warning", committed_since="2026-05-12T10:00:00+00:00", has_committed=True
    )
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert/incidents")
    assert r.status_code == 200
    incidents = r.json()["incidents"]
    # Ongoing first (newest first within each group) — derive_incidents' own
    # sort contract (design §5.3), unchanged by the route.
    assert [i["ongoing"] for i in incidents] == [True, False]
    assert incidents[0]["plugin"] == "mem"
    assert incidents[1]["plugin"] == "cpu"


def test_alert_incidents_exposes_is_initializing(config_factory, store):
    """Fix round 2, IMPORTANT 2: the route answers an envelope, not a bare
    array, so the browser can tell "warm-up" from "no alert detected" —
    the same distinction `render_alert_block` already makes
    (curses_renderer_v5.py:738-745). A fresh `GlancesAlerts` that never
    ingested anything is still initializing."""
    config = config_factory()
    alerts = GlancesAlerts(config)
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert/incidents")
    assert r.status_code == 200
    body = r.json()
    assert body["is_initializing"] is True
    assert body["incidents"] == []


def test_alert_incidents_marks_a_partial_incident(config_factory, store):
    """`partial` says the opening event aged out of the bounded history, so
    the duration is a LOWER BOUND. A client that lost the flag would print
    a lower bound as if it were exact.

    The engine reports the tuple active (`get_ongoing()`), but neither its
    opening transition (evicted from the ring buffer) nor its start time
    (`get_ongoing_since()` — nothing was ever committed here) survive
    anywhere: exactly what a long-running alert does to a bounded history.
    """
    config = config_factory()
    alerts = GlancesAlerts(config)
    alerts._state[("cpu", None, "total")] = _AlertState(committed_level="critical", has_committed=True)
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert/incidents")
    assert r.status_code == 200
    incidents = r.json()["incidents"]
    assert len(incidents) == 1
    assert incidents[0]["ongoing"] is True
    assert incidents[0]["partial"] is True


def test_alert_incidents_404_when_disabled(config_factory, store):
    """Same contract as /api/5/alert."""
    app = _make_app_with_plugins(config_factory(), store, alerts=None)
    with TestClient(app) as client:
        r = client.get("/api/5/alert/incidents")
    assert r.status_code == 404


def test_alert_incidents_every_incident_has_a_duration_key(config_factory, store):
    """`duration` is always present in the response, `null` or not, so a
    consumer can rely on the key existing rather than guarding for it."""
    config = config_factory()
    alerts = GlancesAlerts(config)
    alerts._history.append(
        {
            "ts": "2026-05-12T09:00:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "warning",
            "previous_level": "ok",
            "value": 90.0,
            "prominent": True,
            "hostname": "test-host",
        }
    )
    alerts._history.append(
        {
            "ts": "2026-05-12T09:05:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "ok",
            "previous_level": "warning",
            "value": 10.0,
            "prominent": False,
            "hostname": "test-host",
        }
    )
    alerts._history.append(
        {
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
    )
    alerts._state[("mem", None, "percent")] = _AlertState(
        committed_level="warning", committed_since="2026-05-12T10:00:00+00:00", has_committed=True
    )
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert/incidents")
    assert r.status_code == 200
    incidents = r.json()["incidents"]
    assert len(incidents) == 2
    assert all("duration" in incident for incident in incidents)


def test_alert_incidents_partial_duration_has_lower_bound_prefix(config_factory, store):
    """The whole reason `duration` is computed server-side: a `partial`
    incident's opening event aged out of the bounded history, so its
    duration is a LOWER BOUND and must be `>`-prefixed. A client that
    recomputed this in JS and dropped the prefix would print a lower bound
    as if it were exact.

    Seeded like the existing partial test — a tuple present in
    `get_ongoing()` but absent from `get_ongoing_since()` (`committed_since`
    left `None`) — except here the surviving history event is an
    ESCALATION (`previous_level` != "ok"), which gives the incident a real
    `begin` so `incident_duration()` has something to format instead of
    returning `None` outright (the fully-evicted-with-no-history case used
    by the earlier partial test has `begin=None`, which formats to no
    duration at all, not a `>`-prefixed one).
    """
    config = config_factory()
    alerts = GlancesAlerts(config)
    alerts._history.append(
        {
            "ts": "2026-05-12T08:00:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "critical",
            "previous_level": "warning",
            "value": 97.0,
            "prominent": True,
            "hostname": "test-host",
        }
    )
    alerts._state[("cpu", None, "total")] = _AlertState(committed_level="critical", has_committed=True)
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert/incidents")
    assert r.status_code == 200
    incidents = r.json()["incidents"]
    assert len(incidents) == 1
    assert incidents[0]["partial"] is True
    assert incidents[0]["duration"] is not None
    assert incidents[0]["duration"].startswith(">")


def test_alert_incidents_resolved_duration_has_no_prefix(config_factory, store):
    """Control for the test above: a resolved (non-partial) incident's
    duration must NOT carry the `>` prefix, so the prefix assertion above
    cannot pass by accident (e.g. a route that always prepends `>`)."""
    config = config_factory()
    alerts = GlancesAlerts(config)
    alerts._history.append(
        {
            "ts": "2026-05-12T09:00:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "warning",
            "previous_level": "ok",
            "value": 90.0,
            "prominent": True,
            "hostname": "test-host",
        }
    )
    alerts._history.append(
        {
            "ts": "2026-05-12T09:05:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "ok",
            "previous_level": "warning",
            "value": 10.0,
            "prominent": False,
            "hostname": "test-host",
        }
    )
    app = _make_app_with_plugins(config, store, alerts=alerts)
    with TestClient(app) as client:
        r = client.get("/api/5/alert/incidents")
    assert r.status_code == 200
    incidents = r.json()["incidents"]
    assert len(incidents) == 1
    assert incidents[0]["ongoing"] is False
    assert incidents[0]["duration"] is not None
    assert not incidents[0]["duration"].startswith(">")
    assert incidents[0]["duration"] == "5m00s"


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


# ------------------------------------------------------- /limits


class FakeLimitsPlugin(GlancesPluginBase[dict]):
    """Scalar plugin carrying thresholds, for the /limits routes."""

    plugin_name: ClassVar[str] = "fakelimits"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "percent": {
            "description": "Usage percentage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 42.0}


def test_plugin_limits_returns_thresholds(config_factory, store):
    config = config_factory()
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakelimits/limits")
    assert r.status_code == 200
    assert r.json() == {"percent": {"careful": 50.0, "warning": 70.0, "critical": 90.0}}


def test_plugin_limits_answers_before_the_first_cycle(config_factory, store):
    """No _populate() call: thresholds come from config + schema, so unlike
    /api/5/<plugin> this route never returns null at cycle 0."""
    config = config_factory()
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakelimits/limits")
    assert r.status_code == 200
    assert r.json()["percent"]["warning"] == 70.0


def test_plugin_limits_empty_dict_when_no_watched_field(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakescalar/limits")
    assert r.status_code == 200
    assert r.json() == {}


def test_plugin_limits_404_on_unknown_plugin(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/nosuchplugin/limits")
    assert r.status_code == 404


def test_plugin_limits_404_on_reserved_name(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/config/limits")
    assert r.status_code == 404


def test_all_limits_is_not_captured_by_the_dynamic_route(config_factory, store):
    """Route-ordering guard: /all/limits must be declared before
    /{plugin_name}/limits, otherwise `all` is read as a plugin name."""
    config = config_factory()
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/all/limits")
    assert r.status_code == 200
    body = r.json()
    assert "fakelimits" in body
    assert body["fakelimits"]["percent"]["critical"] == 90.0


def test_all_limits_omits_plugins_without_thresholds(config_factory, store):
    config = config_factory()
    with_limits = FakeLimitsPlugin(store, config)
    without_limits = FakeScalarPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[with_limits, without_limits])
    with TestClient(app) as client:
        r = client.get("/api/5/all/limits")
    body = r.json()
    assert "fakelimits" in body
    assert "fakescalar" not in body


def test_limits_routes_require_auth_when_password_is_set(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        assert client.get("/api/5/all/limits").status_code == 401
        assert client.get("/api/5/fakelimits/limits").status_code == 401
        ok = client.get("/api/5/fakelimits/limits", headers=_basic_header("glances", "hunter2"))
    assert ok.status_code == 200


# ------------------------------------------------- export filter (issue #3211)
#
# The routes used to hand back the RAW store payload, so a field declared
# `exportable: False` reached every unauthenticated HTTP client while the
# exporters correctly dropped it. Both handlers now go through
# `plugin.get_api_payload()`.


def test_plugin_payload_drops_non_exportable_fields(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])

    assert "secret" in store.get("fakescalar"), "guard: the fixture must publish it"

    with TestClient(app) as client:
        payload = client.get("/api/5/fakescalar").json()

    assert "secret" not in payload
    assert payload["percent"] == 42.0


def test_plugin_payload_projects_each_collection_item(config_factory, store):
    config = config_factory()
    plugin = FakeCollectionPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])

    with TestClient(app) as client:
        payload = client.get("/api/5/fakecollection").json()

    assert payload["data"], "fixture must produce at least one item"
    for item in payload["data"]:
        assert "secret" not in item
        assert "rx" in item


def test_all_drops_non_exportable_fields(config_factory, store):
    config = config_factory()
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    _populate(store, scalar)
    _populate(store, collection)
    app = _make_app_with_plugins(config, store, plugins=[scalar, collection])

    with TestClient(app) as client:
        body = client.get("/api/5/all").json()

    assert "secret" not in body["fakescalar"]
    assert all("secret" not in i for i in body["fakecollection"]["data"])
    # `_levels` is what a UI colours cells from -- the API keeps it.
    assert "_levels" in body["fakescalar"]


def test_api_keeps_time_since_update(config_factory, store):
    """Regression guard. `time_since_update` is declared `exportable: False`
    (it is not a metric), so filtering the API on `exportable` alone would
    strip it from every endpoint. The WebUI divides counters by it to get
    rates -- see `plugin-cpu.vue` (ctx_switches) and `plugin-processlist.vue`
    (per-process IO). Dropping it renders those values as NaN.
    """
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])

    with TestClient(app) as client:
        payload = client.get("/api/5/fakescalar").json()
        body = client.get("/api/5/all").json()

    assert "time_since_update" in payload
    assert "time_since_update" in body["fakescalar"]
    # ... but it must still never reach an exporter.
    assert "time_since_update" not in plugin.get_export()


def test_all_still_excludes_a_collection_plugin_that_never_published(config_factory, store):
    """A collection plugin's envelope is built by get_api_payload(); without an
    emptiness guard it would answer `{"data": []}` before its first cycle and
    appear in /all a cycle too early."""
    config = config_factory()
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    _populate(store, scalar)  # collection deliberately NOT updated
    app = _make_app_with_plugins(config, store, plugins=[scalar, collection])

    with TestClient(app) as client:
        body = client.get("/api/5/all").json()
        single = client.get("/api/5/fakecollection")

    assert "fakescalar" in body
    assert "fakecollection" not in body
    assert single.status_code == 200
    assert single.json() is None


# ------------------------------------------------------------------ /args


def _make_app_with_args(config, store, args):
    """build_app() with an args namespace attached, for the /args route."""
    from glances.webserver_v5 import build_app

    return build_app(config=config, store=store, alerts=None, args=args)


def test_args_returns_the_argument_namespace(config_factory, store):
    config = config_factory()
    args = argparse.Namespace(port=61208, bind="127.0.0.1", server=True)
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        response = client.get("/api/5/args")

    assert response.status_code == 200
    assert response.json() == {"port": 61208, "bind": "127.0.0.1", "server": True}


def test_args_redacts_credentials_embedded_in_a_value(config_factory, store):
    """CVE-2026-68520 is a VALUE-level bypass: a credential inside a URL
    survives any key-name check. Asserted on the value, not on a key name."""
    config = config_factory()
    args = argparse.Namespace(export_url="http://alice:s3cr3t@influx.example:8086")
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        payload = client.get("/api/5/args").json()

    assert "s3cr3t" not in payload["export_url"]
    assert "alice" not in payload["export_url"]
    assert "influx.example" in payload["export_url"]


def test_args_redacts_a_secret_key_name(config_factory, store):
    config = config_factory()
    args = argparse.Namespace(some_token="abcdef", port=61208)
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        payload = client.get("/api/5/args").json()

    assert payload["some_token"] == "***"
    assert payload["port"] == 61208


def test_args_returns_an_empty_dict_when_no_namespace_was_supplied(config_factory, store):
    """build_app() is called without args by several tests and by any future
    embedder. The route must answer, not raise."""
    config = config_factory()
    app = _make_app_with_args(config, store, None)

    with TestClient(app) as client:
        response = client.get("/api/5/args")

    assert response.status_code == 200
    assert response.json() == {}


def test_args_redacts_the_config_file_path(config_factory, store):
    """The config file PATH discloses the local username and directory layout,
    which the config CONTENTS served by /api/5/config do not. v4 redacts its
    equivalent (`conf_file`); `_secure_value()` alone does not catch it."""
    config = config_factory()
    args = argparse.Namespace(config_path="/home/alice/.config/glances/glances.conf")
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        payload = client.get("/api/5/args").json()

    assert payload["config_path"] == "***"
    assert "alice" not in payload["config_path"]


def test_args_matches_the_real_v5_argument_set(config_factory, store):
    """Freeze the key set. Adding a CLI option fails this test on purpose, so
    its author has to decide whether the new argument is sensitive (spec 4.3).

    `set_password` comes back as "***" because `_secure_value()` matches
    "password" as a SUBSTRING of the key name and returns before its
    non-string check. It is a boolean flag, not a credential. This is the
    "over-redact rather than under-redact" behaviour the shared helper
    documents; do NOT special-case it here -- the helper is shared with
    /api/5/config and must not be loosened for cosmetics.
    """
    from glances.main_v5 import build_parser

    config = config_factory()
    args = build_parser().parse_args(["-s"])
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        payload = client.get("/api/5/args").json()

    assert set(payload) == {
        "api_doc",
        # `--arrow-keys-sort`: which arrow pair steps the sort and which
        # scrolls the command column. A display preference, like
        # `disable_cursor` and `disable_unicode` — nothing sensitive.
        "arrow_keys_sort",
        "bind",
        "byte",
        "config_path",
        "debug",
        "disable_config_exec",
        # A boolean display preference, like `disable_unicode` two lines down:
        # whether the curses UI offers a process-selection cursor. Nothing
        # sensitive, and the WebUI would read this key if the cursor ever
        # reaches the browser (2.X-b design 8.1).
        "disable_cursor",
        "disable_plugin",
        "disable_unicode",
        "disable_webui",
        "enable_mcp",
        "enable_plugin",
        "export",
        "export_csv_file",
        "export_csv_overwrite",
        "export_json_file",
        "export_process_filter",
        # The TUI's process filter (`-f`). A regex the operator typed, the
        # same shape as `export_process_filter` above it — not a credential.
        # It is also always None here: `--process-filter` is applied in TUI
        # mode, and TUI mode serves no REST API at all.
        "process_filter",
        "fahrenheit",
        "fs_free_space",
        "full_quicklook",
        "hide_public_info",
        "meangpu",
        "no_tui",
        "percpu",
        "port",
        "programs",
        "server",
        "set_password",
        "sort_processes_key",
    }
    assert payload["set_password"] == "***"
    assert payload["config_path"] == "***"
    assert payload["server"] is True


def test_token_hashes_off_the_event_loop(config_factory, store, monkeypatch):
    """Same contract as the auth middleware: PBKDF2 must not run on the loop
    the scheduler shares with the API."""
    import glances.routes_v5 as routes_v5

    calls: list[bool] = []
    real = routes_v5.verify_password

    def spy(plaintext, stored):
        try:
            asyncio.get_running_loop()
            calls.append(True)
        except RuntimeError:
            calls.append(False)
        return real(plaintext, stored)

    monkeypatch.setattr(routes_v5, "verify_password", spy)
    config = config_factory(password=hash_password("hunter2"))
    app = _make_app_with_plugins(config, store)
    with TestClient(app) as client:
        assert client.post("/api/5/token", headers=_basic_header("glances", "hunter2")).status_code == 200
        assert client.post("/api/5/token", headers=_basic_header("glances", "wrong")).status_code == 401
    assert calls == [False, False]


def test_token_rejects_a_non_ascii_username_with_401(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = _make_app_with_plugins(config, store)
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/api/5/token", headers=_basic_header("glancés", "hunter2"))
    assert r.status_code == 401


# ------------------------------------- the pinned process (2.X-b3-web)


@pytest.fixture
def engine(monkeypatch):
    """The process engine's pin state, isolated per test."""
    from glances.processes import glances_processes

    monkeypatch.setattr(glances_processes, "extended_pid", None, raising=False)
    monkeypatch.setattr(glances_processes, "extended_process", None, raising=False)
    monkeypatch.setattr(glances_processes, "disable_extended_tag", True, raising=False)
    return glances_processes


def _app_with_processes(config_factory, store, pids=(1, 42)):
    config = config_factory()
    app = _make_app_with_plugins(config, store)
    asyncio.run(store.set("processlist", {"data": [{"pid": p, "name": f"p{p}"} for p in pids]}))
    return app


def test_pinning_a_process_sets_the_engine_pin(engine, config_factory, store):
    """The same `extended_pid` the TUI's `e` sets — one pin, two ways to ask
    for it. v4 reaches the same engine from its own two POSTs
    (`glances_restful_api.py:534-537`)."""
    app = _app_with_processes(config_factory, store)

    with TestClient(app) as client:
        response = client.post("/api/5/processes/extended/42")

    assert response.status_code == 200
    assert response.json() is True
    assert engine.extended_pid == 42
    assert engine.disable_extended_tag is False


def test_pinning_clears_the_previous_accumulation(engine, config_factory, store):
    """min/max/mean accumulate into `extended_process`. Carrying the previous
    process' numbers into the new pin would misreport it."""
    app = _app_with_processes(config_factory, store)
    engine.extended_pid = 1
    engine.extended_process = {"pid": 1, "cpu_max": 99.0}

    with TestClient(app) as client:
        client.post("/api/5/processes/extended/42")

    assert engine.extended_process is None


def test_unpinning_stops_the_grab(engine, config_factory, store):
    """Clearing `extended_process` is what actually stops it — the grab is
    keyed on that being set (`processes.py:663-669`), not on the tag."""
    app = _app_with_processes(config_factory, store)
    engine.extended_pid = 42
    engine.extended_process = {"pid": 42}
    engine.disable_extended_tag = False

    with TestClient(app) as client:
        response = client.post("/api/5/processes/extended/disable")

    assert response.status_code == 200
    assert engine.extended_pid is None
    assert engine.extended_process is None
    assert engine.disable_extended_tag is True


def test_an_unknown_pid_is_refused(engine, config_factory, store):
    """A pid the caller cannot see in /api/5/processlist is not pinnable."""
    app = _app_with_processes(config_factory, store)

    with TestClient(app) as client:
        response = client.post("/api/5/processes/extended/9999")

    assert response.status_code == 404
    assert engine.extended_pid is None


def test_a_non_numeric_pid_is_rejected_before_the_handler(engine, config_factory, store):
    """v4 reaches this through `int(pid)`, which raises ValueError → 500.
    FastAPI's path type answers 422 without the handler running."""
    app = _app_with_processes(config_factory, store)

    with TestClient(app) as client:
        response = client.post("/api/5/processes/extended/notapid")

    assert response.status_code == 422
    assert engine.extended_pid is None


def test_the_pin_route_is_not_captured_by_the_plugin_catch_all(engine, config_factory, store):
    """`/{plugin_name}` sits at the end of the router. If the pin route were
    declared after it, `processes` would be read as a plugin name."""
    app = _app_with_processes(config_factory, store)

    with TestClient(app) as client:
        assert client.post("/api/5/processes/extended/42").status_code == 200
        # ... and the catch-all still answers for a real unknown plugin.
        assert client.get("/api/5/nosuchplugin").status_code == 404


def test_pinning_is_refused_when_nothing_has_been_published(engine, config_factory, store):
    """Cycle 0: no process list, so no pid is pinnable — and the handler must
    say 404 rather than raise on an absent payload."""
    config = config_factory()
    app = _make_app_with_plugins(config, store)

    with TestClient(app) as client:
        assert client.post("/api/5/processes/extended/1").status_code == 404
