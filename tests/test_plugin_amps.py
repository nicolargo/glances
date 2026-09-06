#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Glances contributors
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the AMPs plugin."""

from argparse import Namespace
from types import SimpleNamespace

import pytest

from glances.exports.export import GlancesExport
from glances.plugins.amps import AmpsPlugin


def _amp(result):
    return SimpleNamespace(
        NAME='Test',
        result=lambda: result,
        refresh=lambda: 30,
        time_until_refresh=lambda: 10,
        count=lambda: 0,
        count_min=lambda: None,
        count_max=lambda: None,
        regex=lambda: None,
    )


@pytest.mark.parametrize(
    ('result', 'result_float'),
    [
        ('12.5', 12.5),
        ('0', 0.0),
        ('service is healthy', None),
        ('12\n13', None),
        (None, None),
    ],
)
def test_amp_result_has_a_type_stable_numeric_field(result, result_float):
    args = Namespace(disable_amps=False, disable_history=True)
    plugin = AmpsPlugin(args=args, config=None)
    plugin.glances_amps = SimpleNamespace(update=lambda: {'test': _amp(result)})

    [stats] = plugin.update()

    assert stats['result'] == result
    assert stats['result_float'] == result_float
    assert 'result_float' in plugin.fields_description


def test_numeric_amp_result_keeps_separate_influxdb_types():
    args = Namespace(disable_amps=False, disable_history=True)
    plugin = AmpsPlugin(args=args, config=None)
    plugin.glances_amps = SimpleNamespace(update=lambda: {'test': _amp('12.5')})
    [stats] = plugin.update()
    exporter = GlancesExport()
    exporter.tags = ''
    exporter.hostname = 'test-host'

    [point] = exporter.normalize_for_influxdb('amps', list(stats), list(stats.values()))

    assert point['fields']['result'] == '12.5'
    assert point['fields']['result_float'] == 12.5
