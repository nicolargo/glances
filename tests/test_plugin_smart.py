#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the SMART plugin: `hide_attributes` configuration and curses rendering."""

import os
from argparse import Namespace

import pytest

import glances.plugins.smart as smart_mod
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


class EmptyConfig:
    """Minimal stand-in for the Glances config, with no [smart] section."""

    def as_dict(self):
        return {}


@pytest.fixture
def plugin(monkeypatch):
    """A SMART plugin instance, enabled, with the pySMART dependency faked as available."""
    monkeypatch.setattr(smart_mod, 'is_admin', lambda: True)
    monkeypatch.setattr(smart_mod, 'import_error_tag', False)
    return SmartPlugin(args=Namespace(disable_smart=False, disable_history=True), config=EmptyConfig())


def device_stats(plugin):
    """One device, as update() builds it: the top-level 'key' next to the numbered attributes."""
    return dict(
        {
            'DeviceName': 'sda My Disk',
            2: {'name': 'Throughput_Performance', 'key': 'Throughput_Performance', 'raw': '100'},
            1: {'name': 'Raw_Read_Error_Rate', 'key': 'Raw_Read_Error_Rate', 'raw': '0'},
        },
        key=plugin.get_key(),
    )


def test_top_level_key_is_not_rendered_as_an_attribute(plugin):
    # See #3704: 'key' holds the name of the identifier field, not an attribute dict.
    assert plugin._get_sorted_stat_keys(device_stats(plugin)) == [1, 2]


def test_msg_curse_renders_the_device_attributes(plugin):
    plugin.stats = [device_stats(plugin)]
    displayed = [line['msg'].strip() for line in plugin.msg_curse(max_width=40)]
    assert 'Raw Read Error Rate' in displayed
    assert 'Throughput Performance' in displayed
