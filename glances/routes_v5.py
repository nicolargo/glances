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
| ``/api/5/all/info``           | GET    | per-plugin ``fields_description`` |
| ``/api/5/alert``              | GET    | ``alerts.get_history()``     |
| ``/api/5/alert/incidents``    | GET    | ``{is_initializing, incidents}`` envelope (``derive_incidents()``) |
| ``/api/5/config``             | GET    | ``config.as_dict_secure()``  |
| ``/api/5/args``               | GET    | ``app.state.args``, redacted |
| ``/api/5/<plugin>``           | GET    | ``plugin.get_api_payload()`` (``_levels`` included) |
| ``/api/5/<plugin>/info``      | GET    | ``plugin.fields_description``|
| ``/api/5/<plugin>/limits``    | GET    | ``plugin.get_limits()``      |
| ``/api/5/<plugin>/history``   | GET    | ``plugin.get_history()`` (``?nb=&field=&item=``) |

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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.concurrency import run_in_threadpool

from glances.alerts_incidents_v5 import derive_incidents, incident_duration
from glances.config_v5 import GlancesConfigV5
from glances.processes import glances_processes
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


def _register_history_route(router: APIRouter) -> None:
    """`GET /api/5/<plugin>/history` (history design 2026-09-26 §5.5).

    Filters are query parameters, not path segments: an item can be `/home`.
    """

    @router.get("/{plugin_name}/history")
    async def plugin_history(
        plugin_name: str,
        request: Request,
        nb: int = Query(0, ge=0, description="Last nb points (0 = all)."),
        field: str | None = Query(None, description="One historised field."),
        item: str | None = Query(None, description="One item of a collection plugin (raw primary-key value)."),
    ) -> dict[str, Any]:
        plugin = _resolve_plugin(request, plugin_name)
        try:
            return plugin.get_history(nb=nb, field=field, item=item)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc.args[0])) from exc


def _register_extended_process_routes(router: APIRouter) -> None:
    """Register the two pin/unpin routes.

    Their own function, not inlined in ``build_router``: they are the only
    state-changing pair in an otherwise read-only API, and grouping them
    keeps that visible rather than buried among thirteen getters.
    """
    # ----------------------------------------- the pinned process (2.X-b3)
    #
    # Declared BEFORE the `/{plugin_name}` family so nothing about their
    # ordering has to be reasoned about later. `POST`, and state-changing, in
    # an API that is otherwise read-only — the same two routes v4 carries
    # (`glances_restful_api.py:534-537`), reaching the same engine.
    #
    # Security posture, stated rather than left implicit: Glances is
    # unauthenticated by default. What an unauthenticated caller gains here is
    # one pinned process' affinity, ionice, fd count, swap and connection
    # counts — the same nature of information as the process list it can
    # already GET, and exactly v4's exposure. Nothing on the host is modified.
    # Under `[outputs] password` these sit behind the same auth middleware as
    # every other route.
    #
    # The pin is GLOBAL: one pinned process per server, set either from here
    # or by the TUI's `e` key. Extended stats cost a psutil grab per cycle, so
    # that ceiling is a property worth having rather than an accident.

    def _pinnable_pids(request: Request) -> set[int]:
        """PIDs the current process list actually carries.

        Read from the store rather than from `glances_processes` directly:
        the store is what every other route answers from, so a pid accepted
        here is a pid the caller can see in `/api/5/processlist`.
        """
        payload = request.app.state.store.get("processlist", {})
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return set()
        return {item["pid"] for item in data if isinstance(item, dict) and isinstance(item.get("pid"), int)}

    @router.post("/processes/extended/disable")
    async def unpin_extended_process(request: Request) -> bool:
        """Stop collecting extended stats for whichever process was pinned."""
        glances_processes.extended_pid = None
        glances_processes.disable_extended_tag = True
        # Clearing this is what actually stops the grab — it is keyed on
        # `extended_process` being set (`processes.py:663-669`), not on the
        # tag. v4 leaves it set and keeps paying for it.
        glances_processes.extended_process = None
        return True

    @router.post("/processes/extended/{pid}")
    async def pin_extended_process(pid: int, request: Request) -> bool:
        """Collect extended stats for `pid` from the next cycle on.

        404 on a pid the process list does not carry, as v4 does — v4 reaches
        that through `int(pid)`, which raises `ValueError` (→ 500) on garbage;
        here FastAPI's path type rejects it with a 422 before the handler runs.
        """
        if pid not in _pinnable_pids(request):
            raise HTTPException(status_code=404, detail=f"Unknown PID process {pid}")
        glances_processes.extended_pid = pid
        glances_processes.disable_extended_tag = False
        # The previous pin's accumulated min/max/mean must not carry over to
        # the new process. The model's own pid guard would hide it for one
        # cycle anyway; clearing it here means there is nothing to hide.
        glances_processes.extended_process = None
        return True


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
        # PBKDF2 off the event loop — see the auth middleware in webserver_v5.
        # Bytes: compare_digest raises TypeError on a non-ASCII str (-> 500).
        if not hmac.compare_digest(
            credentials.username.encode(), expected_user.encode()
        ) or not await run_in_threadpool(verify_password, credentials.password, password_hash):
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

    # Declared BEFORE /{plugin_name}/info: FastAPI matches routes in declaration
    # order, so the dynamic route would otherwise swallow `all` as a plugin name.
    router.add_api_route("/all/info", _all_info, methods=["GET"], name="all_info")

    @router.get("/alert")
    async def alert_history(request: Request) -> list[dict[str, Any]]:
        alerts = request.app.state.alerts
        if alerts is None:
            raise HTTPException(status_code=404, detail="Alerts subsystem disabled")
        return alerts.get_history()

    # Declared BEFORE /{plugin_name}, like /all/info: FastAPI matches routes
    # in declaration order, so a dynamic route declared first would swallow
    # `alert` as a plugin name.
    router.add_api_route("/alert/incidents", _alert_incidents, methods=["GET"], name="alert_incidents")

    @router.get("/config")
    async def config_dump(request: Request) -> dict[str, Any]:
        return request.app.state.config.as_dict_secure()

    @router.get("/args")
    async def args_dump(request: Request) -> dict[str, Any]:
        """Return the CLI argument namespace, redacted (issue #1527 / CVE-2026-68520)."""
        return _redact_args(getattr(request.app.state, "args", None))

    _register_extended_process_routes(router)
    _register_history_route(router)

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


