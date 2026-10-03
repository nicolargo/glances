#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — schema completeness of every plugin's ``fields_description``.

Replaces the per-plugin v4 ``test_field_has_description`` /
``test_field_has_unit`` tests (mem, memswap, load, cpu, processcount).
"""

from __future__ import annotations

import pytest

from glances.main_v5 import discover_plugin_classes

_PLUGIN_CLASSES = [cls for _, cls in discover_plugin_classes()]


@pytest.mark.parametrize("cls", _PLUGIN_CLASSES, ids=[cls.plugin_name for cls in _PLUGIN_CLASSES])
def test_every_field_has_a_description_and_a_unit(cls):
    assert cls.fields_description
    for field, spec in cls.fields_description.items():
        assert spec.get("description"), f"{cls.plugin_name}.{field} has no description"
        assert "unit" in spec, f"{cls.plugin_name}.{field} has no unit key"
