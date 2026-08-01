#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Shell action (concrete `GlancesActionBase`).

Executes a shell command on alert. Migrates the v4 `_action` /
`_action_repeat` behaviour.

Config key suffixes (in any plugin section), with the 3-level precedence
resolved by `GlancesAlerts`:

- ``<level>_action``                              # any watched field, any item
- ``<level>_action_repeat``                       # idem, fires every cycle
- ``<field>_<level>_action[_repeat]``             # field-specific
- ``<key>_<field>_<level>_action[_repeat]``       # per-item (collection plugins)

The template uses Mustache syntax (rendered by `chevron`). Context
values are **shell-quoted with `shlex.quote()` before substitution** so
that user-influenced metric strings (process names, container names,
interface names, …) cannot inject shell commands — CVE-2026-32608.

`--disable-config-exec` (CVE-2026-68519) additionally drops the shell
altogether: the rendered command is split with `shlex.split()` and run as
a single process, so the shell operators written in the operator's *own*
`glances.conf` line (`&&`, `|`, `>`, …) are never interpreted. This
mirrors v4 `secure_popen(..., allow_operators=False)`.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
from typing import Any, ClassVar

import chevron

from glances.actions_v5.action_base import GlancesActionBase

logger = logging.getLogger(__name__)


class ShellAction(GlancesActionBase):
    """Run a shell command on alert."""

    action_name: ClassVar[str] = "action"
    # chevron is a core Glances dependency — no extra requires.
    requires: ClassVar[list[str]] = []

    def allow_shell(self) -> bool:
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
        # Pre-quote every context value so that interpolation produces
        # shell-safe text. Numbers and simple identifiers pass through
        # unchanged; strings with metacharacters get single-quoted.
        safe_context = {key: shlex.quote(str(value)) for key, value in context.items()}

        try:
            command = chevron.render(action_value, safe_context)
        except Exception as e:
            logger.warning(
                "Shell action: template render failed (plugin=%s, level=%s, template=%r): %s",
                plugin_name,
                level,
                action_value,
                e,
            )
            return

        allow_shell = self.allow_shell()
        if not allow_shell:
            try:
                argv = shlex.split(command)
            except ValueError as e:
                logger.warning(
                    "Shell action: command cannot be split (plugin=%s, level=%s, command=%r): %s",
                    plugin_name,
                    level,
                    command,
                    e,
                )
                return
            if not argv:
                return

        try:
            if allow_shell:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            _, stderr = await proc.communicate()
        except Exception as e:
            logger.warning(
                "Shell action: execution failed (plugin=%s, level=%s, command=%r): %s",
                plugin_name,
                level,
                command,
                e,
            )
            return

        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace").strip()
            logger.warning(
                "Shell action: non-zero exit (plugin=%s, level=%s, repeat=%s, command=%r, returncode=%d, stderr=%s)",
                plugin_name,
                level,
                repeat,
                command,
                proc.returncode,
                err_text,
            )
