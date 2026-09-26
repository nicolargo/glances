#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--api-restful-doc`: docs/api/restful.rst, generated from the API itself.

v4 parity (`glances/outputs/glances_stdout_api_restful_doc.py`), decided by
the maintainer on 2026-09-26: the page describes `/api/5` and cannot drift
from the code.

- The route index comes from the application's own OpenAPI schema, so a route
  added, renamed or removed changes the page.
- Every example is a real response: the v5 app is built in memory (no port is
  opened), the plugins run two cycles, and each route is called with a
  `TestClient`. v4 printed its stats objects and wrote the `curl` lines by
  hand next to them.
- Each plugin's fields, units and descriptions come from its
  `fields_description`, as `/api/5/<plugin>/info` serves them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, TextIO

from glances.api_v5_doc import _escape

API_URL = "http://localhost:61208/api/5"
# A collection example keeps this many items; the rest is summarised.
_EXAMPLE_ITEMS = 2

_HEADER = f"""\
.. _api_restful:

Restful/JSON API documentation
==============================

This page describes the Glances API version 5 (Restful/JSON). Every example
below is a real response, taken when the page was generated.

Run the Glances API server
--------------------------

The API and the Web UI are served by:

.. code-block:: bash

    # glances-v5 -s

Add ``--disable-webui`` to serve the API alone.

API URL
-------

The root API URL is ``{API_URL}``. The bind address and the port are set with
``--bind`` and ``--port``, or ``[outputs] bind_address`` and ``port`` in
``glances.conf``. The server listens on ``127.0.0.1`` by default.

API documentation URL
---------------------

The server documents itself at ``http://localhost:61208/docs`` (Swagger UI) and
``http://localhost:61208/redoc``, unless ``--no-api-doc`` or
``[outputs] api_doc=false`` turns them off.

Authentication
--------------

The API is open by default. Set ``[outputs] password`` to a hash made with
``glances-v5 --set-password``, and every route except ``/status``,
``/healthz`` and ``/api/5/token`` then requires HTTP Basic credentials
(``[outputs] username``, ``glances`` by default) or a JWT bearer token:

.. code-block:: bash

    # curl -u glances:<password> -X POST {API_URL}/token
    # curl -H "Authorization: Bearer <access_token>" {API_URL}/cpu
"""


def _title(text: str, underline: str = "-") -> list[str]:
    return [text, underline * len(text), ""]


def _example(command: str, body: Any) -> list[str]:
    text = body if isinstance(body, str) else json.dumps(body, indent=4, sort_keys=True, default=str)
    return [".. code-block:: bash", "", f"    # {command}"] + ["    " + line for line in text.split("\n")] + [""]


def _shorten(payload: Any) -> Any:
    """A collection example keeps its first items and says how many were left out."""
    if isinstance(payload, dict) and isinstance(payload.get("data"), list) and len(payload["data"]) > _EXAMPLE_ITEMS:
        rest = len(payload["data"]) - _EXAMPLE_ITEMS
        return {**payload, "data": payload["data"][:_EXAMPLE_ITEMS] + [f"... {rest} more"]}
    return payload


def _route_index(schema: dict[str, Any]) -> list[str]:
    out = _title("Routes")
    out += ["Every route the server publishes, from its OpenAPI schema:", ""]
    out += [".. list-table::", "    :header-rows: 1", "", "    * - Method", "      - Path", "      - Purpose"]
    for path, operations in schema.get("paths", {}).items():
        for method, operation in operations.items():
            purpose = (operation.get("description") or "").strip().split("\n")[0] or operation.get("summary", "")
            out += [f"    * - {method.upper()}", f"      - ``{path}``", f"      - {_escape(purpose)}"]
    return out + [""]


