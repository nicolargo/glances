#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 alert actions package.

Concrete actions (shell, apprise, llm, …) live as sub-packages
(`glances/actions_v5/<name>/__init__.py`) and are auto-discovered at
startup via `discover_actions()`. Phase 0 ships the base class and the
discovery mechanism only — concrete actions land alongside `GlancesAlerts`
in Phase 1.
"""

from glances.actions_v5.action_base import GlancesActionBase, discover_actions

__all__ = ["GlancesActionBase", "discover_actions"]
