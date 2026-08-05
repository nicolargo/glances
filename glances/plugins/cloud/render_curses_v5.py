#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the cloud plugin (header block).

Mirrors v4 `cloud.msg_curse()`: the platform name as a title, followed by
the instance summary.

    OpenStack gold instance my-vm (eu-west-1a)

Routed to the header slot next to `uptime`, matching v4's banner
(`curses_renderer_v5.HEADER_SLOT_RIGHT`). The model publishes `{}` when
the metadata is incomplete; this renderer returns an empty row list for any
payload lacking both platform and name (v4 guard against issue #2485).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row

_UNKNOWN = "Unknown"


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    # Guard against partial metadata: platform and name are mandatory.
    # Task 1 model guarantees all-or-nothing, but this is a second line of defence
    # (v4 check for issue #2485, prevents rendering "Unknown" as the instance name).
    if not isinstance(payload, dict) or not payload.get("platform") or not payload.get("name"):
        return []
    summary = " {} instance {} ({})".format(
        payload.get("type", _UNKNOWN),
        payload.get("name", _UNKNOWN),
        payload.get("region", _UNKNOWN),
    )
    return [
        Row(
            cells=[
                Cell(text=str(payload["platform"]), color=ColorRole.HEADER, bold=True),
                Cell(text=summary),
            ]
        )
    ]
