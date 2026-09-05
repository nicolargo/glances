#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Shell action (concrete `GlancesActionBase`).

Executes a command on alert. Migrates the v4 `_action` / `_action_repeat`
behaviour.

Config key suffixes (in any plugin section), with the 3-level precedence
resolved by `GlancesAlerts`:

- ``<level>_action``                              # any watched field, any item
- ``<level>_action_repeat``                       # idem, fires every cycle
- ``<field>_<level>_action[_repeat]``             # field-specific
- ``<key>_<field>_<level>_action[_repeat]``       # per-item (collection plugins)

The command line uses Mustache syntax (rendered by `chevron`) and is executed
by `secure_popen`, the same tokenizer as v4 and the AMPs.

Security — order of operations
------------------------------
`secure_popen` splits the command line into arguments **first**, then renders
each argument. The template comes from `glances.conf` and is trusted; the stat
values it interpolates (process names, container names, mount points, …) are
not. Because the argument boundaries are already fixed when a value is
expanded, that value can neither open nor close a quote, introduce whitespace
nor forge an operator: it always lands in exactly one argument
(GHSA-56xw-p9qm-r437).

Rendering first and lexing afterwards is what made every earlier mitigation on
this subsystem incomplete. Quoting the values before rendering does not work
either: chevron's default `{{var}}` syntax HTML-escapes `" < > &`, so it
rewrites the very quotes an escaper emits.

`--disable-config-exec` maps to `secure_popen(allow_operators=False)`: the
operators written in the operator's *own* `glances.conf` line (`&&`, `|`, `>`)
are then passed verbatim as literal arguments instead of being interpreted.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any, ClassVar

import chevron

from glances.actions_v5.action_base import GlancesActionBase
from glances.secure import secure_popen

logger = logging.getLogger(__name__)


class ShellAction(GlancesActionBase):
    """Run a command on alert."""

    action_name: ClassVar[str] = "action"
    # chevron is a core Glances dependency — no extra requires.
    requires: ClassVar[list[str]] = []

    def allow_operators(self) -> bool:
        """False when `--disable-config-exec` hardened config-driven execution.

        The command lines are read from the same `glances.conf` as the AMP
        commands, so an attacker able to edit that file could otherwise chain
        commands or write to an arbitrary file through a redirection
        (CVE-2026-68519, incomplete fix of CVE-2026-53925). Defaults to True:
        the flag is opt-in and the shipped behaviour is unchanged.
        """
        if self.config is None:
            return True
        return not self.config.get("global", "disable_config_exec", False)

    async def execute(
        self,
        plugin_name: str,
        level: str,
        context: dict[str, Any],
        action_value: str,
        repeat: bool = False,
    ) -> None:
        # `action_value` is handed over as the raw template: secure_popen
        # tokenizes it and only then expands each argument (see module
        # docstring). `secure_popen` is blocking, hence the thread handoff.
        try:
            ret = await asyncio.to_thread(
                secure_popen,
                action_value,
                allow_operators=self.allow_operators(),
                render=partial(chevron.render, data=context),
            )
        except chevron.ChevronError as e:
            # A Mustache section spanning two arguments cannot be rendered per
            # argument. Refuse to run rather than fall back to rendering the
            # whole line, which would reopen the injection.
            logger.warning(
                "Shell action: template render failed (plugin=%s, level=%s, template=%r): %s",
                plugin_name,
                level,
                action_value,
                e,
            )
            return
        except OSError as e:
            logger.warning(
                "Shell action: execution failed (plugin=%s, level=%s, template=%r): %s",
                plugin_name,
                level,
                action_value,
                e,
            )
            return

        # secure_popen returns the command output, or its stderr when the
        # command wrote any — the return code is not available through it.
        logger.debug(
            "Shell action: result (plugin=%s, level=%s, repeat=%s, template=%r): %s",
            plugin_name,
            level,
            repeat,
            action_value,
            ret,
        )
