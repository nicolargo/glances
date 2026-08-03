#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — AMP orchestrator.

Replaces v4's `glances/amps_list.py::AmpsList` (left untouched for the v4
runtime). The AMP-facing contract is unchanged — an AMP is still a
`GlancesAmp` subclass with a synchronous `update(process_list)` — so
third-party AMP scripts written for v4 keep working. What changes is the
orchestration around them:

- **Loading**: `importlib.import_module("glances.amps.<name>")` instead of
  `__import__` on a bare basename with `glances/amps/` injected into
  `sys.path`. No global import-path mutation, so an AMP named after a stdlib
  module (`[amp_email]`) no longer shadows it process-wide.
- **Registry**: an INSTANCE attribute. v4 keeps it on the class, so every
  `AmpsList` shares one dict for the process lifetime.
- **Matching**: each AMP's regex is compiled ONCE at load time instead of
  being re-parsed for every process on every cycle.
- **Execution**: `asyncio.to_thread`, launched only when the AMP's own
  `Timer` has fired AND no previous run is still in flight — v4 spawns an
  un-joined thread per AMP per cycle unconditionally, so a hung command
  leaks one thread every `refresh` seconds forever.

See docs/superpowers/specs/2026-08-02-glances-v5-g6c-amps-design.md.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from glances.processes import glances_processes

if TYPE_CHECKING:
    from glances.amps.amp import GlancesAmp
    from glances.config_v5 import GlancesConfigV5

logger = logging.getLogger(__name__)

_SECTION_PREFIX = "amp_"
_DEFAULT_MODULE = "glances.amps.default"


