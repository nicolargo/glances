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

    Each plugin component renders an <article class="gl-plugin"> with an
    <h2> naming it (PluginMem.vue -> "MEM", PluginNetwork.vue ->
    "NETWORK"). Assert both are present, not just "some markup exists":
    a loop that iterates only `PLUGINS[0]` would still produce one
    gl-plugin article and could pass a weaker assertion.
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
    assert payload["pluginHeaders"] == ["MEM", "NETWORK"], (
        f"expected both registered plugins to render, got {payload['pluginHeaders']!r}"
    )


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
    mem_text = payload["pluginText"].get("MEM", "")

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
    mem_text = payload["pluginText"].get("MEM", "")

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
    headers = payload["pluginColumnHeaders"].get("NETWORK")

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
def test_network_rate_columns_are_marked_numeric():
    """The two rate columns must carry `.gl-num`, the interface one must not.

    `.gl-num` right-aligns, fixes the digit width and floors the column at
    9ch -- the width `formatRate()` can never exceed -- so a rate going from
    "1.2K/s" to "10.2M/s" between two ticks stops resizing the column. This
    observes the rendered <th> class lists, so it fails if the `numeric` flag
    is dropped from the descriptor or the binding stops reaching the header.
    """
    payload = _run_render_probe("network")
    classes = payload["pluginColumnClasses"].get("NETWORK")

    assert classes is not None, "no NETWORK column classes rendered"
    assert "gl-num" not in classes[0], f"the interface column must not be numeric, got {classes[0]!r}"
    for i in (1, 2):
        assert "gl-num" in classes[i], f"expected the rate column {i} to carry gl-num, got {classes[i]!r}"
