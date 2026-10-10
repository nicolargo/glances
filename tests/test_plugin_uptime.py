# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""Tests for the Uptime plugin."""

from types import SimpleNamespace
from unittest import mock

from glances.plugins.uptime import UptimePlugin


def test_snmp_uptime_is_exported_in_seconds():
    plugin = UptimePlugin(args=SimpleNamespace(disable_uptime=False, disable_history=True))
    plugin.input_method = 'snmp'

    # sysUpTime is in hundredths of seconds: 1 day, 2 hours, 3 minutes and 4 seconds
    with mock.patch.object(plugin, 'get_stats_snmp', return_value={'_uptime': '9378400'}):
        plugin.update()

    assert plugin.get_raw() == '1 day, 2:03:04'
    assert plugin.get_export() == {'seconds': 93784}
