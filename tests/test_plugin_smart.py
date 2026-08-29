#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the SMART plugin `hide_attributes` configuration."""

import os

import pytest

from glances.config import Config
from glances.plugins.smart import SmartPlugin


@pytest.fixture
def plugin_for(tmp_path):
    """Build a SMART plugin from a `[smart] hide_attributes=...` config value."""

    def build(hide_value):
        config_file = tmp_path / f'glances-{abs(hash(hide_value))}.conf'
        config_file.write_text(f'[smart]\nhide_attributes={hide_value}\n', encoding='utf-8')
        return SmartPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

    return build


class TestSmartHideAttributes:
    def test_a_plain_list_is_honoured(self, plugin_for):
        assert plugin_for('Self-tests,Errors').hide_attributes == ['Self-tests', 'Errors']

    @pytest.mark.parametrize(
        'hide_value',
        [
            'Self-tests, Errors',
            'Self-tests ,Errors',
            ' Self-tests , Errors ',
        ],
    )
    def test_whitespace_around_items_is_ignored(self, plugin_for, hide_value):
        """`hide_attributes` is read from `config.as_dict()`, not from `load_limits`.

        The PR #3700 strip therefore never reached it: an attribute written with a
        leading space was compared against the SMART attribute names and never
        matched, so the rule was accepted, logged, and silently did nothing.
        """
        assert plugin_for(hide_value).hide_attributes == ['Self-tests', 'Errors']

    def test_an_empty_value_hides_nothing(self, plugin_for):
        assert plugin_for('').hide_attributes == []
