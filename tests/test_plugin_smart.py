"""Tests for the SMART plugin curses rendering."""

from argparse import Namespace

import pytest

import glances.plugins.smart as smart_mod
from glances.plugins.smart import SmartPlugin


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
