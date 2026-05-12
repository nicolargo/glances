#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 FastAPI app skeleton.

Phase 1.5 deliverable. Builds the FastAPI app, wires the security
middlewares (TrustedHost / CORS / Auth), and exposes the liveness probes
``/status`` and ``/healthz``. Concrete REST routes (``/api/5/<plugin>``,
``/api/5/alert``, ``/api/5/token``) land in Phase 1.6 and read from
``app.state``.

Architecture references:
- §4   REST API server — FastAPI
- §8   Security advisories (CVE-2026-32596, 32610, 32632, 34839)

Middleware composition (from outer to inner):

    TrustedHostMiddleware   ← DNS rebinding (CVE-2026-32632)
        ↓
    CORSMiddleware          ← Cross-origin policy (CVE-2026-32610 / 34839)
        ↓
    AuthMiddleware          ← Basic / Bearer (CVE-2026-32596)
        ↓
    route handler / probe

Starlette applies middlewares in reverse registration order, so the code
below registers them inner-first.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import hmac
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.security_v5 import JWTHandler, verify_password
from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)

# Liveness / readiness probes — always exempt from authentication. ``/status``
# matches the v4 endpoint name; ``/healthz`` is the Kubernetes / Prometheus /
# Docker healthcheck convention. Hardcoded — deliberately not configurable
# so the probe surface stays predictable.
UNAUTH_PATHS: frozenset[str] = frozenset({"/status", "/healthz"})

# Loopback addresses that suppress the "no TrustedHost configured" warning.
_LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "::1", "localhost"})

# Default bind address — matches v4 (``--bind 127.0.0.1`` default).
_DEFAULT_BIND_ADDRESS = "127.0.0.1"

# Default Basic-Auth username — matches v4 CLI default.
_DEFAULT_USERNAME = "glances"

# Default JWT token lifetime in minutes — matches v4.
_DEFAULT_JWT_EXPIRE_MINUTES = 60


def build_app(
    *,
    config: GlancesConfigV5,
    store: StatsStoreV5,
    alerts: GlancesAlerts | None = None,
) -> FastAPI:
    """Build the v5 FastAPI app with security middlewares wired in.

    The returned app:
    - exposes ``/status`` and ``/healthz`` (200 OK, no auth)
    - serves Swagger UI at ``/docs`` and ReDoc at ``/redoc`` unless
      ``[outputs] api_doc=false``
    - applies, from outer to inner: TrustedHost → CORS → Auth
    - exposes ``config``, ``store``, ``alerts``, ``jwt_handler`` via
      ``app.state``

    The scheduler is *not* started here — Phase 1.7 wires that into the CLI
    entrypoint. Routes for ``/api/5/<plugin>`` and ``/api/5/alert`` land in
    Phase 1.6.
    """
    api_doc_enabled = config.get("outputs", "api_doc", True)

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(
        title="Glances REST API",
        version="5",
        docs_url="/docs" if api_doc_enabled else None,
        redoc_url="/redoc" if api_doc_enabled else None,
        lifespan=lifespan,
    )
    app.state.config = config
    app.state.store = store
    app.state.alerts = alerts
    app.state.jwt_handler = None  # set by _wire_auth() when password is configured

    # Register from inner to outer — Starlette applies middlewares in reverse.
    _wire_auth(app, config)
    _wire_cors(app, config)
    _wire_trusted_hosts(app, config)

    _register_health_endpoints(app)

    if not _auth_is_configured(config):
        logger.warning(
            "Glances REST API runs unauthenticated (CVE-2026-32596). "
            "Set [outputs] password=<pbkdf2> in glances.conf to enable Basic + Bearer auth."
        )

    return app


# ---------------------------------------------------------- middlewares


def _wire_trusted_hosts(app: FastAPI, config: GlancesConfigV5) -> None:
    """Filter requests by ``Host`` header against an allowlist.

    Default: not wired (matches v4 behaviour). When the bind address is not
    loopback and no allowlist is configured, log a WARNING — this is the
    only signal users see that DNS-rebinding mitigation is off (CVE-2026-32632).
    """
    allowed = _csv_to_list(config.get("outputs", "webui_allowed_hosts", []))
    if not allowed:
        bind = config.get("outputs", "bind_address", _DEFAULT_BIND_ADDRESS)
        if not _is_loopback(bind):
            logger.warning(
                "[outputs] webui_allowed_hosts is not set and bind_address=%s is not loopback. "
                "DNS rebinding mitigation (CVE-2026-32632) is disabled.",
                bind,
            )
        return
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)


