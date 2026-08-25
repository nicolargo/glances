#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the InfluxDB normalization of exported stats (issues #3419, #3423)."""

import pytest

from glances.exports.export import GlancesExport


@pytest.fixture
def exporter():
    """An exporter with just enough state for normalize_for_influxdb()."""
    export = GlancesExport.__new__(GlancesExport)
    export.tags = None
    export.hostname = 'testhost'
    return export


def fields_of(exporter, columns, points, measurement='amps'):
    result = exporter.normalize_for_influxdb(measurement, columns, points)
    assert len(result) == 1
    return result[0]['fields']


class TestAmpResultTyping:
    """`result` carries whatever the AMP command printed.

    Forcing it to a string keeps InfluxDB from rejecting the second AMP that
    writes a different type into the same column (#3419) — but it also left a
    numeric AMP with no numeric field at all. `result_float` is that field.
    """

    def test_a_numeric_result_is_also_published_as_a_float(self, exporter):
        fields = fields_of(exporter, ['key', 'name', 'result'], ['name', 'throttle', '42'])
        assert fields['result_float'] == 42.0
        assert isinstance(fields['result_float'], float)

    def test_result_itself_stays_a_string(self, exporter):
        fields = fields_of(exporter, ['key', 'name', 'result'], ['name', 'throttle', 3.5])
        assert isinstance(fields['result'], str)

    def test_a_textual_result_publishes_no_float(self, exporter):
        fields = fields_of(exporter, ['key', 'name', 'result'], ['name', 'conntrack', 'nf_conntrack_count = 123'])
        assert 'result_float' not in fields
        assert fields['result'] == 'nf_conntrack_count = 123'

    def test_the_two_amps_from_the_report_can_coexist(self, exporter):
        """A string AMP and a numeric AMP must not disagree about a column type."""
        text = fields_of(exporter, ['key', 'name', 'result'], ['name', 'conntrack', 'count = 1'])
        number = fields_of(exporter, ['key', 'name', 'result'], ['name', 'throttle', '7'])
        assert type(text['result']) is type(number['result'])
        assert number['result_float'] == 7.0

    @pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
    def test_non_finite_results_are_not_published_as_floats(self, exporter, value):
        """InfluxDB rejects NaN/inf; one of them would fail the whole write."""
        fields = fields_of(exporter, ['key', 'name', 'result'], ['name', 'weird', value])
        assert 'result_float' not in fields

    def test_an_empty_result_publishes_neither_field(self, exporter):
        fields = fields_of(exporter, ['key', 'name', 'result'], ['name', 'quiet', None])
        assert 'result_float' not in fields

    def test_a_zero_result_is_still_published(self, exporter):
        fields = fields_of(exporter, ['key', 'name', 'result'], ['name', 'throttle', '0'])
        assert fields['result_float'] == 0.0


class TestNormalizeUnchanged:
    """The companion field must not disturb the rest of the normalization."""

    def test_ordinary_numeric_fields_stay_floats_without_a_companion(self, exporter):
        fields = fields_of(exporter, ['key', 'name', 'cpu_percent'], ['name', 'a', 12], measurement='p')
        assert fields['cpu_percent'] == 12.0
        assert 'cpu_percent_float' not in fields

    def test_a_measurement_without_a_result_is_untouched(self, exporter):
        fields = fields_of(exporter, ['key', 'name', 'count'], ['name', 'a', 3], measurement='p')
        assert fields == {'key': 'name', 'count': 3.0}
