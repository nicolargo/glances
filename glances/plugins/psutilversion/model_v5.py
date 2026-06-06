#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — psutilversion plugin (psutil version string, REST-only).

Migrated from `glances/plugins/psutilversion/__init__.py`. No v4
``msg_curse`` → ``DISPLAY_IN_TUI=False``. Constant data.
"""

from __future__ import annotations

from typing import Any, ClassVar

from glances import psutil_version_info as _PSUTIL_VERSION_INFO
from glances.plugins.plugin.base_v5 import GlancesPluginBase


class PluginModel(GlancesPluginBase[dict]):
    """psutil version plugin (scalar, REST-only)."""

    plugin_name: ClassVar[str] = "psutilversion"
    IS_COLLECTION: ClassVar[bool] = False
    DISPLAY_IN_TUI: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "version": {"description": "psutil version.", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"version": ".".join(str(i) for i in _PSUTIL_VERSION_INFO)}
