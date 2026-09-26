# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""CSV file columns must keep their identities as devices appear and disappear."""

import csv
from types import SimpleNamespace

import pytest

from glances.exports.glances_csv import Export


def test_csv_columns_remain_aligned_when_interfaces_change(tmp_path):
    path = tmp_path / 'stats.csv'
    exporter = Export(args=SimpleNamespace(export_csv_file=str(path), export_csv_overwrite=False))
    exporter.exclude_fields = None

    def update(items):
        stats = SimpleNamespace(
            getPluginsList=lambda: ['network'],
            getAllExportsAsDict=lambda **kwargs: {'network': items},
        )
        exporter.update(stats)

    try:
        update([{'key': 'name', 'name': 'z0', 'bytes_recv': 10}])
        update(
            [
                {'key': 'name', 'name': 'a0', 'bytes_recv': 100},
                {'key': 'name', 'name': 'z0', 'bytes_recv': 20},
            ]
        )
        update([{'key': 'name', 'name': 'a0', 'bytes_recv': 200}])
    finally:
        exporter.exit()

    with path.open(newline='') as file:
        rows = list(csv.reader(file))
    assert all(len(row) == len(rows[0]) for row in rows[1:])
    counter = rows[0].index('network.z0.bytes_recv')
    assert [row[counter] for row in rows[1:]] == ['10', '20', '']


@pytest.mark.parametrize('compatible', [True, False])
def test_existing_header_compatibility_is_preserved(tmp_path, compatible):
    path = tmp_path / 'stats.csv'
    column = 'cpu.total' if compatible else 'cpu.other'
    with path.open('w', newline='') as file:
        csv.writer(file).writerows([['timestamp', column], ['before', '1']])
    original = path.read_bytes()
    exporter = Export(args=SimpleNamespace(export_csv_file=str(path), export_csv_overwrite=False))
    exporter.exclude_fields = None
    stats = SimpleNamespace(
        getPluginsList=lambda: ['cpu'],
        getAllExportsAsDict=lambda **kwargs: {'cpu': {'total': 2}},
    )
    try:
        exporter.update(stats)
    finally:
        exporter.exit()
    if compatible:
        with path.open(newline='') as file:
            rows = list(csv.reader(file))
        assert len(rows) == 3
        assert rows[-1][1] == '2'
    else:
        assert path.read_bytes() == original
