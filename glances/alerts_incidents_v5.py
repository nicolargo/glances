#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — incident synthesis.

Collapses a transition log (`GlancesAlerts.get_history()`) into incidents:
an incident opens on the first transition away from `ok` for a
`(plugin, key, field)` tuple and closes on its transition back to `ok`.
Escalations mutate the open incident instead of opening a new one.

This module is pure — no curses, no I/O, data in and data out — because it
has two consumers that must not depend on each other: the curses alert
block (`glances/outputs/curses_renderer_v5.py`) and the
`/api/5/alert/incidents` REST endpoint. It lives in neither.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _format_duration_compact(seconds: float) -> str:
    """Elapsed time in at most 8 columns (design §6.4).

    ``43s`` / ``2m58s`` / ``1h13m`` / ``2d04h``. Replaces ``str(timedelta)``,
    whose ``0:02:04`` reads as a clock rather than an elapsed time and whose
    width is unpredictable. Sub-second precision is dropped so the value does
    not jitter between refreshes.
    """
    total = int(max(0.0, seconds))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m{total % 60:02d}s"
    if total < 86400:
        return f"{total // 3600}h{(total % 3600) // 60:02d}m"
    return f"{total // 86400}d{(total % 86400) // 3600:02d}h"


def incident_duration(incident: dict[str, Any], now: datetime | None = None) -> str | None:
    """Rendered duration of one incident, or ``None`` when it cannot be known.

    Ongoing incidents measure from ``begin`` to now; resolved ones from
    ``begin`` to ``end``, so a resolved row freezes instead of ticking. A
    ``partial`` incident — one whose opening transition has aged out of the
    history — is prefixed ``>`` because its duration is a lower bound.

    Returns ``None`` for an unknown, malformed or future ``begin`` (clock
    skew): the caller then leaves the column blank rather than printing
    something false. Never raises — the renderer must not crash on a
    malformed event.
    """
    begin_raw = incident.get("begin")
    if not begin_raw:
        return None
    try:
        begin = datetime.fromisoformat(str(begin_raw))
    except (ValueError, TypeError):
        return None
    if begin.tzinfo is None:
        begin = begin.replace(tzinfo=timezone.utc)

    end_raw = incident.get("end")
    end: datetime | None = None
    if end_raw:
        try:
            end = datetime.fromisoformat(str(end_raw))
        except (ValueError, TypeError):
            end = None
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
    if end is None:
        end = now or datetime.now(tz=timezone.utc)

    elapsed = (end - begin).total_seconds()
    if elapsed < 0:
        return None
    text = _format_duration_compact(elapsed)
    return f">{text}" if incident.get("partial") else text


# Severity ranking, used to keep an incident's level monotonic: once an
# incident has reached `critical` it keeps reporting `critical` even if it
# later de-escalates. v4 parity — `GlancesEvent.update()` assigns `state`
# only on CRITICAL (design §2.6).
_LEVEL_ORDER: dict[str, int] = {"ok": 0, "careful": 1, "warning": 2, "critical": 3}


