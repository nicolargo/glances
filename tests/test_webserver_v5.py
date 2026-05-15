#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the FastAPI app skeleton.

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- build_app returns a configured FastAPI app exposing state
- /status and /healthz: 200 OK, identical payload, no auth required
- Swagger / ReDoc default-on, disabled when api_doc=false
- AuthMiddleware: Basic round-trip, Bearer round-trip, wrong creds → 401
- AuthMiddleware: probes exempt even when auth is configured
- AuthMiddleware: not wired when password is absent
- CORSMiddleware: origin allowlist enforced; wildcard + credentials downgrade
- TrustedHostMiddleware: hostname allowlist enforced; warning when bind is non-loopback
- Startup WARNING when running unauthenticated
- /docs and /redoc reachable; api_doc=false → 404
"""

from __future__ import annotations

import base64
import logging

import pytest
from fastapi.testclient import TestClient

from glances.config_v5 import GlancesConfigV5
from glances.security_v5 import hash_password
from glances.stats_store_v5 import StatsStoreV5
from glances.webserver_v5 import build_app

# ----------------------------------------------------------------- fixtures


@pytest.fixture
def config_factory(tmp_path, monkeypatch):
    """Build a hermetic ``GlancesConfigV5`` and let tests overlay ``[outputs]`` keys."""

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("GLANCES_CONFIG_FILE", raising=False)
    # Strip any pre-existing GLANCES_* env vars so tests are deterministic.
    for env_key in list(__import__("os").environ):
        if env_key.startswith("GLANCES_"):
            monkeypatch.delenv(env_key, raising=False)

    def make(**outputs) -> GlancesConfigV5:
        for key, value in outputs.items():
            env_var = f"GLANCES_OUTPUTS__{key.upper()}"
            monkeypatch.setenv(env_var, str(value))
        return GlancesConfigV5()

    return make


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


# ------------------------------------------------------------- build_app


def test_build_app_exposes_state(config_factory, store):
    config = config_factory()
    app = build_app(config=config, store=store)
    assert app.state.config is config
    assert app.state.store is store
    assert app.state.alerts is None
    assert app.state.jwt_handler is None


def test_build_app_with_alerts_object(config_factory, store):
    config = config_factory()
    sentinel = object()
    app = build_app(config=config, store=store, alerts=sentinel)  # type: ignore[arg-type]
    assert app.state.alerts is sentinel


# ------------------------------------------------------------- health probes


def test_status_endpoint(config_factory, store):
    config = config_factory()
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        r = client.get("/status")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": "5"}


def test_healthz_alias_returns_same_payload(config_factory, store):
    config = config_factory()
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        status = client.get("/status").json()
        healthz = client.get("/healthz").json()
    assert status == healthz


def test_probes_exempt_from_auth(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        # No Authorization header at all — must still pass.
        assert client.get("/status").status_code == 200
        assert client.get("/healthz").status_code == 200


# ------------------------------------------------------------- auth basic


def _basic_header(user: str, password: str) -> dict[str, str]:
    encoded = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {encoded}"}


def test_basic_auth_accepts_correct_credentials(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store)
    # Plant a non-probe route so we exercise the middleware on a path that
    # is *not* in UNAUTH_PATHS. Otherwise the request bypasses auth entirely.
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app) as client:
        r = client.get("/secret", headers=_basic_header("glances", "hunter2"))
    assert r.status_code == 200


def test_basic_auth_rejects_wrong_password(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app) as client:
        r = client.get("/secret", headers=_basic_header("glances", "wrong"))
    assert r.status_code == 401
    assert "Basic" in r.headers.get("WWW-Authenticate", "")


def test_basic_auth_rejects_wrong_username(config_factory, store):
    config = config_factory(password=hash_password("hunter2"), username="alice")
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app) as client:
        r = client.get("/secret", headers=_basic_header("glances", "hunter2"))
    assert r.status_code == 401


def test_basic_auth_rejects_missing_authorization(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app) as client:
        r = client.get("/secret")
    assert r.status_code == 401


def test_basic_auth_rejects_garbage_basic_header(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app) as client:
        # Invalid base64 in the Basic credentials section.
        r = client.get("/secret", headers={"Authorization": "Basic !!!notb64!!!"})
    assert r.status_code == 401


# ------------------------------------------------------------- auth bearer


def test_bearer_auth_accepts_valid_jwt(config_factory, store):
    config = config_factory(
        password=hash_password("hunter2"),
        jwt_secret_key="stable-secret",
    )
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    token = app.state.jwt_handler.create_access_token("glances")
    with TestClient(app) as client:
        r = client.get("/secret", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_bearer_auth_rejects_invalid_jwt(config_factory, store):
    config = config_factory(
        password=hash_password("hunter2"),
        jwt_secret_key="stable-secret",
    )
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app) as client:
        r = client.get("/secret", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"


# ------------------------------------------------------------- no auth


def test_no_auth_when_password_absent(config_factory, store):
    config = config_factory()
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    assert app.state.jwt_handler is None
    with TestClient(app) as client:
        # No auth configured → routes are open.
        assert client.get("/secret").status_code == 200


def test_warning_logged_when_unauthenticated(config_factory, store, caplog):
    config = config_factory()
    with caplog.at_level(logging.WARNING):
        build_app(config=config, store=store)
    assert any("unauthenticated" in rec.message for rec in caplog.records)


# ------------------------------------------------------------- CORS


def test_cors_allowlist_enforced(config_factory, store):
    config = config_factory(cors_origins="https://allowed.example")
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        # Allowed origin → ACAO echoed back.
        r = client.get("/status", headers={"Origin": "https://allowed.example"})
        assert r.headers.get("access-control-allow-origin") == "https://allowed.example"
        # Disallowed origin → header absent.
        r = client.get("/status", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in r.headers


def test_cors_wildcard_with_credentials_downgrades(config_factory, store, caplog):
    config = config_factory(cors_origins="*", cors_allow_credentials="true")
    with caplog.at_level(logging.WARNING):
        app = build_app(config=config, store=store)
    assert any("CORS spec" in rec.message or "CVE-2026-32610" in rec.message for rec in caplog.records)
    with TestClient(app) as client:
        r = client.get("/status", headers={"Origin": "https://any.example"})
    # The wildcard is honoured but credentials are off.
    assert r.headers.get("access-control-allow-origin") == "*"
    assert r.headers.get("access-control-allow-credentials") is None


def test_cors_absent_by_default(config_factory, store):
    config = config_factory()
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        r = client.get("/status", headers={"Origin": "https://any.example"})
    assert "access-control-allow-origin" not in r.headers


# ------------------------------------------------------------- TrustedHost


def test_trusted_host_allowlist_enforced(config_factory, store):
    config = config_factory(webui_allowed_hosts="glances.example,glances.local")
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        r = client.get("/status", headers={"Host": "glances.example"})
        assert r.status_code == 200
        r = client.get("/status", headers={"Host": "evil.example"})
        assert r.status_code == 400


def test_trusted_host_warning_when_bind_non_loopback(config_factory, store, caplog):
    config = config_factory(bind_address="0.0.0.0")
    with caplog.at_level(logging.WARNING):
        build_app(config=config, store=store)
    assert any("webui_allowed_hosts" in rec.message for rec in caplog.records)


def test_trusted_host_no_warning_when_bind_loopback(config_factory, store, caplog):
    config = config_factory(bind_address="127.0.0.1")
    with caplog.at_level(logging.WARNING):
        build_app(config=config, store=store)
    assert not any("webui_allowed_hosts" in rec.message for rec in caplog.records)


# ------------------------------------------------------------- docs


def test_docs_default_on(config_factory, store):
    config = config_factory()
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_docs_disabled_by_config(config_factory, store):
    config = config_factory(api_doc="false")
    app = build_app(config=config, store=store)
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404


# ------------------------------------------------------------- attach_mcp (G3-MCP Task 2)


def _has_mount(app, prefix: str) -> bool:
    """Return True if `app` has a Mount route whose path starts with `prefix`."""
    from starlette.routing import Mount

    return any(isinstance(r, Mount) and r.path == prefix for r in app.routes)


def test_build_app_does_not_mount_mcp_by_default(config_factory, store):
    """Without [outputs] enable_mcp=true, /mcp must NOT be mounted."""
    config = config_factory()
    app = build_app(config=config, store=store)
    assert not _has_mount(app, "/mcp")
    with TestClient(app) as client:
        assert client.get("/mcp").status_code == 404


def test_attach_mcp_skips_when_gate_off(config_factory, store):
    from glances.webserver_v5 import attach_mcp

    config = config_factory()
    app = build_app(config=config, store=store)
    attached = attach_mcp(app, config=config, store=store, plugins=[])
    assert attached is False
    assert not _has_mount(app, "/mcp")


def test_attach_mcp_mounts_when_gate_on(config_factory, store):
    """[outputs] enable_mcp=true → /mcp is mounted."""
    from glances.webserver_v5 import attach_mcp

    config = config_factory(enable_mcp="true")
    app = build_app(config=config, store=store)
    attached = attach_mcp(app, config=config, store=store, plugins=[])
    assert attached is True
    assert _has_mount(app, "/mcp")


def test_attach_mcp_records_server_in_app_state(config_factory, store):
    """Successful attach exposes the MCP server via app.state for diagnostics."""
    from glances.webserver_v5 import attach_mcp

    config = config_factory(enable_mcp="true")
    app = build_app(config=config, store=store)
    attach_mcp(app, config=config, store=store, plugins=[])
    assert app.state.mcp_server is not None


def test_attach_mcp_skipped_path_emits_no_warning(config_factory, store, caplog):
    """Gate off is the common case — must not log anything."""
    from glances.webserver_v5 import attach_mcp

    config = config_factory()
    app = build_app(config=config, store=store)
    with caplog.at_level(logging.WARNING):
        attach_mcp(app, config=config, store=store, plugins=[])
    mcp_warnings = [r for r in caplog.records if "MCP" in r.message and r.levelno >= logging.WARNING]
    assert mcp_warnings == []


def test_attach_mcp_logs_known_v5_gaps(config_factory, store, caplog):
    """Operators must see, on mount, which v4 plugins MCP cannot expose yet."""
    from glances.webserver_v5 import attach_mcp

    config = config_factory(enable_mcp="true")
    app = build_app(config=config, store=store)
    with caplog.at_level(logging.INFO):
        attach_mcp(app, config=config, store=store, plugins=[])

    msgs = " ".join(r.message for r in caplog.records if r.levelno == logging.INFO)
    assert "not yet ported" in msgs
    # The canonical missing v4 plugins must be named so operators can
    # match the message against MCP client errors.
    for missing in ("processlist", "fs", "diskio", "memswap"):
        assert missing in msgs


def test_attach_mcp_logs_history_limitation(config_factory, store, caplog):
    """A single INFO line surfaces the deferred history semantic."""
    from glances.webserver_v5 import attach_mcp

    config = config_factory(enable_mcp="true")
    app = build_app(config=config, store=store)
    with caplog.at_level(logging.INFO):
        attach_mcp(app, config=config, store=store, plugins=[])

    msgs = " ".join(r.message for r in caplog.records if r.levelno == logging.INFO)
    assert "history" in msgs.lower()
    assert "empty" in msgs.lower()


def test_attach_mcp_logs_when_package_missing(config_factory, store, monkeypatch, caplog):
    """If MCP_AVAILABLE is False, attach_mcp returns False + clear WARN."""
    from glances.outputs import glances_mcp
    from glances.webserver_v5 import attach_mcp

    monkeypatch.setattr(glances_mcp, "MCP_AVAILABLE", False)

    config = config_factory(enable_mcp="true")
    app = build_app(config=config, store=store)
    with caplog.at_level(logging.WARNING):
        attached = attach_mcp(app, config=config, store=store, plugins=[])

    assert attached is False
    assert not _has_mount(app, "/mcp")
    msgs = " ".join(r.message for r in caplog.records if r.levelno >= logging.WARNING)
    assert "mcp" in msgs.lower()
    assert "pip install" in msgs


# ------------------------------------------------------------- helper


async def _ok_handler():
    return {"ok": True}