def _plugin(client: Any, name: str) -> list[str]:
    out = _title(f"GET {name}")
    payload = client.get(f"/api/5/{name}").json()
    out += ["Get the plugin stats:", ""]
    out += _example(f"curl {API_URL}/{name}", _shorten(payload))
    fields = client.get(f"/api/5/{name}/info").json() or {}
    if fields:
        out += ["Fields (``/info`` serves them as JSON):", ""]
        for field, schema in fields.items():
            unit = schema.get("unit")
            description = _escape(str(schema.get("description", "")).strip())
            out.append(f"* ``{field}``: {description}" + (f" (unit is *{_escape(str(unit))}*)" if unit else ""))
        out.append("")
    limits = client.get(f"/api/5/{name}/limits").json()
    if limits:
        out += ["Get the thresholds in effect:", ""]
        out += _example(f"curl {API_URL}/{name}/limits", limits)
    history = client.get(f"/api/5/{name}/history", params={"nb": 2}).json()
    if history.get("series"):
        out += ["Get the last two points of its history (``nb=0`` for all of them):", ""]
        out += _example(f"curl {API_URL}/{name}/history?nb=2", history)
    return out


def render(client: Any, schema: dict[str, Any]) -> str:
    """The whole restful.rst page, from calls on `client` (a TestClient on the v5 app)."""
    lines = [_HEADER]
    lines += _route_index(schema)
    lines += _title("GET status")
    lines += ["Check that the server is up (no authentication needed):", ""]
    lines += _example("curl http://localhost:61208/status", client.get("/status").json())
    plugins = client.get("/api/5/pluginslist").json()
    lines += _title("GET plugins list")
    lines += _example(f"curl {API_URL}/pluginslist", plugins)
    lines += _title("GET all stats")
    lines += ["Every plugin's payload in one call, a large dictionary:", ""]
    lines += [".. code-block:: bash", "", f"    # curl {API_URL}/all", ""]
    lines += _title("GET alerts")
    lines += ["The alert events, most recent last, then the same history grouped into incidents:", ""]
    lines += _example(f"curl {API_URL}/alert", client.get("/api/5/alert").json())
    lines += _example(f"curl {API_URL}/alert/incidents", client.get("/api/5/alert/incidents").json())
    lines += _title("Pin a process for extended stats")
    lines += [
        "Collect extended stats (affinity, I/O nice, open files, connections) for one process,",
        "then stop. They appear in the ``extended`` metadata of ``/api/5/processlist``:",
        "",
        ".. code-block:: bash",
        "",
        f"    # curl -X POST {API_URL}/processes/extended/<pid>",
        f"    # curl -X POST {API_URL}/processes/extended/disable",
        "",
    ]
    for name in plugins:
        lines += _plugin(client, name)
    return "\n".join(lines).rstrip() + "\n"


async def _collect(plugins: list[Any], alerts: Any, wait: float) -> None:
    """Two cycles, `wait` apart, so rates have a value and alerts a history."""
    for _ in range(2):
        for plugin in plugins:
            await plugin.update()
            await alerts.ingest_plugin(plugin)
        await asyncio.sleep(wait)


def run(config: Any, out: TextIO = sys.stdout, wait: float = 1.0) -> int:
    """`--api-restful-doc`: build the v5 app in memory, call it, print the page."""
    from fastapi.testclient import TestClient

    from glances.alerts_v5 import GlancesAlerts
    from glances.main_v5 import attach_history, discover_plugins
    from glances.stats_store_v5 import StatsStoreV5
    from glances.webserver_v5 import build_app, register_plugin

    store = StatsStoreV5()
    plugins = discover_plugins(store, config)
    attach_history(plugins, config, argparse.Namespace(disable_history=False))
    # No actions: generating a page must not run the commands glances.conf
    # attaches to alerts.
    alerts = GlancesAlerts(config, actions={})
    try:
        asyncio.run(_collect(plugins, alerts, wait))
        # No `args`: the page documents the API, and the Web UI is not wired.
        app = build_app(config=config, store=store, alerts=alerts)
        for plugin in plugins:
            register_plugin(app, plugin)
        with TestClient(app) as client:
            out.write(render(client, app.openapi()))
    finally:
        for plugin in plugins:
            try:
                plugin.stop()
            except Exception:  # noqa: S110 -- best effort on the way out
                pass
    return 0
