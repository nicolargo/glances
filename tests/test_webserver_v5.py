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
import base64
import json
import logging
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from glances.config_v5 import GlancesConfigV5
from glances.outputs.curses_renderer_v5 import HEADER_SLOT_LEFT, HEADER_SLOT_RIGHT, LEFT_SLOT, RIGHT_SLOT, TOP_SLOT
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


_BUNDLE_PATH = Path(__file__).parent.parent / "glances" / "outputs" / "static" / "public" / "glances5.js"
_RENDER_PROBE_PATH = Path(__file__).parent / "fixtures" / "webui_render_probe.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_v5_bundle_actually_renders_an_element():
    """Guards against a silent, all-tests-green blank page.

    `import { createApp } from "vue"` resolves to Vue's runtime-only build
    unless webpack aliases it to the compiler-included build. A component
    that only supplies a string `template:` (as app_v5.js does) then gets
    `render = NOOP` -- in production mode the dev warning for this is
    compiled out, so nothing is logged and nothing throws. The mount target
    ends up holding a single, silently-empty comment node instead of real
    markup.

    Every HTTP-level test in this file (e.g. test_the_v5_bundle_is_served)
    only checks that the bundle is served with a non-empty body -- a bundle
    that renders nothing passes all of them. This test instead runs the
    actual bundle against a minimal DOM stub and asserts that the `#app`
    mount target ends up containing a real ELEMENT node, not just Vue's
    empty-render comment placeholder -- the distinction Finding 1 hinged on.

    G9-2's AppShell also renders a bare `<main>`, so a `tagName == "MAIN"`
    check alone would pass against a stub as blank as G9-1's -- e.g. a
    `createApp({ template: "<main></main>" })`. Assert markup that only the
    real shell (header + plugin area + footer) produces and that a blank
    page cannot satisfy: the `gl-app` class and both a HEADER and a FOOTER
    descendant.

    The fixture's `fetch` stub answers `api/5/alert` with twelve events in the
    real `_build_event()` shape (glances/alerts_v5.py:706-716), oldest first
    -- matching get_history()'s documented most-recent-LAST contract
    (glances/alerts_v5.py:181). Assert the footer actually renders them --
    identified by plugin AND field, not just the bare level, so a fallback to
    a field that does not exist cannot pass unnoticed -- AND that it keeps the
    ten MOST RECENT, newest first: a single-alert stub could not catch
    AppShell using `history.slice(0, 10)` (the ten OLDEST) instead of the
    correct `history.slice(-10).reverse()`, which is exactly the bug that
    shipped in the previous fix round. This is exactly the shape the G9-1
    blank page took: an untested corner of an otherwise-green test suite --
    and the corner turned out deeper than the first probe fix realised.
    """
    if not _BUNDLE_PATH.exists():
        pytest.fail(f"{_BUNDLE_PATH} is missing -- run `npm run build` in glances/outputs/static/")

    result = subprocess.run(
        ["node", str(_RENDER_PROBE_PATH), str(_BUNDLE_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"render probe crashed:\n{result.stderr}"
    # A thrown exception inside AppShell's async mounted() hook (e.g. a
    # sandbox missing a global it calls) does not necessarily flip the exit
    # code -- it can land as stderr noise on an otherwise-green run. Assert
    # stderr is empty so a broken lifecycle hook cannot hide behind a
    # passing returncode again.
    assert result.stderr == "", f"render probe printed to stderr:\n{result.stderr}"

    payload = json.loads(result.stdout)
    # nodeType 1 == ELEMENT_NODE, 8 == COMMENT_NODE (the runtime-only-Vue
    # failure mode). Assert the concrete element, not just "has children":
    # a broken build also has exactly one child -- an empty comment.
    assert payload["nodeType"] == 1, (
        f"expected an ELEMENT_NODE under #app, got nodeType={payload['nodeType']!r} "
        f"(tagName={payload['tagName']!r}) -- the Vue template rendered nothing"
    )
    assert payload["tagName"] == "MAIN"
    assert payload["hasClass"], "expected the root <main> to carry class 'gl-app'"
    assert payload["hasHeader"], "expected a <header> descendant of the app shell"
    assert payload["hasFooter"], "expected a <footer> descendant of the app shell"
    # The stub's api/5/alert fixture carries plugin="pluginN", field="total"
    # for N in 0..11, oldest (0) first -- get_history()'s documented order.
    # A footer that renders only the level (e.g. a fallback to a
    # non-existent `description` field) would show "critical" with no
    # plugin/field at all -- assert both are present for the regression
    # from fix round 1.
    footer_text = payload["footerText"] or ""
    assert "plugin11" in footer_text and "total" in footer_text, (
        f"expected the footer to identify the alert by plugin and field, got {footer_text!r}"
    )
    # The two OLDEST alerts must have been dropped (only 10 of 12 shown) --
    # `history.slice(0, 10)` would keep these and drop the newest two
    # instead, which is the regression from fix round 2. Match "pluginN "
    # (with the trailing space before " total"), not a bare substring:
    # "plugin1" is also a substring of "plugin10" and "plugin11".
    assert "plugin0 " not in footer_text and "plugin1 " not in footer_text, (
        f"expected the two oldest alerts dropped, got {footer_text!r}"
    )
    # Newest first: plugin11 (most recent) must render before plugin2
    # (oldest of the ten kept) -- a `slice(-10)` without `.reverse()` would
    # still keep the right ten alerts but in oldest-first order.
    assert footer_text.index("plugin11") < footer_text.index("plugin2"), (
        f"expected newest-first order, got {footer_text!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_registry_renders_every_registered_plugin():
    """Proves plugins/index.js is wired up end to end, not just importable.

    G9-3 replaced AppShell's four hardcoded per-plugin surfaces (import,
    components map, spec list, template tag) with a loop over
    `PLUGINS` from `plugins/index.js`. A regression here would not be a
    missing import -- the bundle would still build -- it would be a loop
    that silently renders zero, or only one, of the registered plugins.

    Each plugin component renders an <article class="gl-plugin"> carrying
    its registry name as `data-plugin` (PluginMem.vue -> "mem",
    PluginNetwork.vue -> "network", PluginLoad.vue -> "load",
    PluginMemswap.vue -> "memswap", PluginCpu.vue -> "cpu",
    PluginGpu.vue -> "gpu"). Assert all are
    present, not just "some markup exists": a loop that iterates only
    `PLUGINS[0]` would still produce one gl-plugin article and could pass a
    weaker assertion.

    The order is the DOCUMENT order, i.e. zone by zone: a registry entry
    whose `slot` is missing or misspelled is rendered in no zone at all, and
    this explicit list is what catches it -- the drift guard below only sees
    what rendered.
    """
    if not _BUNDLE_PATH.exists():
        pytest.fail(f"{_BUNDLE_PATH} is missing -- run `npm run build` in glances/outputs/static/")

    result = subprocess.run(
        ["node", str(_RENDER_PROBE_PATH), str(_BUNDLE_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"render probe crashed:\n{result.stderr}"
    assert result.stderr == "", f"render probe printed to stderr:\n{result.stderr}"

    payload = json.loads(result.stdout)
    assert payload["pluginNames"] == [
        "system",
        "ip",
        "uptime",
        "cloud",
        "now",
        "cpu",
        "gpu",
        "mem",
        "memswap",
        "load",
        "network",
    ], f"expected all registered plugins to render, got {payload['pluginNames']!r}"


_TUI_SLOTS = {
    "header-left": HEADER_SLOT_LEFT,
    "header-right": HEADER_SLOT_RIGHT,
    "top": TOP_SLOT,
    "left": LEFT_SLOT,
    "right": RIGHT_SLOT,
}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_every_slot_orders_its_plugins_like_the_tui():
    """The drift guard G9-5's decision D4 depends on.

    The WebUI keeps its own copy of the TUI's slot lists (a `slot` attribute
    per entry in plugins/index.js, order = registry order). Nothing prevents
    the two copies from drifting apart; this test makes drift a failure. It
    compares the RENDERED layout -- not the registry source -- against the
    tuples imported from glances.outputs.curses_renderer_v5, which it must
    never restate.

    For each slot container, the plugins rendered in it must be exactly the
    TUI tuple for that slot, filtered to the plugins that rendered, in the
    tuple's order. A plugin placed in the wrong slot is absent from that
    slot's tuple and fails; two plugins swapped within a slot fail on order.
    """
    payload = _run_render_probe("default")
    rendered = payload["pluginNames"]
    slots = payload["slots"]

    assert rendered, "vacuous: nothing rendered"
    assert set(slots) <= set(_TUI_SLOTS), f"a slot the TUI does not have rendered: {sorted(slots)!r}"
    placed = [name for names in slots.values() for name in names]
    assert sorted(placed) == sorted(rendered), f"every plugin must sit in exactly one slot: {slots!r}"
    for slot, names in slots.items():
        expected = [name for name in _TUI_SLOTS[slot] if name in rendered]
        assert names == expected, f"slot {slot!r}: rendered {names!r}, the TUI orders {expected!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_plugin_the_server_did_not_instantiate_is_not_rendered():
    """A disabled plugin is never instantiated (glances/main_v5.py:372), so it
    is never in /api/5/all, and before G9-5 the WebUI showed it as "loading…"
    forever. `gpu-disabled` answers /api/5/pluginslist without `gpu`.
    """
    payload = _run_render_probe("gpu-disabled")
    assert "gpu" not in payload["pluginNames"], f"gpu is disabled: {payload['pluginNames']!r}"
    assert "cpu" in payload["pluginNames"], f"vacuous: the other plugins must still render: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unreadable_pluginslist_renders_the_whole_registry():
    """/api/5/pluginslist failing must degrade to the pre-G9-5 behaviour --
    every registered plugin rendered -- never to an empty page.
    """
    payload = _run_render_probe("pluginslist-unreachable")
    assert payload["pluginNames"] == [
        "system",
        "ip",
        "uptime",
        "cloud",
        "now",
        "cpu",
        "gpu",
        "mem",
        "memswap",
        "load",
        "network",
    ], f"expected the whole registry, got {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_refresh_cadence_renders_in_the_footer():
    """G9-5 decision D5: the top bar is gone and the cadence moved to the
    footer. The probe answers /api/5/config with `{}`, so the cadence is
    api.js' DEFAULT_REFRESH_SECONDS (2).
    """
    payload = _run_render_probe("default")
    assert "refresh 2s" in (payload["footerText"] or ""), f"got {payload['footerText']!r}"


# --------------------------------------------------------- mem TUI parity (G9-3 Task 5)


def _run_render_probe(scenario: str) -> dict:
    if not _BUNDLE_PATH.exists():
        pytest.fail(f"{_BUNDLE_PATH} is missing -- run `npm run build` in glances/outputs/static/")

    result = subprocess.run(
        ["node", str(_RENDER_PROBE_PATH), str(_BUNDLE_PATH), scenario],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"render probe crashed:\n{result.stderr}"
    assert result.stderr == "", f"render probe printed to stderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mem_renders_all_eight_statistics_with_avail():
    """`render_curses_v5.py`'s reference block (module docstring, lines
    16-28) is eight (label, value) pairs: percent, total, avail, free,
    active, inactive, buffers, cached. The probe's `api/5/all` stub answers
    with the `mem-with-available` fixture -- a full psutil-shaped payload
    that HAS `available` -- so this asserts every one of the eight
    formatted values actually reaches the DOM, and that the avail/used
    switch shows `avail`: the fixture's `used` field carries a DIFFERENT
    value (9.0G) than `available` (8.0G) specifically so a component that
    rendered `used` instead, or both, could not pass unnoticed.
    """
    payload = _run_render_probe("mem-with-available")
    mem_text = payload["pluginText"].get("mem", "")

    for expected in ("53.2%", "16.0G", "8.0G", "2.0G", "5.0G", "4.0G", "100.0M", "3.0G"):
        assert expected in mem_text, f"expected {expected!r} in the MEM plugin text, got {mem_text!r}"
    assert "avail" in mem_text, f"expected the 'avail' label in the MEM plugin text, got {mem_text!r}"
    assert "9.0G" not in mem_text, f"expected 'used' (9.0G) NOT shown when 'available' is present: {mem_text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mem_shows_used_when_available_is_absent():
    """Avail/used switch, other side: the `mem-no-available` fixture omits
    `available` entirely (e.g. a BSD without it), so the component must fall
    back to showing `used` -- and the `avail` label must not appear at all.
    """
    payload = _run_render_probe("mem-no-available")
    mem_text = payload["pluginText"].get("mem", "")

    for expected in ("53.2%", "16.0G", "9.0G", "2.0G", "5.0G", "4.0G", "100.0M", "3.0G"):
        assert expected in mem_text, f"expected {expected!r} in the MEM plugin text, got {mem_text!r}"
    assert "avail" not in mem_text, f"expected no 'avail' label when 'available' is absent: {mem_text!r}"


# ------------------------------------------------- network TUI parity (labels)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_column_headers_are_the_tui_strings():
    """The WebUI's network column headers must be the TUI's, not field names.

    `PluginNetwork.vue` resolves every header through `labelFor()`, i.e. from
    `/api/5/<plugin>/info` = `NetworkPluginModel.fields_description`. With no
    `short_name` declared there the headers degrade to `interface_name` /
    `bytes_recv` / `bytes_sent`, while the TUI block
    (`glances/plugins/network/render_curses_v5.py`) reads `NETWORK` / `Rx/s`
    / `Tx/s` -- i.e. the WebUI would move AWAY from TUI parity.

    The probe's `/info` stub is keyed by plugin name and carries the network
    schema's own short_names, so this observes the RESOLVED headers: with the
    mem schema answering every `/info` (as it did before this fix) the
    assertion below fails on field names.
    """
    payload = _run_render_probe("network")
    headers = payload["pluginColumnHeaders"].get("network")

    assert headers == ["interface", "Rx/s", "Tx/s"], f"expected the TUI's network headers, got {headers!r}"


def test_network_schema_declares_the_tui_short_names():
    """Pin the schema the WebUI's network headers resolve from.

    `test_network_column_headers_are_the_tui_strings` renders through the
    probe, whose `/info` stub is a hand-copied mirror of this schema -- so it
    passes even if `short_name` is dropped from the real plugin. This asserts
    the source instead: drop a `short_name` here and the WebUI silently falls
    back to field names (`labelFor()` degrades to the field name by design),
    with no other test noticing.
    """
    from glances.plugins.network.model_v5 import PluginModel

    fields = PluginModel.fields_description
    assert fields["interface_name"]["short_name"] == "interface"
    assert fields["bytes_recv"]["short_name"] == "Rx/s"
    assert fields["bytes_sent"]["short_name"] == "Tx/s"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_server_args_does_not_leak_into_the_dom_as_an_attribute():
    """Every component must DECLARE `serverArgs`, even when it ignores it.

    Vue turns an undeclared prop into a fallthrough attribute, so a component
    missing the declaration renders `server-args="[object Object]"` onto its
    root <article> -- AppShell.vue binds it as `:server-args`, and Vue keeps
    that exact kebab-case key on an undeclared attribute, it does not
    concatenate it to `serverargs`. Verified by actually deleting the prop
    declaration from PluginMem.vue and observing the probe emit
    `"server-args"` in `pluginAttrs.mem` before restoring it. This observes
    the rendered attribute rather than the source, so it fails for a
    component added later that forgets the line.
    """
    payload = _run_render_probe("mem-with-available")
    # Without this the loop below is vacuous: an empty `pluginAttrs` (a probe
    # that stopped collecting the attribute, a render that produced no
    # article) would pass silently. Eleven is the registry size asserted by
    # test_the_registry_renders_every_registered_plugin.
    assert len(payload["pluginAttrs"]) == 11, f"expected all eleven plugins' attributes, got {payload['pluginAttrs']!r}"
    for name, attrs in payload["pluginAttrs"].items():
        assert "server-args" not in attrs, f"{name} leaked serverArgs as an attribute: {attrs!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_every_scalar_grid_renders_its_values_with_the_same_classes():
    """The five `.gl-stat-grid` plugins must dress their <dd>s identically.

    `.gl-num` is not only alignment: `css/v5.css` floors it at 9ch, a width
    sized for `formatRate()`'s worst case ("1023.9G/s") in a collection
    TABLE. On a scalar <dd> that floor is too wide for any non-rate value --
    load's "0.86" in a 9ch cell -- and, being on the <dd>, it would also widen
    the prominent badge past its text. A scalar column's width floor lives on
    the grid COLUMN instead (`.gl-stat-grid dl`, 9ch only for `gl-col-rate`),
    and jitter-free digits come from `font-variant-numeric: tabular-nums` on
    `.gl-stat-grid dd`, which costs no width.

    So the only class a scalar value cell may carry is its tier
    (`gl-level-*`), and every one of the five must agree. Observed through
    the rendered class lists, not the component sources: a comment asking the
    next port to "keep these consistent" is not a test.

    `.gl-num` on the COLLECTION tables is untouched and still asserted by
    test_network_rate_columns_are_marked_numeric.
    """
    payload = _run_render_probe("scalar-grids")

    non_tier = {}
    for name in ("mem", "load", "memswap", "cpu", "gpu"):
        classes = payload["pluginValueClasses"].get(name)
        assert classes, f"{name} rendered no value cells: {payload['pluginValueClasses']!r}"
        non_tier[name] = sorted({c for cls in classes for c in cls.split() if not c.startswith("gl-level-")})

    assert non_tier == dict.fromkeys(non_tier, []), (
        f"a scalar value cell carries a non-tier class -- the five grids disagree: {non_tier!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_load_renders_the_three_averages_and_the_core_count():
    """TUI reference (load/render_curses_v5.py docstring): a header carrying
    LOAD and the core count, then three rows labelled from the schema.

    `cpucore` is `internal: true` -- it is the header's suffix, never a row
    of its own, so this asserts the label "cpucore" is absent.
    """
    payload = _run_render_probe("load")
    text = payload["pluginText"].get("load", "")

    for expected in ("LOAD", "4core", "1 min", "0.86", "5 min", "0.72", "15 min", "0.80"):
        assert expected in text, f"expected {expected!r} in the LOAD plugin text, got {text!r}"
    assert "cpucore" not in text, f"cpucore is internal and must not be a row: {text!r}"


@pytest.mark.parametrize(
    ("scenario", "name", "expected"),
    [
        pytest.param(
            "mem-with-available",
            "mem",
            [
                [["MEM", "53.2%"], ["total", "16.0G"], ["avail", "8.0G"], ["free", "2.0G"]],
                [["active", "5.0G"], ["inacti", "4.0G"], ["buffer", "100.0M"], ["cached", "3.0G"]],
            ],
            id="mem",
        ),
        pytest.param(
            "load",
            "load",
            [[["LOAD", "4core"], ["1 min", "0.86"], ["5 min", "0.72"], ["15 min", "0.80"]]],
            id="load",
        ),
        pytest.param(
            "memswap",
            "memswap",
            [[["SWAP", "25.0%"], ["total", "16.0G"], ["sin", "100.0K/s"], ["sout", "0B/s"]]],
            id="memswap",
        ),
        pytest.param(
            "cpu",
            "cpu",
            [
                [["CPU", "4.5%"], ["user", "3.8%"], ["system", "0.7%"], ["iowait", "0.0%"]],
                [["idle", "95.5%"], ["irq", "0.0%"], ["nice", "0.0%"], ["steal", "0.0%"]],
                [["ctx_sw", "6.7K"], ["inter", "3.0K"], ["sw_int", "1.8K"], ["guest", "0.0%"]],
            ],
            id="cpu",
        ),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_scalar_title_is_the_first_pair_of_its_first_column(scenario, name, expected):
    """TUI reference layouts (mem/memswap/load/cpu render_curses_v5.py
    docstrings): line 1 carries the title AND its value as the first
    (label, value) pair of column 1 -- `SWAP 25.0%`, `CPU 4.5% | idle 95.5% |
    ctx_sw 6.7K`. So the title value shares the right-aligned value column,
    and every column has the same four lines.

    A title row rendered ABOVE the grid puts the value next to the title
    instead of in the value column, and shifts `active`/`idle`/`ctx_sw` one
    line below the title in mem and cpu. `pluginGrid` is every <dl> of the
    plugin as (dt, dd) text pairs, so this observes both the pairing and the
    per-column line count.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginGrid"].get(name) == expected, (
        f"{name}: expected the TUI grid {expected!r}, got {payload['pluginGrid'].get(name)!r}"
    )


@pytest.mark.parametrize(
    ("scenario", "name", "expected"),
    [
        pytest.param("memswap", "memswap", ["gl-col-rate"], id="memswap"),
        pytest.param("mem-with-available", "mem", ["", ""], id="mem"),
        pytest.param("load", "load", [""], id="load"),
        pytest.param("cpu", "cpu", ["", "", ""], id="cpu"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_only_a_column_of_rates_takes_the_wider_floor(scenario, name, expected):
    """Every scalar value column has a 7ch floor so a block keeps its width as
    values change (css/v5.css). Only a column holding formatRate() values --
    memswap's sin/sout, up to "1023.9G/s" -- needs 9ch, via `gl-col-rate`. A
    rate column without it would still resize as the rate grows.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginGridClasses"].get(name) == expected, (
        f"{name}: expected column classes {expected!r}, got {payload['pluginGridClasses'].get(name)!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_loaded_scalar_plugin_still_names_itself_for_assistive_technology():
    """Once loaded, a scalar plugin's title is a <dt> -- a heading is not
    allowed inside <dt> -- so the <article> carries an aria-label, or a screen
    reader navigating by landmark/heading loses mem, swap, load and cpu.
    `scalar-grids` renders all four loaded. `data-plugin` is asserted in the
    same breath: a template comment placed before the root <article> would
    make a second root node and silently drop both fallthrough attributes.
    """
    payload = _run_render_probe("scalar-grids")
    for name in ("mem", "memswap", "load", "cpu"):
        attrs = payload["pluginAttrs"].get(name) or []
        assert "aria-label" in attrs, f"{name}: the loaded article names itself: {attrs!r}"
        assert "data-plugin" in attrs, f"{name}: data-plugin still lands on the root: {attrs!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_scalar_plugin_keeps_its_title_while_loading():
    """The title moves into the grid only once a payload exists; before that
    (cycle 0) the plugin must still say what it is, not show a bare
    "loading…". Checked on the `default` scenario, which publishes nothing.
    """
    payload = _run_render_probe("default")
    for name, title in (("mem", "MEM"), ("load", "LOAD"), ("memswap", "SWAP"), ("cpu", "CPU")):
        text = payload["pluginText"].get(name, "")
        assert text.startswith(title) and "loading" in text, f"{name}: expected {title} then loading, got {text!r}"
        assert name not in payload["pluginGrid"], f"{name}: no grid before the first payload"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_prominent_alert_badges_its_level_word_only():
    """TUI parity (curses_renderer_v5.py alert grid): a prominent incident
    paints the badge on its LEVEL cell only. Now that `gl-prominent` fills
    the tier colour as a background, putting it on the whole footer <li>
    would turn every prominent alert into a full-width coloured band.

    Every alert in the probe fixture is critical AND prominent, so the line
    keeps the tier text colour without the badge, and the level word alone
    carries both classes.
    """
    payload = _run_render_probe("default")
    alerts = payload["footerAlerts"]
    assert len(alerts) == 10, f"vacuous: expected the ten most recent alerts, got {alerts!r}"
    for alert in alerts:
        item_classes = alert["className"].split()
        assert "gl-level-critical" in item_classes and "gl-prominent" not in item_classes, (
            f"the line keeps the tier colour but never the badge: {alert!r}"
        )
        assert alert["level"] == "critical", f"the level word renders on its own: {alert!r}"
        assert set((alert["levelClass"] or "").split()) == {"gl-level-critical", "gl-prominent"}, (
            f"the level word carries the badge: {alert!r}"
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_rate_columns_are_marked_numeric():
    """The two rate columns must carry `.gl-num`, the interface one must not.

    `.gl-num` right-aligns, fixes the digit width and floors the column at
    9ch -- the width `formatRate()` can never exceed -- so a rate going from
    "1.2K/s" to "10.2M/s" between two ticks stops resizing the column. This
    observes the rendered <th> class lists, so it fails if the `numeric` flag
    is dropped from the descriptor or the binding stops reaching the header.
    """
    payload = _run_render_probe("network")
    classes = payload["pluginColumnClasses"].get("network")

    assert classes is not None, "no NETWORK column classes rendered"
    assert "gl-num" not in classes[0], f"the interface column must not be numeric, got {classes[0]!r}"
    for i in (1, 2):
        assert "gl-num" in classes[i], f"expected the rate column {i} to carry gl-num, got {classes[i]!r}"


def _tier_classes(class_name):
    return {c for c in (class_name or "").split() if c.startswith("gl-level-") or c == "gl-prominent"}


@pytest.mark.parametrize(
    ("scenario", "name", "cell_index", "expected"),
    [
        # Columns: interface, Rx/s, Tx/s -> cell 1 is eth0's Rx.
        pytest.param("network-prominent", "network", 1, {"gl-level-warning", "gl-prominent"}, id="network"),
        # Columns: name, proc, mem -> cell 1 is card 0's proc.
        pytest.param("gpu-multi-levels", "gpu", 1, {"gl-level-critical"}, id="gpu"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_table_value_carries_its_tier_on_the_text_not_the_cell(scenario, name, cell_index, expected):
    """A prominent badge paints the tier colour as a BACKGROUND. On a <td>
    that background fills the whole cell -- including `.gl-num`'s 9ch floor
    and the padding -- so a short value like "0%" sat on a wide coloured
    block (maintainer smoke test). The tier classes therefore go on a <span>
    around the formatted value, like the TUI badge that covers the cell text;
    the <td> keeps only its layout class.
    """
    payload = _run_render_probe(scenario)
    cell = payload["pluginTableCells"][name][cell_index]
    assert _tier_classes(cell["value"]) == expected, f"the value span carries the tier: {cell!r}"
    assert _tier_classes(cell["cell"]) == set(), f"the <td> itself carries no tier class: {cell!r}"
    assert "gl-num" in cell["cell"].split(), f"the <td> keeps its numeric layout class: {cell!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_memswap_renders_total_and_the_paging_rates():
    """TUI reference (memswap/render_curses_v5.py docstring): SWAP + percent,
    then total, sin, sout.

    `used` and `free` are deliberately absent: v5 trades that redundant pair
    (they are derivable from total and percent) for the live paging rates.
    Asserting their VALUES are absent, not just their labels, is what makes
    this a parity test rather than a spelling test.

    Note on "0B/s" rather than the docstring's illustrative "0.0K/s": the
    real formatter (`format_bytespers`/`formatRate`, both base-1024
    "K/M/G" scaling) never promotes a zero value to "K" -- `sout=0` reads
    as "0B/s" on both the TUI and the WebUI. Confirmed against
    `glances.outputs.curses_formatters_v5.format_bytespers(0.0)`, which
    also returns "0B/s"; the docstring's "0.0K/s" is not literal.
    """
    payload = _run_render_probe("memswap")
    text = payload["pluginText"].get("memswap", "")

    for expected in ("SWAP", "25.0%", "total", "16.0G", "sin", "100.0K/s", "sout", "0B/s"):
        assert expected in text, f"expected {expected!r} in the SWAP plugin text, got {text!r}"
    assert "4.0G" not in text, f"`used` must not be rendered: {text!r}"
    assert "12.0G" not in text, f"`free` must not be rendered: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_memswap_shows_a_dash_for_rates_before_the_second_cycle():
    """`sin`/`sout` are rate fields: null until a baseline exists, and PRESENT
    in the payload while null. The component must render "-" for them and
    still render everything else.
    """
    payload = _run_render_probe("memswap-no-rates")
    text = payload["pluginText"].get("memswap", "")

    assert "16.0G" in text, f"total must still render: {text!r}"
    assert "-" in text, f"expected the missing marker for the null rates: {text!r}"
    assert "K/s" not in text, f"no rate should be formatted when both are null: {text!r}"


# ------------------------------------------------------- cpu TUI parity (G9-4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_renders_the_linux_three_column_grid():
    """TUI reference (cpu/render_curses_v5.py docstring, lines 17-21)."""
    payload = _run_render_probe("cpu")
    text = payload["pluginText"].get("cpu", "")

    for expected in (
        "CPU",
        "4.5%",
        "idle",
        "95.5%",
        "ctx_sw",
        "6.7K",
        "user",
        "3.8%",
        "inter",
        "3.0K",
        "system",
        "0.7%",
        "sw_int",
        "1.8K",
        "iowait",
        "steal",
        "guest",
    ):
        assert expected in text, f"expected {expected!r} in the CPU plugin text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_title_row_carries_only_the_total_not_idle_or_ctx_sw():
    """Task 6b: `idle` and `ctx_sw` move out of the title row -- `idle` becomes
    the first row of column 2, `ctx_sw` the first row of column 3.

    The substring checks in `test_cpu_renders_the_linux_three_column_grid`
    cannot tell this layout apart from Task 6's (title row carrying `idle`/
    `ctx_sw` beside `CPU 4.5%`): every string it looks for is present either
    way, since `pluginText` concatenates the whole article regardless of
    where each pair sits.

    `textContent` concatenates in DOM order, and the three columns are three
    sequential <dl> elements after the title. So `user` (column 1's first
    row) must appear in the text BEFORE `idle` (column 2's first row) in the
    new layout. In Task 6's layout `idle` sits in the title row, ahead of
    the grid entirely, so it appears BEFORE `user` -- this assertion fails
    against that layout, which is the RED step for this task.
    """
    payload = _run_render_probe("cpu")
    text = payload["pluginText"].get("cpu", "")

    assert "user" in text and "idle" in text, f"expected both `user` and `idle` in the CPU text: {text!r}"
    assert text.index("user") < text.index("idle"), (
        f"expected `user` (column 1) before `idle` (column 2's first row): {text!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_switches_column_one_and_column_three_on_payload_content():
    """The TUI branches on payload CONTENT, never on the OS, so the WebUI can
    reproduce it exactly (cpu/render_curses_v5.py:181-200).

    This fixture has no `user` key (column 1 becomes idle/cpucore/dpc), a
    null-but-present `soft_interrupts` (column 3 falls back to ctx_switches),
    and no `guest` key (column 3's last row falls back to syscalls). It fails
    if the two kinds of check -- key presence vs value -- are collapsed into
    one.
    """
    payload = _run_render_probe("cpu-idle-tag")
    text = payload["pluginText"].get("cpu", "")

    assert "dpc" in text, f"the idle-tag branch must show dpc: {text!r}"
    assert "user" not in text, f"no `user` key, so no user row: {text!r}"
    assert "sw_int" not in text, f"soft_interrupts is null -> ctx_switches instead: {text!r}"
    assert "syscalls" in text, f"no `guest` key -> syscalls instead: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_leaves_column_three_short_when_neither_guest_nor_syscalls():
    """Column 3's last row carries neither `guest` nor `syscalls`.

    `pluginText` cannot distinguish an emitted empty label/value pair from an
    absent one -- the three `<dl>` are independent grids -- so what is asserted
    is the absence of both labels while the rest of column 3 still renders.
    """
    payload = _run_render_probe("cpu-no-third-row")
    text = payload["pluginText"].get("cpu", "")

    assert "guest" not in text, f"no guest key: {text!r}"
    assert "syscalls" not in text, f"syscalls is null: {text!r}"
    assert "sw_int" in text, f"the rest of column 3 must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_drops_ctx_switches_when_it_has_no_rate_yet():
    """`ctx_switches` opens column 3 only when it has a value.

    It is a `rate` field, so it is null-but-present on the first cycle -- the
    real production state, not an edge case. `soft_interrupts` is populated
    here, so the column-3 fallback does not bring `ctx_sw` back either and it
    must not appear anywhere in the block.
    """
    payload = _run_render_probe("cpu-ctx-switches-null")
    text = payload["pluginText"].get("cpu", "")

    assert "ctx_sw" not in text, f"a null ctx_switches must render nowhere: {text!r}"
    assert "inter" in text, f"the rest of column 3 must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_keeps_a_null_guest_ahead_of_a_populated_syscalls():
    """`guest` is chosen on KEY PRESENCE, `syscalls` on VALUE
    (cpu/render_curses_v5.py:196-199).

    A `guest` that is present but null therefore still wins the last row --
    shown as the missing marker -- and `syscalls` must not appear even though
    it carries a value. Every other cpu fixture passes with the two checks
    collapsed into one; this is the one that does not.
    """
    payload = _run_render_probe("cpu-guest-null")
    text = payload["pluginText"].get("cpu", "")

    assert "guest-" in text, f"a null guest must still render, as the missing marker: {text!r}"
    assert "syscalls" not in text, f"`guest` is present as a key, so syscalls must not render: {text!r}"


# ------------------------------------------------------- gpu TUI parity (G9-4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_one_card_renders_the_summary_block():
    """TUI reference (gpu/render_curses_v5.py docstring, lines 13-16): a single
    card renders the summary block -- its name as the title, then proc, mem and
    temperature, one row each.
    """
    payload = _run_render_probe("gpu-one-card")
    text = payload["pluginText"].get("gpu", "")

    assert "GeForce RTX 3080" in text, f"the title is the card's name: {text!r}"
    for expected in ("proc:", "30%", "mem:", "40%", "temperature:", "55C"):
        assert expected in text, f"expected {expected!r} in the GPU plugin text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_several_cards_render_one_row_each_without_temperature():
    """v4 quirk reproduced on purpose: multi mode shows name + proc + mem, and
    NO temperature -- unlike summary mode, which shows all three.
    """
    payload = _run_render_probe("gpu-three-cards")
    text = payload["pluginText"].get("gpu", "")

    assert "3 GeForce RTX 3080" in text, f"title counts the cards: {text!r}"
    for expected in ("30%", "45%", "12%"):
        assert expected in text, f"expected every card's proc: {text!r}"
    assert "55C" not in text, f"multi mode shows no temperature: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_meangpu_forces_the_summary_and_the_mean_labels():
    """`--meangpu` reaches the WebUI through /api/5/args (design spec §5).

    Same three cards as `gpu-three-cards`, which renders the per-card table:
    the ONLY difference is the args fixture, so the switch to the summary
    block and to the "mean" labels can only come from the flag.
    """
    payload = _run_render_probe("gpu-three-cards-mean")
    text = payload["pluginText"].get("gpu", "")

    assert "proc mean:" in text, f"meangpu switches the labels: {text!r}"
    assert "29%" in text, f"the mean of 30/45/12 rounds to 29: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_drops_the_memory_column_only_when_no_card_reports_it():
    """#3631: an unavailable sensor on ONE card shows N/A rather than being
    hidden, because hiding it per card misaligns heterogeneous rows. The
    column disappears only when no card reports memory at all.
    """
    payload = _run_render_probe("gpu-no-memory")
    text = payload["pluginText"].get("gpu", "")

    # `N/A` is what an undropped memory cell renders for a null value
    # (`gpuValue`), so its absence observes the dropped CELLS directly rather
    # than the absence of a label -- which would also hold for a component
    # that never labels the column at all.
    assert "N/A" not in text, f"no card reports memory -> no mem cells at all: {text!r}"
    assert "30%" in text and "45%" in text, f"proc must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_keeps_the_memory_cell_of_a_card_that_reports_nothing():
    """The other half of #3631, and the half the spec section 8.4 actually
    argues for: a card reporting no memory still shows `N/A`, because hiding
    the cell per card drops a cell and misaligns heterogeneous rows.

    `gpu-no-memory` (every card null) cannot observe this -- a component that
    hid the cell per card passes it. This fixture has card 0 at 40% and card 1
    at null, so only the column-level rule renders an "N/A".
    """
    payload = _run_render_probe("gpu-mixed-memory")
    text = payload["pluginText"].get("gpu", "")

    assert "40%" in text, f"the reporting card's memory must render: {text!r}"
    assert "N/A" in text, f"the non-reporting card keeps its cell as N/A: {text!r}"
    assert "30%" in text and "45%" in text, f"both cards' proc must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_with_no_card_renders_nothing_beyond_its_title():
    """Design spec section 11: a machine with no GPU (or with every backend
    failing) publishes an empty `data` list, and the plugin then renders its
    title and nothing else -- no empty table, no "loading…" (the payload
    arrived, it is just empty).
    """
    payload = _run_render_probe("gpu-zero-cards")

    assert payload["pluginText"].get("gpu") == "GPU", (
        f"expected the bare fallback title, got {payload['pluginText'].get('gpu')!r}"
    )
    assert "gpu" not in payload["pluginValueClasses"], (
        f"no card -> no value cell: {payload['pluginValueClasses'].get('gpu')!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_honours_fahrenheit():
    """`--fahrenheit` also arrives through /api/5/args. Same single card as
    `gpu-one-card`, which renders 55C: only the args fixture differs.
    """
    payload = _run_render_probe("gpu-one-card-fahrenheit")
    text = payload["pluginText"].get("gpu", "")

    assert "131F" in text, f"55C is 131F: {text!r}"
    assert "55C" not in text, f"Celsius must not also render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_summary_colours_from_the_first_card_not_from_the_mean():
    """v4 quirk reproduced on purpose (gpu/render_curses_v5.py:69, 80): summary
    mode averages ACROSS the cards but passes `first_id` to `_level_role()`,
    i.e. it colours from the FIRST card's `_levels`.

    The fixture carries the same three cards as `gpu-three-cards` with card 0
    critical on `proc` and cards 1 and 2 ok, and `--meangpu` to force the
    summary. Two thirds of the tiers are ok, so a colour derived from the mean
    -- or from any card but the first -- cannot come out critical: the
    assertion distinguishes the quirk from the "fix".

    The tier reaches the DOM only as a `gl-level-*` class, never as text,
    which is why this reads `pluginValueClasses` rather than `pluginText`.
    """
    payload = _run_render_probe("gpu-first-card-colour")
    classes = payload["pluginValueClasses"].get("gpu")

    assert classes, "no GPU value cells rendered"
    # Summary order is proc, mem, temperature -- proc is the first <dd>.
    assert "gl-level-critical" in classes[0], f"the proc cell must take card 0's critical tier, got {classes[0]!r}"


# ------------------------------------------------------- header plugins (G9-5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_blocks_are_hidden_while_their_plugin_has_not_published():
    """The `default` scenario publishes nothing. The TUI renders `[]` for an
    empty payload, so the header blocks are hidden -- not "loading…", which
    would fill the banner with placeholders.

    `mem` is asserted NOT hidden in the same run: without that, a probe that
    reported every element as hidden would pass this test.
    """
    payload = _run_render_probe("default")
    hidden = payload["pluginHidden"]
    for name in ("system", "ip", "uptime", "cloud", "now"):
        assert hidden.get(name) is True, f"{name} must be hidden before it publishes: {hidden!r}"
    assert hidden.get("mem") is False, f"vacuous: a panel plugin is never hidden: {hidden!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_system_renders_the_hostname_and_the_os_name():
    """system/render_curses_v5.py: `hostname` then `hr_name`."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("system", "")
    assert payload["pluginHidden"].get("system") is False
    assert "test-host" in text, f"got {text!r}"
    assert "Ubuntu 26.04 64bit / Linux 7.0.0-31-generic" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_system_without_a_hostname_is_hidden():
    payload = _run_render_probe("system-no-hostname")
    assert payload["pluginHidden"].get("system") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_uptime_renders_in_the_tui_format():
    """uptime/render_curses_v5.py: `Uptime:` then format_seconds(seconds)."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("uptime", "")
    assert "Uptime:" in text and "3d04h" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_now_renders_the_custom_date():
    """now/render_curses_v5.py: the `custom` string only; `iso` is REST-only."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("now", "")
    assert text == "2026-09-11 10:20:30 CEST", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_plugins_sit_in_the_header_zone():
    payload = _run_render_probe("header")
    assert payload["slots"].get("header-left") == ["system", "ip"], f"got {payload['slots']!r}"
    assert payload["slots"].get("header-right") == ["uptime", "cloud", "now"], f"got {payload['slots']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_renders_the_private_and_public_addresses():
    """ip/render_curses_v5.py: `IP addr/cidr`, then `Pub addr` and the
    geolocation string."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("ip", "")
    for expected in ("IP", "192.168.1.10/24", "Pub", "203.0.113.42", "Paris, France (AS64496 Example Net)"):
        assert expected in text, f"expected {expected!r} in the ip text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_without_a_cidr_shows_the_bare_address():
    """`mask_cidr is not None` gates the suffix (ip/render_curses_v5.py:53)."""
    payload = _run_render_probe("ip-no-cidr")
    text = payload["pluginText"].get("ip", "")
    assert "192.168.1.10" in text, f"got {text!r}"
    assert "192.168.1.10/" not in text, f"no cidr -> no slash: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_masks_the_public_address_with_hide_public_info():
    """`--hide-public-info` reaches the WebUI through /api/5/args. Same payload
    as `header`; only the args fixture differs.

    Display-only, like the TUI: the API still serves the address in clear
    (G9-5 spec §11). This test proves the rendered text, nothing more.
    """
    payload = _run_render_probe("header-hide-public")
    text = payload["pluginText"].get("ip", "")
    assert "203.0.*.*" in text, f"got {text!r}"
    assert "113.42" not in text, f"the masked octets must not render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_with_no_address_is_hidden():
    payload = _run_render_probe("ip-no-address")
    assert payload["pluginHidden"].get("ip") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_renders_the_platform_and_the_instance_summary():
    """cloud/render_curses_v5.py docstring: `OpenStack gold instance my-vm (eu-west-1a)`."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("cloud", "")
    assert "OpenStack" in text, f"got {text!r}"
    assert "gold instance my-vm (eu-west-1a)" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_without_a_name_is_hidden():
    """#2485: platform and name are both mandatory, or nothing renders."""
    payload = _run_render_probe("cloud-no-name")
    assert payload["pluginHidden"].get("cloud") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_fills_a_missing_part_with_unknown():
    payload = _run_render_probe("cloud-no-region")
    text = payload["pluginText"].get("cloud", "")
    assert "gold instance my-vm (Unknown)" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_disabled_on_the_server_is_not_rendered():
    """The shipped default. Before G9-5 this block would have sat in the header
    as a permanent loading state for most users."""
    payload = _run_render_probe("cloud-disabled")
    assert "cloud" not in payload["pluginNames"], f"got {payload['pluginNames']!r}"
    assert "system" in payload["pluginNames"], f"vacuous: the header still renders: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_blocks_show_their_error_when_all_fails():
    """Spec §9: "`/api/5/all` fails -> every visible block shows its error,
    header included." `fetchAll()` (api.js) turns the failed fetch into
    `api/5/all: HTTP 500` for every requested plugin, and each header
    component's root is `v-show="error || <guard>"` -- the `error ||` term is
    what keeps the block visible although its guard field never arrived."""
    payload = _run_render_probe("all-unreachable")
    for name in ("system", "ip", "uptime", "cloud", "now"):
        assert payload["pluginHidden"].get(name) is False, (
            f"{name} must show its error, not hide: {payload['pluginHidden']!r}"
        )
        text = payload["pluginText"].get(name, "")
        assert "HTTP 500" in text, f"{name}: expected the HTTP 500 error text, got {text!r}"
