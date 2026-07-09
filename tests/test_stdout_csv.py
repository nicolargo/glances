#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the stdout CSV output (--stdout-csv).

Regression tests for the case where a list-type plugin (e.g. network) gains or
loses items between refreshes, which previously desynchronised the data rows
from the header (see issue #3606).
"""

from glances.outputs.glances_stdout_csv import GlancesStdoutCsv


def _make_csv():
    """Return a GlancesStdoutCsv instance without going through __init__."""
    csv = GlancesStdoutCsv.__new__(GlancesStdoutCsv)
    csv.separator = ','
    csv.na = 'N/A'
    csv.header = True
    csv.list_keys = {}
    csv.header_field_counts = {}
    return csv


def _iface(name, sent, recv):
    return {'interface_name': name, 'key': 'interface_name', 'bytes_sent': sent, 'bytes_recv': recv}


def _ncols(line):
    stripped = line.rstrip(',')
    return len(stripped.split(',')) if stripped else 0


def test_list_plugin_steady_state():
    """Rows match the header when the interface set is unchanged."""
    csv = _make_csv()
    stat = [_iface('eth0', 1, 2), _iface('wlan0', 3, 4)]
    header = csv.build_header('network', None, stat)
    data = csv.build_data('network', None, stat)
    assert _ncols(data) == _ncols(header)


def test_list_plugin_interface_removed():
    """A removed interface is N/A-filled so the row stays aligned."""
    csv = _make_csv()
    start = [_iface('eth0', 1, 2), _iface('wlan0', 3, 4)]
    header = csv.build_header('network', None, start)
    removed = [_iface('eth0', 5, 6)]  # wlan0 gone
    data = csv.build_data('network', None, removed)
    assert _ncols(data) == _ncols(header)
    assert 'N/A' in data  # missing interface padded


def test_list_plugin_interface_added_is_omitted():
    """An interface appearing after export start has no column and is omitted."""
    csv = _make_csv()
    start = [_iface('eth0', 1, 2), _iface('wlan0', 3, 4)]
    header = csv.build_header('network', None, start)
    added = [_iface('eth0', 7, 8), _iface('ppp0', 9, 9), _iface('wlan0', 10, 11)]
    data = csv.build_data('network', None, added)
    assert _ncols(data) == _ncols(header)
    assert 'ppp0' not in data  # new interface omitted, not shifted in


def test_list_plugin_added_keeps_existing_aligned():
    """When a new interface shifts the live order, existing ones stay under their columns."""
    csv = _make_csv()
    start = [_iface('eth0', 1, 2), _iface('wlan0', 3, 4)]
    csv.build_header('network', None, start)
    added = [_iface('eth0', 7, 8), _iface('ppp0', 9, 9), _iface('wlan0', 10, 11)]
    data = csv.build_data('network', None, added)
    cells = data.rstrip(',').split(',')
    # wlan0's current values (10, 11) must land in wlan0's columns (last two)
    assert cells[-2:] == ['10', '11']


def test_dict_plugin_unaffected():
    """Non-list plugins (dict) are unchanged by the fix."""
    csv = _make_csv()
    cpu = {'user': 1.2, 'system': 0.8, 'idle': 98.0}
    header = csv.build_header('cpu', None, cpu)
    data = csv.build_data('cpu', None, cpu)
    assert _ncols(data) == _ncols(header) == 3


def test_attribute_selector_unaffected():
    """A plugin.attribute selector still yields a single aligned column."""
    csv = _make_csv()
    cpu = {'user': 1.2, 'system': 0.8, 'idle': 98.0}
    header = csv.build_header('cpu', 'user', cpu)
    data = csv.build_data('cpu', 'user', cpu)
    assert _ncols(data) == _ncols(header) == 1
