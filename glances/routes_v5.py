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
| ``/api/5/all``                | GET    | ``store.as_dict()``          |
| ``/api/5/alert``              | GET    | ``alerts.get_history()``     |
| ``/api/5/config``             | GET    | ``config.as_dict_secure()``  |
| ``/api/5/<plugin>``           | GET    | ``store.get(plugin)`` (``_levels`` included) |
| ``/api/5/<plugin>/info``      | GET    | ``plugin.fields_description``|

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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from glances.security_v5 import verify_password

logger = logging.getLogger(__name__)

# Static path segments that the dynamic ``/{plugin_name}`` handler must not
# capture. FastAPI matches routes in declaration order, so listing static
# routes first is enough, but this set documents the reservation explicitly
# and guards against rename mistakes in test fixtures.
_RESERVED_NAMES: frozenset[str] = frozenset({"token", "pluginslist", "all", "alert", "config"})

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
        return request.app.state.store.as_dict()

    @router.get("/alert")
    async def alert_history(request: Request) -> list[dict[str, Any]]:
        alerts = request.app.state.alerts
        if alerts is None:
            raise HTTPException(status_code=404, detail="Alerts subsystem disabled")
        return alerts.get_history()

    @router.get("/config")
    async def config_dump(request: Request) -> dict[str, Any]:
        return request.app.state.config.as_dict_secure()

    @router.get("/{plugin_name}/info")
    async def plugin_info(plugin_name: str, request: Request) -> dict[str, Any]:
        plugin = _resolve_plugin(request, plugin_name)
        return plugin.fields_description

    @router.get("/{plugin_name}")
    async def plugin_payload(plugin_name: str, request: Request):
        plugins = _plugins(request)
        if plugin_name not in plugins:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name!r} not found")
        # Plugin is registered but may not have published a payload yet
        # (scheduler cycle 0). Return a bare JSON ``null`` so clients can
        # distinguish "unknown plugin" (404) from "data not yet available"
        # without surfacing a transient as an error.
        payload = request.app.state.store.get(plugin_name)
        if payload is None:
            return JSONResponse(content=None)
        return payload

    return router


# --------------------------------------------------------------- helpers


def _plugins(request: Request) -> dict[str, Any]:
    plugins = getattr(request.app.state, "plugins", None)
    if not isinstance(plugins, dict):
        return {}
    return plugins


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
