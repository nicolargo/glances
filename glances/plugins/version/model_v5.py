#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — version plugin (Glances version string, REST-only).

Migrated from `glances/plugins/version/__init__.py`. No v4 ``msg_curse`` →
``DISPLAY_IN_TUI=False``. Constant data (changes only on upgrade).
"""

from __future__ import annotations

from typing import Any, ClassVar

from glances import __version__ as _GLANCES_VERSION
from glances.plugins.plugin.base_v5 import GlancesPluginBase


class PluginModel(GlancesPluginBase[dict]):
    """Glances version plugin (scalar, REST-only)."""

    plugin_name: ClassVar[str] = "version"
    IS_COLLECTION: ClassVar[bool] = False
    DISPLAY_IN_TUI: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "version": {"description": "Glances version.", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"version": _GLANCES_VERSION}
