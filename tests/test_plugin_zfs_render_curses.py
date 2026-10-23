#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 ZFS curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer import LEFT_SLOT, slot_for
from glances.plugins.zfs.model import PluginModel
from glances.plugins.zfs.render_curses import _LEFT_SIDEBAR_MAX_WIDTH, _status_text, render

_SCHEMA = PluginModel.fields_description


def _pool(name='tank', state='ONLINE', capacity=10, fragmentation=5, errors=0, status='', datasets=None):
    return {
        'name': name,
        'guid': '1',
        'state': state,
        'health': state,
        'size': 1000,
        'allocated': 100,
        'free': 900,
        'capacity': capacity,
        'fragmentation': fragmentation,
        'read_errors': errors,
        'write_errors': 0,
        'checksum_errors': 0,
        'error_count': 0,
        'status': status,
        'scan_function': '',
        'scan_state': '',
        'scan_errors': 0,
        'scan_progress': 0,
        'vdevs': [],
        'datasets': datasets or [],
    }


def _payload(rows, levels=None, show_datasets=False):
    return {'data': rows, 'show_datasets': show_datasets, '_levels': levels or {}}


def _cell(text, *, color='default', prominent=False, bold=False):
    return {'text': text, 'color': color, 'prominent': prominent, 'bold': bold}


def _row(*cells, item_start=False):
    return {'item_start': item_start, 'cells': list(cells)}


def _snapshot(rows):
    return [
        {
            'item_start': row.item_start,
            'cells': [
                {
                    'text': cell.text,
                    'color': cell.color.value,
                    'prominent': cell.prominent,
                    'bold': cell.bold,
                }
                for cell in row.cells
            ],
        }
        for row in rows
    ]


def _header():
    return _row(
        _cell('POOL      ', color='header', bold=True),
        _cell('   STATE', color='header', bold=True),
        _cell(' CAP', color='header', bold=True),
        _cell('FRAG', color='header', bold=True),
        _cell('ERR', color='header', bold=True),
    )


def _pool_row(
    *,
    name='tank      ',
    state='  ONLINE',
    state_color='default',
    capacity=' 10%',
    fragmentation='  5%',
    errors='  0',
    error_color='default',
):
    return _row(
        _cell(name),
        _cell(state, color=state_color),
        _cell(capacity),
        _cell(fragmentation),
        _cell(errors, color=error_color),
        item_start=True,
    )


def _status_row(text):
    return _row(_cell(text, color='warning'))


def test_registered_in_left_slot():
    assert ('zfs' in LEFT_SLOT, slot_for('zfs')) == (True, 'left')  # nosec B101


def test_empty_collection_renders_nothing():
    assert (render(_payload([]), _SCHEMA), render({}, _SCHEMA), render(None, _SCHEMA)) == ([], [], [])  # nosec B101


def test_header_and_pool_row():
    assert _snapshot(render(_payload([_pool()]), _SCHEMA)) == [_header(), _pool_row()]  # nosec B101


def test_width_budget():
    rows = render(_payload([_pool(name='a-very-long-pool-name')]), _SCHEMA)
    assert all(len(' '.join(cell.text for cell in row.cells)) <= _LEFT_SIDEBAR_MAX_WIDTH for row in rows)  # nosec B101


def test_state_level_colours_the_state_cell():
    levels = {'tank': {'state': {'level': 'critical', 'prominent': False}}}
    assert _snapshot(render(_payload([_pool(state='FAULTED')], levels), _SCHEMA)) == [  # nosec B101
        _header(),
        _pool_row(state=' FAULTED', state_color='critical'),
    ]


def test_status_line_is_first_sentence():
    raw_status = (
        'One or more devices could\n\tnot be opened.  Sufficient replicas exist for\n'
        '\tthe pool to continue functioning in a degraded state.\n'
    )
    assert _status_text(raw_status) == 'One or more devices could not be opened.'  # nosec B101
    assert _snapshot(render(_payload([_pool(status=raw_status)]), _SCHEMA)) == [  # nosec B101
        _header(),
        _pool_row(),
        _status_row('  └─ One or more devices could ...'),
    ]


def test_status_line_is_warning_coloured():
    rows = render(_payload([_pool(status='One or more devices could not be opened.\n')]), _SCHEMA)
    assert _snapshot(rows) == [  # nosec B101
        _header(),
        _pool_row(),
        _status_row('  └─ One or more devices could ...'),
    ]


def test_status_line_fits_left_sidebar():
    expected = '  └─ ' + 'A' * 26 + '...'
    assert _snapshot(render(_payload([_pool(status='A' * 300 + '.')]), _SCHEMA)) == [  # nosec B101
        _header(),
        _pool_row(),
        _status_row(expected),
    ]


def test_status_text_caps_at_256_chars():
    assert _status_text('A' * 300 + '.', limit=256) == 'A' * 253 + '...'  # nosec B101


def test_datasets_hidden_by_default():
    dataset = {'name': 'tank/home', 'used': 10, 'available': 90}
    assert _snapshot(render(_payload([_pool(datasets=[dataset])]), _SCHEMA)) == [_header(), _pool_row()]  # nosec B101


def test_datasets_shown_when_enabled():
    dataset = {'name': 'tank/home', 'used': 10, 'available': 90}
    assert _snapshot(render(_payload([_pool(datasets=[dataset])], show_datasets=True), _SCHEMA)) == [  # nosec B101
        _header(),
        _pool_row(),
        _row(_cell('  └─ tank/home    '), _cell('    10B'), _cell('    90B')),
    ]