class AmpsListV5:
    """Load, schedule and run the configured AMPs."""

    def __init__(self, config: GlancesConfigV5) -> None:
        self.config = config

        # `GlancesAmp.allow_operators()` reads `args.disable_config_exec`, and
        # v5 hands plugins a config object, not an argparse namespace. Build the
        # minimal shim the frozen v4 contract expects. `main_v5` already
        # overlays this key onto `[global]` when `--disable-config-exec` is
        # passed (main_v5.py:386-392).
        self._args = SimpleNamespace(
            disable_config_exec=bool(config.get("global", "disable_config_exec", False)),
        )

        # INSTANCE attributes, all keyed by the config-section suffix
        # (`[amp_foo]` -> "foo"), which is NOT the display name (`Amp.NAME`).
        self._amps: dict[str, GlancesAmp] = {}
        self._regex: dict[str, re.Pattern[str]] = {}

        # Tasks currently running an AMP's `update()` in a worker thread,
        # keyed like `_amps`. Guarantees at most ONE run in flight per AMP.
        self._inflight: dict[str, asyncio.Task] = {}

        self._load()

    # ------------------------------------------------------------- loading

    def _load(self) -> None:
        for section in self.config.sections():
            if not section.startswith(_SECTION_PREFIX):
                continue
            name = section[len(_SECTION_PREFIX) :]
            amp = self._instantiate(name)
            if amp is None:
                continue
            # A single broken `[amp_*]` section must not abort construction of
            # the whole registry — v4's `AmpsList.load_configs` only guards the
            # import, not `load_config()` itself, so one bad section there
            # takes the rest of the list down with it.
            try:
                amp.load_config(self.config)
            except Exception as e:
                logger.warning("Cannot load configuration for AMP %s (%s)", name, e)
                continue
            self._amps[name] = amp
            self._compile_regex(name, amp)
        logger.debug("AMPs list: %s", list(self._amps))

    def _instantiate(self, name: str) -> GlancesAmp | None:
        """Import the AMP module for `name` and build its `Amp` instance.

        Falls back to the `default` AMP when no dedicated module exists —
        the documented behaviour for every `command=`-based AMP.
        """
        module = self._import_amp_module(name)
        if module is None:
            return None
        try:
            return module.Amp(name=name, args=self._args)
        except Exception as e:
            logger.warning("Cannot build AMP %s (%s)", name, e)
            return None

    def _import_amp_module(self, name: str) -> Any | None:
        """Return the module backing AMP `name`, or None to skip it entirely.

        A name that is not a valid Python identifier can never be a module,
        so it goes straight to the default AMP instead of producing a
        confusing import error.
        """
        module_name = f"glances.amps.{name}" if name.isidentifier() else None

        if module_name is not None:
            try:
                return importlib.import_module(module_name)
            except ModuleNotFoundError as e:
                if e.name != module_name:
                    # The AMP module exists but one of ITS imports is missing.
                    # v4 logs "Missing Python Lib" and skips the AMP — do not
                    # silently substitute the default AMP for it.
                    logger.warning("Missing Python lib (%s), cannot load AMP %s", e, name)
                    return None
                # No dedicated module for this AMP — fall through to default.
            except Exception as e:
                logger.warning("Cannot load AMP %s (%s)", name, e)
                return None

        try:
            return importlib.import_module(_DEFAULT_MODULE)
        except Exception as e:  # pragma: no cover — the default AMP ships with Glances
            logger.warning("Cannot load the default AMP module (%s)", e)
            return None

    def _compile_regex(self, name: str, amp: GlancesAmp) -> None:
        """Compile the AMP's regex once. No regex is a valid case (issue #1690).

        An invalid regex disables the AMP, mirroring how `load_config`
        disables an AMP that lacks the mandatory `refresh` key.
        """
        pattern = amp.regex()
        if pattern is None:
            return
        try:
            self._regex[name] = re.compile(pattern)
        except re.error as e:
            logger.warning("AMP %s: invalid regex %r (%s) — the AMP is disabled", name, pattern, e)
            amp.configs["enable"] = "false"

    # -------------------------------------------------------------- update

    async def update(self) -> list[GlancesAmp]:
        """Run one orchestration cycle and return every loaded AMP.

        Never awaits an AMP's own work: a due AMP is offloaded to a worker
        thread and this coroutine returns immediately with whatever results
        the AMPs have produced so far. Mirrors `AmpsList.update()` branch for
        branch, with two deliberate differences (design §5.2): the process
        count is computed inline instead of inside a spawned thread, and an
        AMP whose previous run is still in flight is skipped.
        """
        processlist = self._get_processlist()

        for name, amp in self._amps.items():
            if not amp.enable():
                continue

            pattern = self._regex.get(name)
            if pattern is None:
                # No regex configured: run every `refresh` seconds regardless
                # of any process, and never display a count (issue #1690).
                amp.set_count(0)
                self._maybe_run(name, amp, [])
                continue

            matching = self._match(pattern, processlist)
            amp.set_count(len(matching))

            if matching:
                self._maybe_run(name, amp, matching)
                continue

            # No match: v4 does NOT run the AMP on this branch. It only
            # surfaces the absence when the operator asked for a minimum.
            count_min = amp.count_min()
            if count_min is not None and count_min > 0:
                amp.set_result("No running process")

        return list(self._amps.values())

    def _get_processlist(self) -> list[dict[str, Any]]:
        """Read the shared process engine. Read-only — refreshing it is
        `processcount`'s job, exactly as in v4."""
        try:
            raw = glances_processes.get_list()
        except Exception as e:
            logger.debug("AMPS: cannot read the process list (%s)", e)
            return []
        return raw if isinstance(raw, list) else []

    @staticmethod
    def _match(pattern: re.Pattern[str], processlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Processes matching `pattern`, projected to what AMPs consume.

        Searches both `name` and the joined `cmdline` (kernel threads have no
        cmdline — see issue #1261). Returns an empty list when the process
        dicts are malformed; v4 raises `UnboundLocalError` there.
        """
        try:
            return [
                {"pid": p["pid"], "cpu_percent": p["cpu_percent"], "memory_percent": p["memory_percent"]}
                for p in processlist
                if pattern.search(p["name"]) or ((cmdline := p.get("cmdline")) and pattern.search(" ".join(cmdline)))
            ]
        except (TypeError, KeyError) as e:
            logger.debug("AMPS: cannot build the AMP process list (%s)", e)
            return []

    def _maybe_run(self, name: str, amp: GlancesAmp, matching: list[dict[str, Any]]) -> None:
        """Offload `amp.update(matching)` to a thread if it is due and idle.

        ORDER MATTERS: the in-flight check comes first because
        `should_update()` re-arms and resets the AMP's timer as a side effect
        (glances/amps/amp.py:168-179). Checking it first and then bailing out
        on the in-flight guard would silently consume that tick and double the
        AMP's effective period.

        `amp.update()` is called directly rather than `update_wrapper()`: the
        count and the timer are decided here now. `update()` is the method the
        AMP contract requires a script to implement; `update_wrapper()` is v4
        plumbing that no AMP overrides.
        """
        if name in self._inflight:
            logger.debug("AMP %s: previous run still in flight — skipping this cycle", name)
            return
        if not amp.should_update():
            return

        task = asyncio.create_task(asyncio.to_thread(amp.update, matching))
        self._inflight[name] = task
        task.add_done_callback(lambda t, n=name: self._on_run_done(n, t))

    def _on_run_done(self, name: str, task: asyncio.Task) -> None:
        self._inflight.pop(name, None)
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            logger.warning("AMP %s: update failed (%s)", name, exception)
