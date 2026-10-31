#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Field and item queries over one plugin's API payload.

The logic behind v4's field routes (`/<plugin>/top/<n>`, `/<plugin>/<field>`,
`/<plugin>/<field>/<pk>`, `/<plugin>/<field>/value/<v>`), kept out of the HTTP
layer because it has two consumers: `glances/routes.py` and the MCP tools in
`glances/outputs/glances_mcp.py`.

Every query reads `plugin.get_api_payload()`, the filtered view (issue #3211):
a non-exportable field is absent from every row, so it can be neither read nor
filtered on. Each returns `None` while the plugin has not published yet
(scheduler cycle 0) and raises `PluginQueryError` for a query that names
something the payload does not carry.
"""

from __future__ import annotations

from typing import Any


class PluginQueryError(LookupError):
    """A query names a field or an item the plugin does not carry.

    `str(exc)` is the message REST serves as its 404 detail.
    """

    def __str__(self) -> str:
        return str(self.args[0])


def _collection_payload(plugin) -> dict[str, Any] | None:
    if not plugin.IS_COLLECTION:
        raise PluginQueryError(f"Plugin {plugin.plugin_name!r} has no items")
    return plugin.get_api_payload() or None


def _check_field(plugin, rows: list[dict[str, Any]], field: str) -> None:
    # The rows are the API projection: a non-exportable field is in none of
    # them. An empty collection can only be checked against the schema, which
    # /info serves anyway.
    if not (any(field in row for row in rows) if rows else field in plugin.fields_description):
        raise PluginQueryError(f"Field {field!r} not found")


def top(plugin, n: int) -> list[dict[str, Any]] | None:
    """The first n items of a collection plugin, as a bare list (v4 `/top/<n>`)."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    payload = _collection_payload(plugin)
    if payload is None:
        return None
    return payload["data"][:n]


def field_values(plugin, field: str) -> dict[str, Any] | None:
    """One field: `{field: value}`, a list of values for a collection (v4 `/<plugin>/<item>`)."""
    payload = plugin.get_api_payload()
    if not payload:
        return None
    if not plugin.IS_COLLECTION:
        if field not in payload:
            raise PluginQueryError(f"Field {field!r} not found")
        return {field: payload[field]}
    _check_field(plugin, payload["data"], field)
    return {field: [row.get(field) for row in payload["data"]]}


def item_field(plugin, field: str, pk_value: str) -> dict[str, Any] | None:
    """One field of the item whose primary key is pk_value (v4 `/<plugin>/<item>/<key>`)."""
    payload = _collection_payload(plugin)
    if payload is None:
        return None
    # Compared as text: the path carries a string, the key may be a pid.
    row = next((row for row in payload["data"] if str(row.get(payload["_key"])) == pk_value), None)
    if row is None or field not in row:
        raise PluginQueryError(f"No {field!r} for item {pk_value!r}")
    return {field: row[field]}


def items_by_value(plugin, field: str, value: str) -> dict[str, list[dict[str, Any]]] | None:
    """The items whose field equals value: `{value: [items]}` (v4 `/<plugin>/<item>/value/<value>`)."""
    payload = _collection_payload(plugin)
    if payload is None:
        return None
    _check_field(plugin, payload["data"], field)
    return {value: [row for row in payload["data"] if str(row.get(field)) == value]}
