#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — memory leak check on the real scheduler (port of v4 `test_memoryleak`).

Drives the `--memory-leak` machinery of `main`: every enabled plugin, a 1 s
refresh, no history. Takes about twice `_CYCLES` seconds.
"""

from __future__ import annotations

import asyncio
import tracemalloc

from glances.config import GlancesConfig
from glances.main import _MEMORY_LEAK_REFRESH, apply_memory_leak_flags, assemble, build_parser, measure_memory_leak

# Refreshes in each window: the warm-up, then the measured one. Five is too
# short: on Python 3.10, psutil allocates ~1 KB per process once, at the 7th
# refresh, which reads as ~130 KB per refresh with 600 processes.
_CYCLES = 10
# Bytes per refresh, as in v4.
_THRESHOLD = 15000


def test_memoryleak_no_history(tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    config = GlancesConfig()
    args = build_parser().parse_args(["--memory-leak", "--stop-after", str(_CYCLES)])
    cycles = apply_memory_leak_flags(args, config)
    _app, scheduler, _host, _port, _tui = assemble(args, config)

    tracemalloc.start()
    try:
        diff = asyncio.run(measure_memory_leak(scheduler, cycles, _MEMORY_LEAK_REFRESH))
    finally:
        tracemalloc.stop()

    per_cycle = sum(stat.size_diff for stat in diff) // cycles
    top = "\n".join(str(stat) for stat in diff[:5])
    assert per_cycle < _THRESHOLD, f"Memory leak: {per_cycle} bytes per refresh\n{top}"
