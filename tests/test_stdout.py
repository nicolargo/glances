#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Glances contributors
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for raw stdout selectors."""

from types import SimpleNamespace

import pytest

from glances.outputs.glances_stdout import GlancesStdout


@pytest.mark.parametrize(
    ('selector', 'expected'),
    [
        ('network.eth0.100.bytes_recv', [('network', 'eth0.100', 'bytes_recv')]),
        ('load,network.eth0.100.bytes_recv', [('load', None, None), ('network', 'eth0.100', 'bytes_recv')]),
        ('load', [('load', None, None)]),
        ('cpu.user', [('cpu', None, 'user')]),
        ('network.eth0.bytes_recv', [('network', 'eth0', 'bytes_recv')]),
    ],
)
def test_stdout_selectors(selector, expected):
    output = GlancesStdout(args=SimpleNamespace(stdout=selector))
    assert output.plugins_list == expected
