# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""Regression tests for the Elasticsearch export bulk actions."""

from unittest import mock

import pytest

pytest.importorskip("elasticsearch")

from glances.exports import glances_elasticsearch  # noqa: E402


def export_actions(name, columns, points):
    exporter = glances_elasticsearch.Export.__new__(glances_elasticsearch.Export)
    exporter.index = 'glances'
    exporter.client = mock.Mock()
    with mock.patch.object(glances_elasticsearch.helpers, 'bulk') as bulk:
        exporter.export(name, columns, points)
    return bulk.call_args.args[1]


def test_actions_do_not_set_a_mapping_type():
    # Elasticsearch 6+ allows a single mapping type per index and 8+ rejects _type:
    # the plugins share the same daily index, so they must not use their own type.
    for plugin in ('cpu', 'mem'):
        (action,) = export_actions(plugin, ['total'], [42.0])

        assert '_type' not in action
        assert action['_index'].startswith('glances-')
        assert action['_source']['plugin'] == plugin
        assert action['_source']['total'] == '42.0'
