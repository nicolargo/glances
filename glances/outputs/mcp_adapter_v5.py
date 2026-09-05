#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 → MCP duck-typed adapter (G3-MCP Task 1).

Bridges v5's lockless ``StatsStoreV5`` + plugin registry + alerts
pipeline to the v4-``GlancesStats``-style surface consumed by
``glances.outputs.glances_mcp.GlancesMcpServer``.

Why an adapter and not a rewrite: the MCP server class is already
production-tested in v4; reusing it as-is (with a thin facade) is
cheaper than re-implementing every resource/prompt against v5 native
APIs. The MCP module stays untouched.

V5 limitations exposed by this adapter (all explicit, not silent):

- **History is not stored in v5 yet.** ``McpPluginView.get_raw_history``
  returns ``{}`` and logs a WARNING (throttled — one per plugin) so
  the MCP client sees an empty dataset rather than a crash.
- **Plugins not yet ported to v5** are tracked in
  ``KNOWN_V5_MISSING_PLUGINS`` below — empty as of G4-processlist (every
  v4 plugin has a v5 model). Whenever a v4-only plugin is reintroduced,
  add it back to that tuple: ``get_plugin("<unported>")`` will then
  return ``None`` and the MCP server raises its canonical
  ``ValueError("Plugin '<x>' not found")`` — matching v4 behaviour when
  a plugin is disabled.
- **Alert schema is v5-native** (``ts`` / ``plugin`` / ``key`` /
  ``field`` / ``level`` / ``previous_level`` / ``prominent``) — no
  translation to v4's flatter ``type`` / ``start`` / ``end`` shape.
  Documented in the G3-MCP plan, "Decision log".

See ``docs/superpowers/plans/2026-05-15-glances-v5-phase2-g3-mcp.md``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from glances.alerts_v5 import GlancesAlerts
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

# v4 plugins that the v5 MCP adapter does not yet expose because the
# underlying plugin is not ported yet. ``get_plugin(name)`` returns
# ``None`` for each of these → ``GlancesMcpServer`` raises its canonical
# ``ValueError("Plugin '<x>' not found")`` to the MCP client. Surfaced at
# ``attach_mcp`` startup so operators know which resources will fail.
# Update this list as v5 absorbs v4 plugins; the adapter logic itself
# does not need to change.
KNOWN_V5_MISSING_PLUGINS: tuple[str, ...] = ()

# Throttle the "history not supported" WARN so polling MCP clients don't
# spam the log. Tracked per plugin name (including the synthetic 'alert')
# and persists for the process lifetime.
_HISTORY_WARN_SEEN: set[str] = set()


class McpPluginView:
    """v4-``GlancesPlugin``-like facade for one plugin's stats.

    Three concrete entry points are consumed by ``GlancesMcpServer``:
    ``get_raw()``, ``get_raw_history(item=None, nb=0)`` and
    ``get_limits()``.
    """

    def __init__(
        self,
        plugin_name: str,
        synthetic_payload: Any | None = None,
        plugin: GlancesPluginBase | None = None,
    ) -> None:
        self._plugin_name = plugin_name
        self._synthetic_payload = synthetic_payload
        self._plugin = plugin

    def get_raw(self) -> dict[str, Any] | list[dict[str, Any]]:
        """Return the latest payload for this plugin.

        Read through the plugin's filtered view, not the store: an MCP client
        is a consumer like any other, and leaving it on the raw payload would
        recreate the very inconsistency issue #3211 is about — fields declared
        ``exportable: False`` reaching a client that the exporters correctly
        withhold them from.

        Synthetic plugins (e.g. ``alert``) have no backing plugin and return a
        caller-supplied payload (an alerts list in that case).
        """
        if self._synthetic_payload is not None:
            return self._synthetic_payload() if callable(self._synthetic_payload) else self._synthetic_payload
        if self._plugin is None:
            return {}
        return self._plugin.get_api_payload()

    def get_raw_history(self, item: str | None = None, nb: int = 0) -> dict[str, list[Any]] | list:
        """Return time-series history — **empty in v5** (see module docstring).

        The MCP resource ``glances://stats/{plugin}/history`` still
        succeeds: the client receives an empty mapping instead of an
        error. A WARN is logged once per plugin to make the limitation
        visible without spamming.
        """
        if self._plugin_name not in _HISTORY_WARN_SEEN:
            logger.warning(
                "MCP history not yet supported in v5; returning empty dataset for '%s'.",
                self._plugin_name,
            )
            _HISTORY_WARN_SEEN.add(self._plugin_name)
        return {}

    def get_limits(self) -> dict[str, Any]:
        """Return the plugin's **effective** thresholds.

        Delegates to ``GlancesPluginBase.get_limits()`` so that MCP and the
        REST ``/api/5/<plugin>/limits`` route share one source of truth.
        This class previously aggregated ``default_thresholds`` straight
        from the field schema, which ignored the operator's config — the
        ``glances://limits`` resource reported shipped defaults even when a
        threshold had been overridden.

        Synthetic plugins (``alert``) have no backing plugin object and
        carry no thresholds.
        """
        if self._plugin is None:
            return {}
        return self._plugin.get_limits()


