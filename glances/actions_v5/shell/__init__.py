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

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
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
