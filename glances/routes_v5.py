#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 REST API routes (Phase 1.6).

Mounted under ``/api/5`` by ``glances.webserver_v5.build_app``. All routes
read from objects exposed on ``app.state`` — they hold no state of their
own. The handlers are intentionally tiny: any meaningful work belongs in
the plugin / store / alerts / security modules.

Route inventory:

| Path                          | Method | Source                       |
|-------------------------------|--------|------------------------------|
| ``/api/5/token``              | POST   | Basic → ``JWTHandler``       |
| ``/api/5/pluginslist``        | GET    | ``app.state.plugins`` keys   |
| ``/api/5/all``                | GET    | per-plugin ``get_api_payload()`` |
| ``/api/5/all/limits``         | GET    | per-plugin ``get_limits()``  |
| ``/api/5/alert``              | GET    | ``alerts.get_history()``     |
| ``/api/5/config``             | GET    | ``config.as_dict_secure()``  |
| ``/api/5/args``               | GET    | ``app.state.args``, redacted |
| ``/api/5/<plugin>``           | GET    | ``plugin.get_api_payload()`` (``_levels`` included) |
| ``/api/5/<plugin>/info``      | GET    | ``plugin.fields_description``|
| ``/api/5/<plugin>/limits``    | GET    | ``plugin.get_limits()``      |

A plugin that has registered but has not yet produced stats (scheduler
cycle 0) returns ``200 null`` — not an error, just a transient. Clients
poll. Plugins not in the registry → ``404``.

Architecture references:
- §4    REST API server — FastAPI
- §3.4  GlancesAlerts (history feed)
- §8    CVE-2026-32609 / 30928 — ``as_dict_secure()`` for ``/config``
"""

from __future__ import annotations

import hmac
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from glances.config_v5 import GlancesConfigV5
from glances.security_v5 import verify_password

if TYPE_CHECKING:
    import argparse

logger = logging.getLogger(__name__)

# Static path segments that the dynamic ``/{plugin_name}`` handler must not
# capture. FastAPI matches routes in declaration order, so listing static
# routes first is enough, but this set documents the reservation explicitly
# and guards against rename mistakes in test fixtures.
_RESERVED_NAMES: frozenset[str] = frozenset({"token", "pluginslist", "all", "alert", "config", "args"})

# Argument names that are sensitive beyond what GlancesConfigV5._secure_value()
# catches. `config_path` is a filesystem path: it discloses the local username
# and the directory layout, which the config CONTENTS served by /api/5/config
# do not. v4 redacts its equivalent (`conf_file`) the same way.
_SENSITIVE_ARGS: frozenset[str] = frozenset({"config_path"})

# ``HTTPBasic(auto_error=False)`` lets us emit our own 401 with the correct
# ``WWW-Authenticate`` header. ``auto_error=True`` short-circuits before the
# username comparison and produces a generic 403 — we want consistent 401s.
_basic_security = HTTPBasic(auto_error=False)


def build_router() -> APIRouter:
    """Return an ``APIRouter`` carrying the v5 REST routes.

    ``build_app()`` mounts this router under ``/api/5``. Splitting the
    router into its own factory keeps the routes testable in isolation and
    keeps ``webserver_v5.py`` focused on middlewares.
    """
    router = APIRouter(prefix="/api/5", tags=["v5"])

    @router.post("/token", tags=["auth"])
    async def issue_token(
        request: Request,
        credentials: HTTPBasicCredentials | None = Depends(_basic_security),
    ):
        config = request.app.state.config
        jwt_handler = request.app.state.jwt_handler
        password_hash = config.get("outputs", "password", "")

        # Auth is not configured at all → no token to mint. Mirrors v4
        # behaviour: returning 404 rather than 501/503 keeps the response
        # surface uniform with "missing resource".
        if not password_hash or jwt_handler is None:
            raise HTTPException(status_code=404, detail="JWT auth not configured")

        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": 'Basic realm="Glances"'},
            )

        expected_user = config.get("outputs", "username", "glances")
        if not hmac.compare_digest(credentials.username, expected_user) or not verify_password(
            credentials.password, password_hash
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": 'Basic realm="Glances"'},
            )

        token = jwt_handler.create_access_token(credentials.username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": jwt_handler.expire_minutes * 60,
        }

    @router.get("/pluginslist")
    async def plugins_list(request: Request) -> list[str]:
        plugins = _plugins(request)
        return sorted(plugins.keys())

    @router.get("/all")
    async def all_stats(request: Request) -> dict[str, Any]:
        # Registry read, not a store read: `/all` must apply each plugin's
        # export filter (issue #3211), which only the plugin can do.
        # Empty payloads are SKIPPED, preserving the existing contract that a
        # registered-but-never-updated plugin is absent from `/all` rather
        # than present with an empty body.
        out: dict[str, Any] = {}
        for name, plugin in _plugins(request).items():
            payload = plugin.get_api_payload()
            if payload:
                out[name] = payload
        return out

    @router.get("/all/limits")
    async def all_limits(request: Request) -> dict[str, Any]:
        # Declared BEFORE /{plugin_name}/limits: FastAPI matches in
        # declaration order, so the dynamic route would otherwise swallow
        # `all` as a plugin name. _RESERVED_NAMES is the belt, this is the
        # braces.
        out: dict[str, Any] = {}
        for name, plugin in _plugins(request).items():
            limits = plugin.get_limits()
            if limits:
                out[name] = limits
        return out

    @router.get("/alert")
    async def alert_history(request: Request) -> list[dict[str, Any]]:
        alerts = request.app.state.alerts
        if alerts is None:
            raise HTTPException(status_code=404, detail="Alerts subsystem disabled")
        return alerts.get_history()

    @router.get("/config")
    async def config_dump(request: Request) -> dict[str, Any]:
        return request.app.state.config.as_dict_secure()

    @router.get("/args")
    async def args_dump(request: Request) -> dict[str, Any]:
        """Return the CLI argument namespace, redacted (issue #1527 / CVE-2026-68520)."""
        return _redact_args(getattr(request.app.state, "args", None))

    @router.get("/{plugin_name}/info")
    async def plugin_info(plugin_name: str, request: Request) -> dict[str, Any]:
        plugin = _resolve_plugin(request, plugin_name)
        return plugin.fields_description

    @router.get("/{plugin_name}/limits")
    async def plugin_limits(plugin_name: str, request: Request) -> dict[str, Any]:
        plugin = _resolve_plugin(request, plugin_name)
        return plugin.get_limits()

    @router.get("/{plugin_name}")
    async def plugin_payload(plugin_name: str, request: Request):
        plugins = _plugins(request)
        if plugin_name not in plugins:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name!r} not found")
        # Plugin is registered but may not have published a payload yet
        # (scheduler cycle 0). Return a bare JSON ``null`` so clients can
        # distinguish "unknown plugin" (404) from "data not yet available"
        # without surfacing a transient as an error.
        # get_api_payload() returns {} where the store returned None, so the
        # cycle-0 guard tests emptiness. The `null` body is unchanged.
        payload = plugins[plugin_name].get_api_payload()
        if not payload:
            return JSONResponse(content=None)
        return payload

    return router