def _wire_cors(app: FastAPI, config: GlancesConfigV5) -> None:
    """Wire CORS only when an explicit origin allowlist is configured.

    A wildcard origin combined with credentials is invalid per the CORS
    spec (CVE-2026-32610). When detected, downgrade ``allow_credentials``
    to ``False`` with a WARNING — do not refuse to start.
    """
    origins = _csv_to_list(config.get("outputs", "cors_origins", []))
    allow_credentials = config.get("outputs", "cors_allow_credentials", False)

    if any(o == "*" for o in origins) and allow_credentials:
        logger.warning(
            "[outputs] cors_origins='*' with cors_allow_credentials=True is invalid "
            "per the CORS spec (CVE-2026-32610). Forcing allow_credentials=False."
        )
        allow_credentials = False

    if not origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )


def _wire_auth(app: FastAPI, config: GlancesConfigV5) -> None:
    """Install the Basic + Bearer authentication middleware.

    Matches v4 behaviour: JWT Bearer is *only* enabled when a Basic-Auth
    password is configured — otherwise there is no path to mint a token
    through ``/api/5/token`` (which lands in Phase 1.6).
    """
    password_hash = config.get("outputs", "password", "")
    if not password_hash:
        return  # No auth configured — startup warning is emitted by build_app().

    username = config.get("outputs", "username", _DEFAULT_USERNAME)
    jwt_secret = config.get("outputs", "jwt_secret_key", "") or None
    jwt_expire = config.get("outputs", "jwt_expire_minutes", _DEFAULT_JWT_EXPIRE_MINUTES)
    jwt_handler = JWTHandler(secret_key=jwt_secret, expire_minutes=jwt_expire)
    app.state.jwt_handler = jwt_handler

    if jwt_handler.secret_was_generated:
        logger.info(
            "[outputs] jwt_secret_key not set — generated an ephemeral key. "
            "Tokens become invalid on every restart. Set jwt_secret_key for stable tokens."
        )

    @app.middleware("http")
    async def authenticate(request: Request, call_next):  # noqa: ANN001 — FastAPI middleware signature
        if request.url.path in UNAUTH_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")

        # JWT Bearer takes precedence — checked first so Bearer Authorization
        # headers are never confused with Basic.
        if auth.startswith("Bearer "):
            token = auth[len("Bearer ") :].strip()
            if jwt_handler.verify_token(token) is not None:
                return await call_next(request)
            return _unauth_response(scheme="Bearer")

        if auth.startswith("Basic "):
            credentials = _decode_basic(auth[len("Basic ") :].strip())
            if credentials is not None:
                user, password = credentials
                if hmac.compare_digest(user, username) and verify_password(password, password_hash):
                    return await call_next(request)

        return _unauth_response(scheme="Basic")


def _decode_basic(encoded: str) -> tuple[str, str] | None:
    try:
        raw = base64.b64decode(encoded, validate=True).decode("utf-8", errors="strict")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    if ":" not in raw:
        return None
    user, _, password = raw.partition(":")
    return user, password


def _unauth_response(*, scheme: str) -> JSONResponse:
    headers = {"WWW-Authenticate": 'Basic realm="Glances"' if scheme == "Basic" else "Bearer"}
    return JSONResponse(status_code=401, content={"detail": "Authentication required"}, headers=headers)


# ---------------------------------------------------------- endpoints


def _register_health_endpoints(app: FastAPI) -> None:
    """Register ``/status`` (v4-compat) and ``/healthz`` (k8s-compat) probes.

    Both endpoints return the same payload. They are *defined* on the app
    but listed in ``UNAUTH_PATHS`` so the auth middleware bypasses them.
    """

    async def status_handler():
        return {"status": "ok", "version": "5"}

    app.add_api_route("/status", status_handler, methods=["GET"], tags=["health"])
    app.add_api_route("/healthz", status_handler, methods=["GET"], tags=["health"])


# ---------------------------------------------------------- helpers


def _csv_to_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _is_loopback(addr: str) -> bool:
    return addr in _LOOPBACK_HOSTS


def _auth_is_configured(config: GlancesConfigV5) -> bool:
    return bool(config.get("outputs", "password", ""))
