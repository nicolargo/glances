#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Folders plugin (collection, per-monitored-folder).

Migrated from `glances/plugins/folders/__init__.py`. Wraps the v4
`FolderList` engine (`glances/folder_list.py`, reused **unchanged**) —
all per-folder config parsing (`folder_N_path/refresh/careful/warning/
critical`) and the per-folder `Timer` gating live inside that engine.

Per-folder thresholds are keyed by **list position** in v4's config
(`folder_1_critical`, not `<path>_size_critical`), so they cannot be
expressed through the base class's generic per-primary-key config-key
override mechanism (`base_v5.read_thresholds(..., pk_value=...)`).
`_derived_parameters()` is overridden instead — same pattern already used
by `raid`/`sensors`/`wifi` — reusing the base's pure threshold-computation
function (`thresholds_v5.compute_level`) directly against each item's own
embedded MB thresholds, converted to bytes.

`errno != 0` (folder unreadable/missing) always outranks the size ladder
and short-circuits it — v4 parity (`get_alert` returns the decoration
`'ERROR'` before any size comparison, which maps to `curses.A_BOLD` with
no colour, see `glances/outputs/glances_colors.py:167`). v5 has no
dedicated Level/ColorRole for that synthetic `'ERROR'` colour, so a
broken folder gets NO `_levels` entry at all: no colour, no alert, no
history, no action dispatch. The renderer (`render_curses_v5.py`) is
responsible for the bold-with-no-colour rendering.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from glances.folder_list import FolderList
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.plugin.thresholds_v5 import compute_level

_MB_TO_BYTES = 1_000_000  # v4 parity: int(threshold) * 1e6 — decimal mega, NOT 1024**2.


class PluginModel(GlancesPluginBase[list]):
    """Per-monitored-folder plugin (collection)."""

    plugin_name: ClassVar[str] = "folders"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True  # v4 calls glances_events.add() on every non-OK level.

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "path": {"description": "Absolute path.", "unit": "string", "primary_key": True},
        "size": {"description": "Folder size in bytes.", "unit": "bytes"},
        "refresh": {"description": "Refresh interval in seconds.", "unit": "seconds"},
        "errno": {"description": "Return code when retrieving folder size (0 is no error).", "unit": "number"},
        "careful": {"description": "Careful threshold in MB.", "unit": "megabyte"},
        "warning": {"description": "Warning threshold in MB.", "unit": "megabyte"},
        "critical": {"description": "Critical threshold in MB.", "unit": "megabyte"},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._folders = FolderList(config)

    async def _grab_stats(self) -> list:
        await asyncio.to_thread(self._folders.update, key=self._primary_key)
        # Fresh per-item copies: FolderList mutates its own dicts in place
        # on every cycle, and _stats_previous must not alias them.
        return [dict(item) for item in self._folders.get()]

    def _derived_parameters(self) -> None:
        """Bespoke per-folder threshold ladder (mirrors v4 `get_alert`).

        Overrides the base watched-field walk entirely: thresholds are not
        plugin-wide and not path-keyed in config — each folder carries its
        own already-resolved careful/warning/critical (in MB) from
        `FolderList`. See the plan's "Key implementation findings" #4.
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if path is None:
                continue
            level = self._folder_level(item)
            if level is None:
                # errno short-circuit (v4 parity): no _levels entry at all —
                # no alert, no history, no action dispatch. The renderer
                # falls back to bold/DEFAULT for this folder.
                continue
            self._levels[str(path)] = {"size": {"level": level, "prominent": False}}

    @staticmethod
    def _folder_level(item: dict[str, Any]) -> str | None:
        if item.get("errno") not in (None, 0):
            # errno short-circuits the size ladder unconditionally (v4
            # parity: `get_alert` returns 'ERROR' before any size
            # comparison). No v5 Level/ColorRole for that synthetic
            # 'ERROR' colour, so emit no level at all rather than map it
            # onto a real level — a broken folder must never alert.
            return None
        size = item.get("size")
        if size is None:
            return "ok"
        thresholds: dict[str, float] = {}
        for level_name in ("careful", "warning", "critical"):
            raw = item.get(level_name)
            if raw is None:
                continue
            try:
                thresholds[level_name] = int(raw) * _MB_TO_BYTES
            except (TypeError, ValueError):
                continue
        return compute_level(size, thresholds, direction="high")
