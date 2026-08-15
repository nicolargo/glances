#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the stdout CSV output (--stdout-csv).

Regression tests for issue #3606: when a list-type plugin (e.g. network) gains or
loses items - or an item reappears with a reduced field set (rate fields are not
computed on an interface's first sample) - the data rows must stay aligned with the
header built on the first refresh.
"""

from glances.outputs.glances_stdout_csv import GlancesStdoutCsv


def _make_csv():
    """Return a GlancesStdoutCsv instance without going through __init__."""
    csv = GlancesStdoutCsv.__new__(GlancesStdoutCsv)
    csv.separator = ','
    csv.na = 'N/A'
    csv.header = True
    csv.list_keys = {}
    csv.header_field_names = {}
    return csv


def _iface_full(name, sent, recv):
    """An interface with the full field set (rate/gauge fields present)."""
    return {
        'interface_name': name,
        'key': 'interface_name',
        'bytes_sent': sent,
        'bytes_recv': recv,
        'speed': 1000,
        'alias': None,
        'bytes_all': sent + recv,
        'time_since_update': 2.0,
        'bytes_recv_gauge': recv * 10,
        'bytes_recv_rate_per_sec': float(recv),
        'bytes_sent_gauge': sent * 10,
        'bytes_sent_rate_per_sec': float(sent),
        'bytes_all_gauge': (sent + recv) * 10,
        'bytes_all_rate_per_sec': float(sent + recv),
    }


def _iface_partial(name, sent, recv):
    """An interface on its first sample: rate/gauge fields not computed yet."""
    return {
        'interface_name': name,
        'key': 'interface_name',
        'bytes_sent': sent,
        'bytes_recv': recv,
        'speed': 1000,
        'alias': None,
        'bytes_all': sent + recv,
    }


def _ncols(line):
    stripped = line.rstrip(',')
    return len(stripped.split(',')) if stripped else 0


def test_list_plugin_steady_state():
    """Rows match the header when the interface set is unchanged."""
    csv = _make_csv()
    stat = [_iface_full('eth0', 1, 2), _iface_full('wlan0', 3, 4)]
    header = csv.build_header('network', None, stat)
    data = csv.build_data('network', None, stat)
    assert _ncols(data) == _ncols(header)


def test_list_plugin_interface_removed():
    """A removed interface is N/A-filled so the row stays aligned."""
    csv = _make_csv()
    start = [_iface_full('eth0', 1, 2), _iface_full('wlan0', 3, 4)]
    header = csv.build_header('network', None, start)
    data = csv.build_data('network', None, [_iface_full('eth0', 5, 6)])
    assert _ncols(data) == _ncols(header)
    assert 'N/A' in data


def test_list_plugin_interface_reappears_with_partial_fields():
    """An interface back on its first sample (missing rate fields) is N/A-padded per field."""
    csv = _make_csv()
    start = [_iface_full('eth0', 1, 2), _iface_full('wlan0', 3, 4)]
    header = csv.build_header('network', None, start)
    # wlan0 returns with only the non-rate fields present
    data = csv.build_data('network', None, [_iface_full('eth0', 5, 6), _iface_partial('wlan0', 7, 8)])
    assert _ncols(data) == _ncols(header)
    # the 7 missing wlan0 fields become N/A
    assert data.count('N/A') == 7


def test_list_plugin_interface_added_is_omitted():
    """An interface appearing after export start has no column and is omitted."""
    csv = _make_csv()
    start = [_iface_full('eth0', 1, 2), _iface_full('wlan0', 3, 4)]
    header = csv.build_header('network', None, start)
    data = csv.build_data(
        'network',
        None,
        [_iface_full('eth0', 7, 8), _iface_full('ppp0', 9, 9), _iface_full('wlan0', 10, 11)],
    )
    assert _ncols(data) == _ncols(header)
    assert 'ppp0' not in data


def test_list_plugin_added_keeps_existing_aligned():
    """When a new interface shifts the live order, existing ones stay under their columns."""
    csv = _make_csv()
    start = [_iface_full('eth0', 1, 2), _iface_full('wlan0', 3, 4)]
    csv.build_header('network', None, start)
    data = csv.build_data(
        'network',
        None,
        [_iface_full('eth0', 7, 8), _iface_full('ppp0', 9, 9), _iface_full('wlan0', 10, 11)],
    )
    cells = data.rstrip(',').split(',')
    # wlan0's current bytes_sent (10) must appear under wlan0's block, not eth0's
    assert '10' in cells


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
