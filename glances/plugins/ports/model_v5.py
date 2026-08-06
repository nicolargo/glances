#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Ports plugin (collection, one item per scanned host/URL).

Port of ``glances/plugins/ports/__init__.py`` (v4). ``GlancesPortsList``,
``GlancesWebList`` and ``ThreadScanner`` are reused VERBATIM (design §4): the
scan list is built once at construction, a single background ``ThreadScanner``
sweeps it, and ``_grab_stats()`` only relaunches that thread when it is dead —
it never awaits a scan.

One list holds TWO item kinds:

- port-scan items — carry ``host`` + ``port`` (``port == 0`` means ICMP);
- web items       — carry ``url`` + ``elapsed``.

``status`` is therefore a heterogeneous union (``None`` while scanning, ``0``
or ``False`` on timeout, a float RTT in seconds, an HTTP status code, or the
string ``"Error"``), and its level depends on the value's *type* as much as its
magnitude. Neither the base's numeric ladder nor its categorical mapping
describes that, so ``_derived_parameters()`` is overridden here.
``glances/plugins/plugin/base_v5.py`` is deliberately NOT modified (design §5.3).

See docs/superpowers/specs/2026-07-18-glances-v5-g6b-design.md.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.ports import ThreadScanner
from glances.ports_list import GlancesPortsList
from glances.timer import Timer
from glances.web_list import GlancesWebList

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[list]):
    """Ports/URL scanner plugin (collection, primary key ``indice``)."""

    plugin_name: ClassVar[str] = "ports"
    IS_COLLECTION: ClassVar[bool] = True
    # v4 runs `get_p_alert(log=False)`: the level colours the TUI cell but is
    # never written to the event history and never dispatches an action.
    EMITS_ALERTS: ClassVar[bool] = False
    # Interval between two full scans. NOT the publication cadence — see
    # SCHEDULE_AT_GLOBAL_REFRESH below; consumed by `_resolve_scan_interval`,
    # not by the scheduler.
    DEFAULT_REFRESH_TIME: ClassVar[float | None] = 30.0
    # Publish the scan-list snapshot on the fast global cadence, NOT on
    # `[ports] refresh`. The background `ThreadScanner` fills the list
    # incrementally (URLs are scanned LAST, after every port's mandatory
    # `time.sleep(1)`), so a snapshot published only every `[ports] refresh`
    # seconds freezes half-scanned items ("Scanning") for a whole interval.
    # v4 avoided this by reading the live list every display tick; we mirror
    # that by republishing cheaply every cycle while throttling the actual
    # scan below (self._scan_timer). See base SCHEDULE_AT_GLOBAL_REFRESH.
    SCHEDULE_AT_GLOBAL_REFRESH: ClassVar[bool] = True

    # HTTP status codes v4 treats as healthy for a web item.
    _WEB_OK_CODES: ClassVar[tuple[int, ...]] = (200, 301, 302)

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        # `port_0` is reserved for the auto-added default-gateway ICMP entry;
        # configured entries are `port_1`.. and `web_1`...
        "indice": {"description": "Unique indice for the host/port.", "unit": "string", "primary_key": True},
        "description": {"description": "Human readable description for the host/port/URL.", "unit": "string"},
        "host": {"description": "Measurement is done on this host (or IP address).", "unit": "string"},
        "port": {"description": "Measurement is done on this port (0 for ICMP).", "unit": "number"},
        "url": {"description": "Measurement is done on this URL (HEAD request).", "unit": "string"},
        "status": {
            "description": "Measurement result: None while scanning, 0/False on timeout, "
            "the RTT in seconds for a port, or the HTTP status code for a URL.",
            "unit": "second",
        },
        "elapsed": {"description": "HTTP response time (URL items only).", "unit": "second"},
        "rtt_warning": {"description": "Warning threshold (in seconds) for the measurement.", "unit": "second"},
        "timeout": {"description": "Timeout (in seconds) for the measurement.", "unit": "second"},
        # Stored for API parity. NOT used as a per-item timer — the whole list
        # is swept on the global `[ports] refresh` cadence (v4 behaviour, design §4).
        "refresh": {"description": "Refresh time (in seconds) for this host/port.", "unit": "second"},
        # NOT declared on purpose: `proxies` (may embed credentials via
        # web_x_http_proxy) and `ssl_verify`. The base `_remove_parameters()`
        # strips every undeclared field, so they never reach the store/REST/export.
    }

    def __init__(self, store, config) -> None:
        super().__init__(store, config)

        # Build the scan list ONCE, exactly as v4's __init__ does. The v4
        # builders are reused verbatim (design §4) and read the config through
        # `get_value(section, option[, default])` — served natively by
        # `GlancesConfigV5` since the shared fix that also unblocks `folders`
        # and (G6C) `amps`: `default` is optional and `default=None` returns
        # the raw uncoerced value, v4 `GlancesConfig.get_value` semantics.
        self._scan_list: list[dict[str, Any]] = (
            GlancesPortsList(config=config).get_ports_list() + GlancesWebList(config=config).get_web_list()
        )

        # The single background scanner sweeping the whole list. Relaunched by
        # `_grab_stats()` only when dead AND the scan timer has fired.
        self._thread: ThreadScanner | None = None

        # Throttle the (heavy) scan to `[ports] refresh`, decoupled from the
        # fast publication cadence — this is v4's `refresh_timer`/`get_refresh`.
        # `Timer(0)` is irrelevant here: the first sweep is launched
        # unconditionally (thread is None), which then arms the timer.
        self._scan_interval: float = self._resolve_scan_interval(config)
        self._scan_timer: Timer = Timer(self._scan_interval)

    def _resolve_scan_interval(self, config) -> float:
        """Seconds between two full scans, from `[ports] refresh` (or the
        `refresh_time` alias), else `DEFAULT_REFRESH_TIME` (30).

        The scan runs on this configured cadence while the display is refreshed
        on the global cadence (SCHEDULE_AT_GLOBAL_REFRESH). This plugin resolves
        its own cadence because the scheduler deliberately ignores it — hence
        the class default is read here rather than in `AsyncScheduler`.
        A `-1.0` float default is used (not `None`) so the value is coerced to
        float rather than routed through the untyped `get_value` passthrough.
        """
        for key in ("refresh", "refresh_time"):
            try:
                value = float(config.get(self.plugin_name, key, -1.0))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return float(self.DEFAULT_REFRESH_TIME or 60.0)

    async def _grab_stats(self) -> list:
        """Return the current scan results; relaunch the scanner if it is dead.

        NON-BLOCKING by construction (design §4): this coroutine never awaits
        the scan. `ThreadScanner.run()` sweeps the list in its own thread —
        including the accepted hardcoded `time.sleep(1)` between ICMP probes —
        and writes `status` / `elapsed` straight into the live dicts. Each
        cycle we simply publish a snapshot of whatever the scanner has produced
        so far; items not yet reached keep `status = None` and render as
        `Scanning`.

        This runs on the fast GLOBAL cadence (SCHEDULE_AT_GLOBAL_REFRESH), so
        the snapshot tracks the scan's progress within a couple of seconds —
        v4's live-list read. The heavy scan itself is throttled to
        `[ports] refresh`: a dead scanner is only relaunched once the scan
        timer has fired. The very first sweep launches unconditionally so real
        values appear immediately.

        The snapshot is a per-item COPY: the base pipeline replaces item dicts
        in `_remove_parameters()`, and the scanner must keep owning the
        originals.
        """
        if not self._scan_list:
            # Nothing configured — empty payload, no thread. Sweeping an empty
            # list every cycle would be pure waste.
            return []
        if self._thread is None or (not self._thread.is_alive() and self._scan_timer.finished()):
            self._thread = ThreadScanner(self._scan_list)
            self._thread.start()
            self._scan_timer.reset(self._scan_interval)
        return [dict(item) for item in self._scan_list]

    def stop(self) -> None:
        """Stop the background scanner (base teardown hook).

        The base `stop()` is synchronous; `AsyncScheduler.stop()` offloads it
        via `asyncio.to_thread`, so a blocking teardown here cannot stall the
        event loop (same contract as `containers`).
        """
        if self._thread is None:
            return
        try:
            self._thread.stop()
        except Exception as e:
            logger.warning("ports: stopping the scanner thread failed: %s", e)
        self._thread = None

    # ------------------------------------------------------------- levels
    #
    # BESPOKE, on purpose: `base_v5.py` is NOT modified by G6B (design §5.3).
    # `status` is a heterogeneous union whose level depends on the value's TYPE
    # as much as its magnitude, so neither the base's numeric ladder nor its
    # categorical mapping applies. A generic threshold hook was considered and
    # rejected as speculative — `ports` would be its only caller.

    @staticmethod
    def _port_level(item: dict[str, Any]) -> str:
        """Level for a port-scan item. Mirrors v4 `get_conds_if_port`.

        A healthy port (open, RTT within threshold) resolves to `"ok"`, NOT
        `None`: v4's `get_default_ret_value` returns `'OK'`, and `'OK'` is
        `COLOR_GREEN` in the curses colour map — the reachable-host value is
        painted green. Returning `None`/no-level here would drop it to the
        DEFAULT (uncoloured) role, which is the bug it used to have.
        """
        status = item.get("status")
        if status is None:
            return "careful"  # not scanned yet → rendered as `Scanning`
        # Resolve by severity, not by evaluation order (#3632): several
        # conditions can match at once and the most severe one has to win.
        # `False == 0` in Python: this single test covers both the ICMP
        # (`status = False`) and the TCP (`status = False`) timeout paths.
        if status == 0:
            return "critical"
        rtt_warning = item.get("rtt_warning")
        if isinstance(status, (int, float)) and rtt_warning is not None and status > rtt_warning:
            return "warning"
        return "ok"

    @staticmethod
    def _web_level(item: dict[str, Any]) -> str:
        """Level for a web item. Mirrors v4 `get_conds_if_url`, except that a
        `None` status resolves to `careful` instead of `critical` (design §5.3):
        v4's last-truthy-wins painted every URL red for the whole first refresh
        window, before any scan had run.

        A healthy URL (OK HTTP code, response within threshold) resolves to
        `"ok"` — v4's `'OK'` = green (see `_port_level`)."""
        status = item.get("status")
        if status is None:
            return "careful"  # not scanned yet → rendered as `Scanning`
        # Resolve by severity, not by evaluation order (#3632): a URL that is
        # BOTH failing and slow is critical, not warning.
        # Covers a bad HTTP code AND the literal string "Error" written by
        # `ThreadScanner._web_scan` when `requests` raises.
        if status not in PluginModel._WEB_OK_CODES:
            return "critical"
        rtt_warning = item.get("rtt_warning")
        elapsed = item.get("elapsed")
        if rtt_warning is not None and elapsed is not None and elapsed > rtt_warning:
            return "warning"
        return "ok"

    def _derived_parameters(self) -> None:
        """Compute `_levels` for both item kinds.

        This REPLACES the base implementation rather than extending it, so
        `status` is the only field that ever gets a level. Adding a
        `watched: True` field to `fields_description` would therefore be
        silently ineffective — wire it in here as well, or call the base
        first and merge.

        Shape (collection): `{indice: {"status": {"level": …, "prominent": False}}}`.
        Every scannable item gets an entry — including the healthy `"ok"`
        level, which the renderer paints green (v4's `'OK'` decoration). Only
        an item with neither `url` nor `host` is skipped (it cannot be scanned).
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            indice = item.get("indice")
            if indice is None:
                continue
            if "url" in item:
                level = self._web_level(item)
            elif "host" in item:
                level = self._port_level(item)
            else:
                continue
            # `prominent = False`: v4 colours the status text only, never the
            # background.
            self._levels[indice] = {"status": {"level": level, "prominent": False}}
