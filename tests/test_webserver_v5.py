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

import argparse
import asyncio
import base64
import logging

import pytest
from fastapi.testclient import TestClient

from glances import __version__
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
    # `version` is the API version; `glances_version` is the release, which the
    # WebUI footer reads from here (v4 serves it from its own /status too).
    assert r.json() == {"status": "ok", "version": "5", "glances_version": __version__}


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


def test_cors_multi_origin_allowlist_with_wildcard_downgrades(config_factory, store, caplog):
    """A multi-entry allowlist containing '*' must still trip the credentials guard.

    v4's guard used exact list equality (`cors_origins == ["*"]`), which a
    multi-origin allowlist like `*,https://trusted` slipped past
    (GHSA-fp27-88fp-2phg). v5's `_wire_cors` uses a membership test; this
    locks that in.
    """
    config = config_factory(cors_origins="*,https://trusted.example", cors_allow_credentials="true")
    with caplog.at_level(logging.WARNING):
        app = build_app(config=config, store=store)
    assert any("CORS spec" in rec.message or "CVE-2026-32610" in rec.message for rec in caplog.records)
    with TestClient(app) as client:
        r = client.get("/status", headers={"Origin": "https://trusted.example"})
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


def test_trusted_host_warning_follows_the_cli_bind(config_factory, store, caplog):
    """`--bind` overrides `[outputs] bind_address` (main_v5.assemble): the
    warning must follow the address actually bound, in both directions."""
    exposed = argparse.Namespace(bind="0.0.0.0", disable_webui=True)
    with caplog.at_level(logging.WARNING):
        build_app(config=config_factory(), store=store, args=exposed)
    assert any("webui_allowed_hosts" in rec.message for rec in caplog.records)

    caplog.clear()
    loopback = argparse.Namespace(bind="127.0.0.1", disable_webui=True)
    with caplog.at_level(logging.WARNING):
        build_app(config=config_factory(bind_address="0.0.0.0"), store=store, args=loopback)
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


def test_attach_mcp_does_not_log_gaps_when_registry_complete(config_factory, store, caplog):
    """Every v4 plugin is ported to v5 as of G4-processlist — the
    "not yet ported" line must NOT appear at MCP mount time.

    If ``KNOWN_V5_MISSING_PLUGINS`` ever grows again (a regression port
    or a new v4-only plugin), flip this test to re-assert the gap list.
    """
    from glances.webserver_v5 import attach_mcp

    config = config_factory(enable_mcp="true")
    app = build_app(config=config, store=store)
    with caplog.at_level(logging.INFO):
        attach_mcp(app, config=config, store=store, plugins=[])

    msgs = " ".join(r.message for r in caplog.records if r.levelno == logging.INFO)
    assert "not yet ported" not in msgs


def test_attach_mcp_no_longer_announces_a_history_gap(config_factory, store, caplog):
    """The INFO line announcing empty history datasets went with the history
    store (design 2026-09-26 §5.6): MCP now serves real history."""
    from glances.webserver_v5 import attach_mcp

    config = config_factory(enable_mcp="true")
    app = build_app(config=config, store=store)
    with caplog.at_level(logging.INFO):
        attach_mcp(app, config=config, store=store, plugins=[])

    msgs = " ".join(r.message for r in caplog.records if r.levelno == logging.INFO)
    assert "history" not in msgs.lower()


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


# ------------------------------------------------------- WebUI serving (G9-1)


def _args(**overrides):
    base = {"disable_webui": False}
    base.update(overrides)
    return argparse.Namespace(**base)


def test_index_is_served_when_the_webui_is_enabled(config_factory, store):
    app = build_app(config=config_factory(), store=store, args=_args())

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "glances5.js" in response.text


def test_static_directory_is_mounted(config_factory, store):
    """Asserted against the v4 bundle, which is committed in public/ --
    glances5.js does not exist until Task 3."""
    app = build_app(config=config_factory(), store=store, args=_args())

    with TestClient(app) as client:
        response = client.get("/static/glances.js")

    assert response.status_code == 200


def test_disable_webui_unregisters_both_routes(config_factory, store):
    """Assert on the route table, not on a 404: a 404 can come from anywhere,
    and a disabled WebUI must not leave the asset directory reachable."""
    app = build_app(config=config_factory(), store=store, args=_args(disable_webui=True))

    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/" not in paths
    assert "/static" not in paths

    with TestClient(app) as client:
        assert client.get("/").status_code == 404
        assert client.get("/static/glances.js").status_code == 404


