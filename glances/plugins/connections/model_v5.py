#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — connections plugin (scalar).

Migrated from `glances/plugins/connections/__init__.py`. The v4 module is
left untouched until the final `develop-v5 → develop` merge (architecture
§10). The only scalar plugin of group G6B — do not model `folders` or
`ports` (both collections) by analogy with it.

Two independent sources are collected each cycle:

- `psutil.net_connections(kind="tcp")` — per-status connection counts.
- The Netfilter conntrack counters under `/proc/sys/net/netfilter/`.

Disabled by default (`[connections] disable=True` ships in
`conf/glances.conf`, mirrored by `DISABLED_BY_DEFAULT = True`) because
`psutil.net_connections()` is expensive on a host with a large socket
table. A disabled plugin is not instantiated by
`main_v5.discover_plugins()`.

Two non-obvious points a future "cleanup" could otherwise undo:

1. The `net_connections_enabled` / `nf_conntrack_enabled` flags are
   deliberately per-cycle locals, not instance state: a source that fails
   is retried on the next cycle so a transient failure self-heals (e.g.
   the `nf_conntrack` kernel module being loaded after Glances starts).
   Do not hoist them onto `self`.

   v4 went the other way in `4591a6f5` ("Remember that a connections probe
   was disabled"): it latches a failed probe onto the plugin for the rest
   of the session. v5 keeps the retry — losing the self-healing is the
   higher price — and addresses what that commit was actually fixing (the
   warning replayed on every refresh) with the one-shot logging below, so
   a probe that can never work costs exactly one WARNING line.
2. `terminated` is computed from `terminated_states`, not
   `initiated_states`. v4 (`__init__.py:123`) iterates
   `self.initiated_states` where it must iterate `self.terminated_states`,
   so v4's `terminated` is today an exact copy of `initiated` and
   `terminated_states` is dead code. This is an approved bug fix: v5 uses
   `terminated_states`, so `terminated` is a real, distinct count (usually
   in the hundreds — TIME_WAIT dominates — vs. `initiated`'s near-zero).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[dict]):
    """TCP connections + Netfilter conntrack plugin (scalar)."""

    plugin_name: ClassVar[str] = "connections"
    IS_COLLECTION: ClassVar[bool] = False
    EMITS_ALERTS: ClassVar[bool] = True
    # Mirrors v4 `[connections] disable=True`: off unless the operator opts in.
    DISABLED_BY_DEFAULT: ClassVar[bool] = True
    # `psutil.net_connections()` costs ~27ms with only ~40 sockets and scales
    # with the socket table — a busy server pays far more. An operator who
    # opts in should not get it at the 2s global rate by default.
    DEFAULT_REFRESH_TIME: ClassVar[float | None] = 10.0

    status_list: ClassVar[list[str]] = [psutil.CONN_LISTEN, psutil.CONN_ESTABLISHED]
    initiated_states: ClassVar[list[str]] = [psutil.CONN_SYN_SENT, psutil.CONN_SYN_RECV]
    terminated_states: ClassVar[list[str]] = [
        psutil.CONN_FIN_WAIT1,
        psutil.CONN_FIN_WAIT2,
        psutil.CONN_TIME_WAIT,
        psutil.CONN_CLOSE,
        psutil.CONN_CLOSE_WAIT,
        psutil.CONN_LAST_ACK,
    ]
    conntrack_paths: ClassVar[dict[str, str]] = {
        "nf_conntrack_count": "/proc/sys/net/netfilter/nf_conntrack_count",
        "nf_conntrack_max": "/proc/sys/net/netfilter/nf_conntrack_max",
    }

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "net_connections_enabled": {
            "description": (
                "Whether `psutil.net_connections()` succeeded during THIS cycle "
                "(re-evaluated every cycle — a failure is not latched)."
            ),
            "unit": "bool",
        },
        "nf_conntrack_enabled": {
            "description": (
                "Whether the Netfilter conntrack /proc counters were readable during "
                "THIS cycle (re-evaluated every cycle — a failure is not latched)."
            ),
            "unit": "bool",
        },
        "LISTEN": {
            "description": "Number of TCP connections in LISTEN state.",
            "unit": "number",
        },
        "ESTABLISHED": {
            "description": "Number of TCP connections in ESTABLISHED state.",
            "unit": "number",
        },
        "initiated": {
            "description": "Number of TCP connections initiated (SYN_SENT + SYN_RECV).",
            "unit": "number",
        },
        "terminated": {
            "description": (
                "Number of TCP connections terminated (FIN_WAIT1, FIN_WAIT2, TIME_WAIT, CLOSE, CLOSE_WAIT, LAST_ACK)."
            ),
            "unit": "number",
        },
        "nf_conntrack_count": {
            "description": "Number of tracked connections.",
            "unit": "number",
        },
        "nf_conntrack_max": {
            "description": "Maximum number of tracked connections.",
            "unit": "number",
        },
        "nf_conntrack_percent": {
            "description": "Percentage of tracked connections (nf_conntrack_count / nf_conntrack_max * 100).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": {"careful": 70.0, "warning": 80.0, "critical": 90.0},
        },
    }

    def __init__(self, store, config) -> None:
        super().__init__(store, config)

        # Names of the probes whose failure has already been reported. This is
        # log-deduplication state only — NOT the enabled flags, which stay
        # per-cycle locals (see the module docstring). Cleared for a probe as
        # soon as it works again, so a flapping probe is not silenced forever.
        self._probe_warned: set[str] = set()

    def _log_probe_failure(self, probe: str, exc: Exception) -> None:
        """WARNING the first time `probe` fails, DEBUG on every repeat."""
        first = probe not in self._probe_warned
        self._probe_warned.add(probe)
        logger.log(
            logging.WARNING if first else logging.DEBUG,
            "connections: %s probe failed this cycle (%s)",
            probe,
            exc,
        )

    def _collect_net_connections(self, stats: dict[str, Any]) -> bool:
        """Fill the connection-state counters. Return False if unavailable.

        The return value is the caller's per-cycle flag — nothing is
        stored on `self`, so the next cycle tries again (v4 parity).
        """
        try:
            connections = psutil.net_connections(kind="tcp")
        except Exception as exc:  # noqa: BLE001 — retried next cycle, never latched
            self._log_probe_failure("net_connections", exc)
            return False

        self._probe_warned.discard("net_connections")
        for status in self.status_list:
            stats[status] = len([c for c in connections if c.status == status])
        stats["initiated"] = sum(1 for c in connections if c.status in self.initiated_states)
        # Approved bug fix vs v4 (__init__.py:123): iterate terminated_states,
        # not initiated_states, so `terminated` is a real, distinct count.
        stats["terminated"] = sum(1 for c in connections if c.status in self.terminated_states)
        return True

    def _collect_nf_conntrack(self, stats: dict[str, Any]) -> bool:
        """Fill the conntrack counters. Return False if unreadable.

        Same per-cycle contract as `_collect_net_connections`: a missing
        `/proc` entry today does not prevent a read tomorrow (the
        `nf_conntrack` module may be loaded after Glances starts).
        """
        for field_name, path in self.conntrack_paths.items():
            try:
                with open(path) as f:
                    stats[field_name] = float(f.readline().rstrip("\n"))
            except (OSError, FileNotFoundError) as exc:
                self._log_probe_failure("nf_conntrack", exc)
                return False

        self._probe_warned.discard("nf_conntrack")
        # Defensive: nf_conntrack_max == 0 would raise ZeroDivisionError and
        # lose the whole cycle. Skip the percent field only; the two raw
        # counters and nf_conntrack_enabled are unaffected.
        if stats.get("nf_conntrack_max"):
            stats["nf_conntrack_percent"] = stats["nf_conntrack_count"] * 100 / stats["nf_conntrack_max"]
        return True

    def _collect(self) -> dict[str, Any]:
        # Both flags are LOCALS, recreated on every call. Do not hoist them
        # onto `self` — see the module docstring.
        stats: dict[str, Any] = {}
        net_connections_enabled = self._collect_net_connections(stats)
        nf_conntrack_enabled = self._collect_nf_conntrack(stats)
        stats["net_connections_enabled"] = net_connections_enabled
        stats["nf_conntrack_enabled"] = nf_conntrack_enabled
        return stats

    async def _grab_stats(self) -> dict:
        return await asyncio.to_thread(self._collect)
