#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 alert action base class and auto-discovery.

Architecture references:
- §3.4    GlancesAlerts (consumer of actions, lands in Phase 1)
- §3.4.1  Action system architecture (this module)

Adding a new action type means dropping one file in
`glances/actions_v5/<name>/__init__.py` with a class inheriting
`GlancesActionBase`. No changes to any core module — actions are
auto-discovered.

Concrete actions (`shell`, `apprise`, `llm`, …) ship in Phase 1 alongside
`GlancesAlerts`, which is the only caller of `execute()`. Phase 0 ships
the base class and the discovery mechanism only.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import pkgutil
from abc import ABC, abstractmethod
from typing import ClassVar

logger = logging.getLogger(__name__)


class GlancesActionBase(ABC):
    """Abstract base class for all Glances v5 alert actions."""

    action_name: ClassVar[str] = ""
    """Suffix used in `glances.conf` keys: `<level>_<action_name>[_repeat]`."""

    requires: ClassVar[list[str]] = []
    """Optional Python module names this action depends on. Missing modules
    cause `is_available()` to return False and the action to be skipped at
    discovery time (with a WARNING log) — Glances always starts."""

    def __init__(self) -> None:
        if not self.action_name:
            raise ValueError(f"{type(self).__name__} must declare a non-empty action_name")

    def is_available(self) -> bool:
        """True iff every module listed in `requires` is importable.

        Probed via `importlib.util.find_spec` — no side effect, no actual
        import. Concrete actions that need to import their deps do so lazily
        in `execute()`.
        """
        for module_name in self.requires:
            if importlib.util.find_spec(module_name) is None:
                return False
        return True

    @abstractmethod
    async def execute(
        self,
        plugin_name: str,
        level: str,
        context: dict,
        action_value: str,
        repeat: bool = False,
    ) -> None:
        """Run the action.

        Parameters
        ----------
        plugin_name : str
            Name of the plugin that triggered the alert (`mem`, `fs`, …).
        level : str
            Alert level: `careful`, `warning`, or `critical`.
        context : dict
            Mustache rendering context: `plugin.get_export()` output plus
            built-in variables (`_glances_hostname`, `_glances_plugin`,
            `_glances_level`, `_glances_timestamp`).
        action_value : str
            Raw value from `glances.conf` (e.g. shell command template,
            apprise URL, `true`, …).
        repeat : bool
            True when the config key carries the `_repeat` suffix and the
            alert is still active on this refresh cycle. False on alert
            entry.
        """


def discover_actions(package: str = "glances.actions_v5") -> dict[str, GlancesActionBase]:
    """Walk `package`, instantiate every concrete `GlancesActionBase` subclass.

    Returns a `{action_name: instance}` registry. Modules whose import fails
    are logged at WARNING and skipped — Glances always starts. Subclasses
    whose `is_available()` is False are also logged and skipped.

    Raises `ValueError` on duplicate `action_name` to surface contributor
    mistakes loudly at startup.
    """
    pkg = importlib.import_module(package)
    if not hasattr(pkg, "__path__"):
        raise ValueError(f"{package!r} is not a package (no __path__)")

    registry: dict[str, GlancesActionBase] = {}

    for module_info in pkgutil.iter_modules(pkg.__path__, prefix=f"{package}."):
        # Skip the action_base module itself — it only defines the abstract class.
        if module_info.name == f"{package}.action_base":
            continue
        try:
            module = importlib.import_module(module_info.name)
        except Exception as e:
            logger.warning("Skipping action module %s: import failed (%s)", module_info.name, e)
            continue

        for attr_name in dir(module):
            cls = getattr(module, attr_name)
            if not isinstance(cls, type):
                continue
            if not issubclass(cls, GlancesActionBase) or cls is GlancesActionBase:
                continue
            # Filter out classes re-exported from elsewhere (only register
            # classes actually defined in this module).
            if cls.__module__ != module_info.name:
                continue

            try:
                instance = cls()
            except Exception as e:
                logger.warning("Skipping action %s: instantiation failed (%s)", cls.__name__, e)
                continue

            if not instance.is_available():
                logger.warning(
                    "Skipping action %r: missing dependencies %s",
                    instance.action_name,
                    instance.requires,
                )
                continue

            if instance.action_name in registry:
                raise ValueError(
                    f"Duplicate action_name {instance.action_name!r} "
                    f"({type(registry[instance.action_name]).__name__} vs {cls.__name__})"
                )
            registry[instance.action_name] = instance

    return registry