class McpStatsAdapter:
    """v4-``GlancesStats``-shape facade over v5 components.

    Exposes the four entry points that ``GlancesMcpServer`` consumes:
    ``getPluginsList`` / ``getAllAsDict`` / ``getAllLimitsAsDict`` /
    ``get_plugin(name)``.

    The synthetic ``"alert"`` plugin is added on top of the real
    registry so the v4 MCP prompt ``alert_analysis`` continues to work.
    """

    SYNTHETIC_PLUGIN_NAMES: tuple[str, ...] = ("alert",)

    def __init__(
        self,
        plugins: list[GlancesPluginBase],
        alerts: GlancesAlerts | None = None,
    ) -> None:
        # No store reference on purpose: since issue #3211 every payload this
        # facade serves comes from the plugin's own filtered view.
        self._alerts = alerts
        self._by_name: dict[str, GlancesPluginBase] = {p.plugin_name: p for p in plugins}

    # ------------------------------------------------------------------ public surface

    def getPluginsList(self) -> list[str]:  # noqa: N802 — matches v4 GlancesStats API
        """Return registered plugin names plus the synthetic ones."""
        return list(self._by_name.keys()) + list(self.SYNTHETIC_PLUGIN_NAMES)

    def getAllAsDict(self) -> dict[str, Any]:  # noqa: N802
        """Return a snapshot of every plugin's filtered payload (issue #3211)."""
        return {name: plugin.get_api_payload() for name, plugin in self._by_name.items()}

    def getAllLimitsAsDict(self) -> dict[str, dict[str, Any]]:  # noqa: N802
        """Aggregate thresholds across every real plugin.

        Synthetic plugins (``alert``) carry no thresholds and are
        therefore omitted.
        """
        out: dict[str, dict[str, Any]] = {}
        for name, plugin in self._by_name.items():
            view = McpPluginView(plugin_name=name, plugin=plugin)
            limits = view.get_limits()
            if limits:
                out[name] = limits
        return out

    def get_plugin(self, name: str) -> McpPluginView | None:
        """Return a plugin view, or ``None`` for an unknown plugin name.

        ``GlancesMcpServer`` translates ``None`` into a
        ``ValueError("Plugin '<x>' not found")`` raised back to the MCP
        client — same shape as v4 when a plugin is disabled.
        """
        if not name:
            return None
        if name == "alert":
            return McpPluginView(plugin_name="alert", synthetic_payload=self._alerts_payload)
        plugin = self._by_name.get(name)
        if plugin is None:
            return None
        return McpPluginView(plugin_name=name, plugin=plugin)

    # ------------------------------------------------------------------ internals

    def _alerts_payload(self) -> list[dict[str, Any]]:
        """Return ``GlancesAlerts.get_history()`` or an empty list if no alerts pipeline."""
        if self._alerts is None:
            return []
        return self._alerts.get_history()