def test_webui_is_absent_when_no_args_namespace_is_supplied(config_factory, store):
    """build_app() without args is the embedder / unit-test path. It must not
    start serving a UI by accident."""
    app = build_app(config=config_factory(), store=store)

    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/" not in paths


def test_index_requires_authentication_when_a_password_is_configured(config_factory, store):
    """UNAUTH_PATHS is {"/status", "/healthz", "/api/5/token"}, so the WebUI
    is behind auth -- v4 parity. Pinned so a future UNAUTH_PATHS edit cannot
    expose it silently."""
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store, args=_args())

    with TestClient(app) as client:
        assert client.get("/").status_code == 401
        assert client.get("/", headers=_basic_header("glances", "hunter2")).status_code == 200


def test_cors_policy_applies_to_the_index(config_factory, store):
    """Spec 5 claims `/` inherits the CORS wiring. A new route silently
    falling outside a middleware is how these protections rot, so verify it
    rather than assume it."""
    config = config_factory(cors_origins="https://trusted.example")
    app = build_app(config=config, store=store, args=_args())

    with TestClient(app) as client:
        allowed = client.get("/", headers={"Origin": "https://trusted.example"})
        denied = client.get("/", headers={"Origin": "https://evil.example"})

    assert allowed.headers.get("access-control-allow-origin") == "https://trusted.example"
    assert "access-control-allow-origin" not in denied.headers


def test_trusted_host_middleware_applies_to_the_index(config_factory, store):
    """TrustedHostMiddleware is the outermost middleware, so a new route
    inherits DNS-rebinding protection. Verify rather than assume."""
    config = config_factory(webui_allowed_hosts="trusted.example")
    app = build_app(config=config, store=store, args=_args())

    with TestClient(app) as client:
        assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
        assert client.get("/", headers={"Host": "trusted.example"}).status_code == 200


def test_webui_missing_assets_warns_and_falls_back_to_rest_only(config_factory, store, monkeypatch, tmp_path, caplog):
    """A source checkout or a trimmed package with no `npm run build` must
    still serve the REST API: the missing-assets guard in _wire_webui() logs
    a WARNING and skips the WebUI routes instead of crashing build_app()."""
    from glances import webserver_v5

    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(webserver_v5, "_STATIC_PATH", missing / "public")
    monkeypatch.setattr(webserver_v5, "_TEMPLATE_PATH", missing / "templates")

    with caplog.at_level(logging.WARNING):
        app = build_app(config=config_factory(), store=store, args=_args())

    assert any("WebUI assets not found" in r.message for r in caplog.records)

    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/" not in paths
    assert "/static" not in paths

    with TestClient(app) as client:
        assert client.get("/status").status_code == 200


def test_the_v5_bundle_is_served(config_factory, store):
    """The bundle is a build artifact. If this fails with 404, run
    `npm run build` in glances/outputs/static/ before looking anywhere else."""
    app = build_app(config=config_factory(), store=store, args=_args())

    with TestClient(app) as client:
        response = client.get("/static/glances5.js")

    assert response.status_code == 200
    assert len(response.content) > 0


def _off_loop_spy(calls: list[bool], real):
    """Wrap verify_password, recording whether it ran on the event loop thread."""

    def spy(plaintext, stored):
        try:
            asyncio.get_running_loop()
            calls.append(True)
        except RuntimeError:
            calls.append(False)
        return real(plaintext, stored)

    return spy


def test_basic_auth_hashes_off_the_event_loop(config_factory, store, monkeypatch):
    """PBKDF2 (100k iterations, ~50 ms) on the event loop stalls the API and
    the scheduler, which share that loop — one wrong-password flood freezes
    stats collection. v4 ran the check in a threadpool."""
    import glances.webserver_v5 as webserver_v5

    calls: list[bool] = []
    monkeypatch.setattr(webserver_v5, "verify_password", _off_loop_spy(calls, webserver_v5.verify_password))
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app) as client:
        assert client.get("/secret", headers=_basic_header("glances", "hunter2")).status_code == 200
        assert client.get("/secret", headers=_basic_header("glances", "wrong")).status_code == 401
    assert calls == [False, False]


def test_basic_auth_rejects_a_non_ascii_username_with_401(config_factory, store):
    """`hmac.compare_digest` raises TypeError on a non-ASCII str: the request
    used to end in a 500 instead of a plain 401."""
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store)
    app.add_api_route("/secret", _ok_handler, methods=["GET"])
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/secret", headers=_basic_header("glancés", "hunter2"))
    assert r.status_code == 401
