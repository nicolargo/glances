#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the threshold engine (pure functions).

Test stack: pytest-native (architecture decisions §9). No I/O.
"""

from __future__ import annotations

from typing import Any

import pytest

from glances.plugins.plugin.thresholds_v5 import compute_level, read_thresholds

# ---------------------------------------------------------- compute_level

THRESHOLDS_HIGH = {"careful": 50.0, "warning": 70.0, "critical": 90.0}
THRESHOLDS_LOW = {"careful": 20.0, "warning": 10.0, "critical": 5.0}


@pytest.mark.parametrize(
    "value, expected",
    [
        (10.0, "ok"),
        (49.99, "ok"),
        (50.0, "careful"),
        (60.0, "careful"),
        (70.0, "warning"),
        (89.0, "warning"),
        (90.0, "critical"),
        (100.0, "critical"),
    ],
)
def test_compute_level_high_direction(value, expected):
    assert compute_level(value, THRESHOLDS_HIGH, "high") == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (50.0, "ok"),
        (21.0, "ok"),
        (20.0, "careful"),
        (15.0, "careful"),
        (10.0, "warning"),
        (6.0, "warning"),
        (5.0, "critical"),
        (0.0, "critical"),
    ],
)
def test_compute_level_low_direction(value, expected):
    assert compute_level(value, THRESHOLDS_LOW, "low") == expected


def test_compute_level_none_value_returns_ok():
    assert compute_level(None, THRESHOLDS_HIGH, "high") == "ok"


def test_compute_level_empty_thresholds_returns_ok():
    assert compute_level(99.0, {}, "high") == "ok"


def test_compute_level_partial_thresholds_walks_severity_descending():
    # Only `warning` is configured. value=80 is at warning, value=50 is ok.
    partial = {"warning": 70.0}
    assert compute_level(80.0, partial, "high") == "warning"
    assert compute_level(60.0, partial, "high") == "ok"


def test_compute_level_int_value_accepted():
    # Int inputs flow through (no float coercion required).
    assert compute_level(75, THRESHOLDS_HIGH, "high") == "warning"


# ---------------------------------------------------------- read_thresholds


class FakeConfig:
    """Minimal stand-in for GlancesConfigV5.get used by `read_thresholds`."""

    def __init__(self, mapping: dict[tuple[str, str], Any]):
        self._mapping = mapping

    def get(self, section: str, option: str, default: Any) -> Any:
        return self._mapping.get((section, option), default)


def test_read_thresholds_no_config_no_defaults_returns_empty():
    config = FakeConfig({})
    assert read_thresholds(config, "mem", "percent") == {}


def test_read_thresholds_uses_defaults_when_config_silent():
    config = FakeConfig({})
    defaults = {"careful": 50.0, "warning": 70.0, "critical": 90.0}
    assert read_thresholds(config, "mem", "percent", defaults=defaults) == defaults


def test_read_thresholds_bare_keys_override_defaults():
    config = FakeConfig({("mem", "critical"): "85"})
    defaults = {"careful": 50.0, "warning": 70.0, "critical": 90.0}
    out = read_thresholds(config, "mem", "percent", defaults=defaults)
    assert out == {"careful": 50.0, "warning": 70.0, "critical": 85.0}


def test_read_thresholds_field_prefixed_keys_take_priority_over_bare():
    config = FakeConfig({("mem", "warning"): "60", ("mem", "percent_warning"): "65"})
    out = read_thresholds(config, "mem", "percent")
    assert out == {"warning": 65.0}


def test_read_thresholds_falls_back_to_bare_when_field_prefixed_missing():
    config = FakeConfig({("load", "warning"): "1.5"})
    out = read_thresholds(config, "load", "min1")
    assert out == {"warning": 1.5}


def test_read_thresholds_no_field_argument_only_bare_keys():
    config = FakeConfig({("mem", "warning"): "60", ("mem", "percent_warning"): "65"})
    # field=None → field-prefixed keys are ignored.
    out = read_thresholds(config, "mem", field=None)
    assert out == {"warning": 60.0}


def test_read_thresholds_negative_value_treated_as_disabled():
    # Per the docstring contract, a negative threshold disables that level —
    # the helper sees the sentinel and falls back to the default if any.
    config = FakeConfig({("mem", "critical"): "-1"})
    defaults = {"warning": 70.0, "critical": 90.0}
    out = read_thresholds(config, "mem", "percent", defaults=defaults)
    # critical is disabled in the config, so the default applies. Bare-key
    # match found nothing meaningful, the default carries.
    # Implementation note: a negative value is *ignored* (not retained).
    assert out["critical"] == 90.0
    assert out["warning"] == 70.0


def test_read_thresholds_non_numeric_value_is_skipped():
    config = FakeConfig({("mem", "critical"): "not-a-number"})
    defaults = {"critical": 90.0}
    out = read_thresholds(config, "mem", "percent", defaults=defaults)
    assert out == {"critical": 90.0}


def test_read_thresholds_per_level_layering():
    # User overrides only `critical`; the others come from defaults.
    config = FakeConfig({("mem", "critical"): "95"})
    defaults = {"careful": 50.0, "warning": 70.0, "critical": 90.0}
    out = read_thresholds(config, "mem", "percent", defaults=defaults)
    assert out == {"careful": 50.0, "warning": 70.0, "critical": 95.0}