# --------------------------------------------------------------- helpers


def _plugins(request: Request) -> dict[str, Any]:
    plugins = getattr(request.app.state, "plugins", None)
    if not isinstance(plugins, dict):
        return {}
    return plugins


def _redact_args(args: argparse.Namespace | None) -> dict[str, Any]:
    """Return the CLI argument namespace with sensitive values redacted.

    Module-level rather than a closure inside `build_router()`: that factory
    was already at ruff's complexity ceiling, so every route added inside it
    pushes it over.

    Redaction is UNCONDITIONAL, matching `/api/5/config` above: v5 applies
    no auth branch there either.

    `config_path` is redacted (see `_SENSITIVE_ARGS`) even though `/config`
    already serves the merged configuration's *contents* to unauthenticated
    callers: the file *path* discloses the local username and directory
    layout, which the contents do not. v4 redacts its equivalent
    (`conf_file`) for the same reason.

    `_secure_value()` is reused rather than reimplemented: CVE-2026-68520
    was a value-level bypass (a credential inside a URL), and a second
    redactor is a second place to get it wrong.
    """
    if args is None:
        return {}
    secure = GlancesConfigV5._secure_value
    return {
        key: GlancesConfigV5.SECRET_REDACTED if key in _SENSITIVE_ARGS else secure(key, value)
        for key, value in vars(args).items()
    }


def _resolve_plugin(request: Request, plugin_name: str):
    plugins = _plugins(request)
    if plugin_name in _RESERVED_NAMES:
        # Defensive: FastAPI route matching already excludes these, but
        # raise explicitly if a test ever subclasses the router.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plugin {plugin_name!r} not found")
    plugin = plugins.get(plugin_name)
    if plugin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plugin {plugin_name!r} not found")
    return plugin
