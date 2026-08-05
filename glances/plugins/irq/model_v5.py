#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — IRQ plugin (collection, per interrupt line).

Migrated from `glances/plugins/irq/__init__.py`. Linux-only: reads
`/proc/interrupts` and publishes the busiest five interrupt lines.

**Rate handling differs from v4 on purpose.** v4 computed the rate by hand
and shipped a precedence bug (`a - b if b else 0 // elapsed` binds as
`(a - b) if b else (0 // elapsed)`), so the division never applied and the
published `irq_rate` was a per-cycle *delta* despite its
`numberpersecond` unit. Here `_grab_stats` returns the **cumulative**
counter and `rate: True` lets the base class divide by
`time_since_update`. Values therefore differ from v4 — the v5 ones are
the ones the field name always claimed.

**Default-disabled**: v4 ships `[irq] disable=True`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.globals import LINUX
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

IRQ_FILE = "/proc/interrupts"

# v4 keeps only the busiest lines; the cap lives at the data layer so the
# REST payload and the TUI agree on what "top" means.
_TOP_N = 5


def parse_interrupts(content: str) -> list[dict[str, Any]]:
    """Parse `/proc/interrupts` content into cumulative per-line counters.

    The first line is the CPU header; its column count tells us how many
    numeric columns each following line carries. Everything after those
    columns is the controller/device description.

        1:      44487        341   IO-APIC   1-edge      i8042
        LOC: 33549868   22394684   Local timer interrupts
    """
    lines = content.splitlines()
    if not lines:
        return []

    cpu_number = len(lines[0].split())
    out: list[dict[str, Any]] = []
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        irq_line = parts[0].replace(":", "")
        if irq_line.isdigit():
            # Numeric lines are meaningless on their own — v4 appends the
            # device alias from the last column.
            irq_line += f"_{parts[-1]}"
        try:
            total = sum(map(int, parts[1 : cpu_number + 1]))
        except ValueError:
            # Some platforms emit lines with no counter columns (v4 #1007).
            total = 0
        out.append({"irq_line": irq_line, "irq_rate": total})
    return out


class PluginModel(GlancesPluginBase[list]):
    """Per-interrupt-line plugin (collection)."""

    plugin_name: ClassVar[str] = "irq"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = False
    # Mirrors v4 `[irq] disable=True`.
    DISABLED_BY_DEFAULT: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "irq_line": {
            "description": "IRQ line name, suffixed with the device alias when numeric.",
            "unit": "string",
            "primary_key": True,
        },
        "irq_rate": {
            "description": "Interrupts per second on this line.",
            "unit": "numberpersecond",
            "rate": True,
        },
    }

    def _read_proc(self) -> str:
        """Read `/proc/interrupts`. Seam for tests."""
        # The `open()` itself is inside the caller's try (Snap strict
        # confinement blocks at open, not at read).
        with open(IRQ_FILE) as f:
            return f.read()

    def _collect(self) -> list:
        if not LINUX:
            return []
        try:
            content = self._read_proc()
        except OSError as exc:
            # Missing on OpenVZ containers (v4 #947); also unreadable under
            # some confinements. Debug level: this is expected, not a fault.
            logger.debug("irq: cannot read %s: %s", IRQ_FILE, exc)
            return []
        return parse_interrupts(content)

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    def _expand_parameters(self) -> None:
        """Sort by rate and keep the top N.

        Runs after `_transform_gauge` (so `irq_rate` is a real rate, not a
        counter) and before `_derived_parameters` — which stays untouched,
        keeping the plugin visible to `/api/5/irq/limits`.

        Items on their first appearance carry no `irq_rate` at all, so they
        sort last rather than raising.
        """
        if not isinstance(self._stats, list):
            return
        self._stats.sort(key=lambda item: item.get("irq_rate", 0.0), reverse=True)
        del self._stats[_TOP_N:]