def derive_incidents(
    history: list[dict[str, Any]],
    ongoing: dict[tuple[str, Any, str], str] | None = None,
    ongoing_since: dict[tuple[str, Any, str], str] | None = None,
    ongoing_top: dict[tuple[str, Any, str], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Collapse a transition log into incidents (design §5.6).

    The alert engine records level *transitions*; the block shows *incidents*.
    An incident opens on the first transition to a non-``ok`` level for a
    ``(plugin, key, field)`` tuple and closes on its transition back to
    ``ok``. Escalations mutate the open incident, they never open a new one —
    that is the "one row per incident" rule (§5.4).

    ``ongoing`` is ``GlancesAlerts.get_ongoing()``. It is the AUTHORITY on
    what is still active: the history is a bounded ring buffer, so an alert
    can outlive its own transitions. Passing ``None`` falls back to deriving
    "ongoing" from the history alone, which is what direct callers (export,
    tests) want.

    ``ongoing_since`` is ``GlancesAlerts.get_ongoing_since()`` — same keys,
    and for the same reason the AUTHORITY on when each active incident
    opened. Without it, an alert whose opening event has aged out of the
    history has no start at all (rendered ``--:--:--``) or only a lower bound
    taken from a surviving escalation (rendered ``>2h04m``).

    ``ongoing_top`` is ``GlancesAlerts.get_ongoing_top()`` — the accumulated
    top processes of each ACTIVE incident, and the authority for them for the
    same ring-buffer reason as ``ongoing_since``. Resolved incidents keep the
    value frozen in their opening event.

    Returns incidents already sorted: ongoing first, newest first within each
    group (§5.3), so a long-running alert cannot sink out of the visible
    window behind newer resolved ones.
    """
    open_by_tuple: dict[tuple[str, Any, str], dict[str, Any]] = {}
    incidents: list[dict[str, Any]] = []

    for evt in history:
        state_key = (str(evt.get("plugin", "")), evt.get("key"), str(evt.get("field", "")))
        level = str(evt.get("level", ""))
        ts = str(evt.get("ts", "")) or None
        if level == "ok":
            closed = open_by_tuple.pop(state_key, None)
            if closed is not None:
                closed["end"] = ts
                closed["ongoing"] = False
            continue
        incident = open_by_tuple.get(state_key)
        if incident is None:
            # A first surviving transition that did not come from `ok` means
            # the opening transition has been evicted from the ring buffer:
            # `begin` is then a lower bound, not the real start. An
            # `is_initial` event is exempt — it IS the start, Glances simply
            # found the system already in that state at boot.
            previous = str(evt.get("previous_level", "ok"))
            partial = previous != "ok" and not bool(evt.get("is_initial", False))
            incident = {
                "plugin": state_key[0],
                "key": state_key[1],
                "field": state_key[2],
                "level": level,
                "begin": ts,
                "end": None,
                "ongoing": True,
                "partial": partial,
                "prominent": bool(evt.get("prominent", False)),
                "top": list(evt.get("top") or []),
                "top_sort": evt.get("top_sort"),
            }
            open_by_tuple[state_key] = incident
            incidents.append(incident)
            continue
        if _LEVEL_ORDER.get(level, 0) > _LEVEL_ORDER.get(incident["level"], 0):
            incident["level"] = level
        incident["prominent"] = incident["prominent"] or bool(evt.get("prominent", False))

    if ongoing is not None:
        for state_key, incident in open_by_tuple.items():
            committed = ongoing.get(state_key)
            if committed is None:
                # The engine says recovered but no `→ ok` event survives.
                # Trust the engine and close the incident with an unknown end.
                incident["ongoing"] = False
            elif _LEVEL_ORDER.get(committed, 0) > _LEVEL_ORDER.get(incident["level"], 0):
                incident["level"] = committed
        # Tuples the engine reports active but the history no longer covers at
        # all. Without this the block would silently drop a live alert.
        for state_key, committed in ongoing.items():
            if state_key in open_by_tuple:
                continue
            incidents.append(
                {
                    "plugin": state_key[0],
                    "key": state_key[1],
                    "field": state_key[2],
                    "level": committed,
                    "begin": None,
                    "end": None,
                    "ongoing": True,
                    "partial": True,
                    "prominent": False,
                    "top": [],
                    "top_sort": None,
                }
            )

    # The engine remembers when every ACTIVE incident opened, even once the
    # history has evicted the opening event, so its timestamp wins over
    # whatever the history could reconstruct. That turns a `--:--:--` start
    # (nothing survived) or a `>` lower bound (only an escalation survived)
    # back into the real one. Applied before the sort so the ordering uses the
    # corrected `begin`. Resolved incidents are absent from the map and keep
    # their history-derived values.
    if ongoing_since:
        for incident in incidents:
            if not incident["ongoing"]:
                continue
            since = ongoing_since.get((incident["plugin"], incident["key"], incident["field"]))
            if since:
                incident["begin"] = since
                incident["partial"] = False

    # Same authority argument as `ongoing_since`: for an ACTIVE incident the
    # engine's live accumulator wins over whatever copy the history still
    # holds. Resolved incidents are absent from the map and keep the value
    # frozen in their opening event.
    if ongoing_top:
        for incident in incidents:
            if not incident["ongoing"]:
                continue
            entry = ongoing_top.get((incident["plugin"], incident["key"], incident["field"]))
            if entry:
                incident["top"] = list(entry.get("top") or [])
                incident["top_sort"] = entry.get("top_sort")

    # Two stable passes: chronological within a group, then ongoing on top.
    incidents.sort(key=lambda i: i["begin"] or "", reverse=True)
    incidents.sort(key=lambda i: 0 if i["ongoing"] else 1)
    return incidents