async def _all_info(request: Request) -> dict[str, Any]:
    """Every registered plugin's schema, published or not (G9-5).

    A schema is static, unlike the payloads /all skips at cycle 0. The WebUI
    fetches this once per page load.
    """
    return {name: plugin.fields_description for name, plugin in _plugins(request).items()}


async def _alert_incidents(request: Request) -> dict[str, Any]:
    """The alert history collapsed into incidents — the same synthesis
    the TUI's alert block paints (glances/alerts_incidents_v5.py).

    Module-level rather than a closure inside `build_router()`, like
    `_all_info` above: that factory was already at ruff's complexity
    ceiling, so every route added inside it pushes it over.

    A second projection of the same data as ``/alert``, not a
    replacement: that route stays the raw transition-log export
    contract.

    Each incident also carries a ``duration``: the same formatted,
    ``>``-prefixed-when-``partial`` string the curses renderer shows
    (`incident_duration()`, also from `glances.alerts_incidents_v5`).
    Computed here rather than left to the caller so the browser cannot
    grow a second implementation of the ``partial`` → ``>`` rule — a
    client that dropped that prefix would print a lower bound as an
    exact duration. ``duration`` is always present in the response;
    its value is ``null`` for the handful of malformed/unknown cases
    `incident_duration()` itself returns ``None`` for (see its
    docstring), which a consumer must treat as "unknown", not as a
    missing key.

    `derive_incidents()` is pure and builds every incident dict fresh
    (never a reference into `alerts._history` or `alerts._state`), so
    mutating the returned dicts in place to add `duration` does not
    touch anything the engine still owns.

    Returns an envelope, not a bare array: ``is_initializing`` is
    ``GlancesAlerts.is_initializing()``, the same flag
    `render_alert_block` uses to tell "warm-up" from "no alert
    detected" (curses_renderer_v5.py:738-745) — warm-up is not an
    all-clear, so a client must be able to tell the two apart instead
    of reading an empty ``incidents`` list as a healthy system from the
    very first paint (fix round 2, IMPORTANT 2). No consumer of this
    route predates this change, so the shape is still free to pick.
    """
    alerts = request.app.state.alerts
    if alerts is None:
        raise HTTPException(status_code=404, detail="Alerts subsystem disabled")
    incidents = derive_incidents(
        alerts.get_history(),
        ongoing=alerts.get_ongoing(),
        ongoing_since=alerts.get_ongoing_since(),
        ongoing_top=alerts.get_ongoing_top(),
    )
    for incident in incidents:
        incident["duration"] = incident_duration(incident)
    return {"is_initializing": alerts.is_initializing(), "incidents": incidents}


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
