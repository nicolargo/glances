#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""A row survives while any of its hide_zero fields is still visible.

hide_zero is decided per field, but it is applied per row: msg_curse drops a
disk only when *all* of its hide_zero_fields are hidden. plugin-diskio.vue and
plugin-network.vue read the same views dict and must reach the same verdict, so
these tests pin the rule on the side that can be tested here.

The half-hidden state -- one rate above the threshold, the other below -- is the
one where an "all fields visible" reading and an "all fields hidden" reading
disagree, so that is what the tests build.
"""

import os
from argparse import Namespace

import pytest

from glances.config import Config
from glances.plugins.diskio import DiskioPlugin

READ = 'read_bytes_rate_per_sec'
WRITE = 'write_bytes_rate_per_sec'

THRESHOLD = 1024


def args():
    """The plugin only draws when it is enabled, so msg_curse needs real args."""
    return Namespace(
        disable_diskio=False,
        diskio_iops=False,
        diskio_latency=False,
        diskio_show_ramfs=False,
        disable_history=True,
    )


@pytest.fixture
def plugin(tmp_path):
    config_file = tmp_path / 'glances.conf'
    config_file.write_text(
        f'[diskio]\nhide_zero=True\nhide_threshold_bytes={THRESHOLD}\n',
        encoding='utf-8',
    )
    return DiskioPlugin(args=args(), config=Config(config_dir=os.fspath(config_file)))


def disk(read_rate, write_rate, name='sda'):
    return {
        'disk_name': name,
        'key': 'disk_name',
        'time_since_update': 1.0,
        'read_count': 0,
        'write_count': 0,
        'read_bytes': 0,
        'write_bytes': 0,
        'read_latency': 0,
        'write_latency': 0,
        READ: read_rate,
        WRITE: write_rate,
        'read_count_rate_per_sec': 0,
        'write_count_rate_per_sec': 0,
    }


def sample(plugin, *disks):
    plugin.stats = list(disks)
    plugin.update_views()
    return plugin.views


def curse_text(plugin):
    return ''.join(line['msg'] for line in plugin.msg_curse(args=plugin.args, max_width=40))


class TestHalfHiddenRow:
    """One rate above the threshold, the other below."""

    def test_the_two_fields_really_do_disagree(self, plugin):
        # Without this the tests below would pass on any rule at all.
        sample(plugin, disk(0, 0))
        views = sample(plugin, disk(THRESHOLD * 2, 0))
        assert views['sda'][READ]['hidden'] is False
        assert views['sda'][WRITE]['hidden'] is True

    def test_a_read_only_disk_is_still_displayed(self, plugin):
        sample(plugin, disk(0, 0))
        sample(plugin, disk(THRESHOLD * 2, 0))
        assert 'sda' in curse_text(plugin)

    def test_a_write_only_disk_is_still_displayed(self, plugin):
        sample(plugin, disk(0, 0))
        sample(plugin, disk(0, THRESHOLD * 2))
        assert 'sda' in curse_text(plugin)


class TestFullyHiddenRow:
    """Every field hidden is the only reason to drop a row."""

    def test_a_disk_below_the_threshold_on_both_rates_is_dropped(self, plugin):
        sample(plugin, disk(0, 0))
        sample(plugin, disk(THRESHOLD - 500, THRESHOLD - 500))
        assert 'sda' not in curse_text(plugin)

    def test_a_busy_disk_is_displayed_beside_a_hidden_one(self, plugin):
        sample(plugin, disk(0, 0, 'quiet'), disk(0, 0, 'busy'))
        sample(plugin, disk(0, 0, 'quiet'), disk(THRESHOLD * 2, THRESHOLD * 2, 'busy'))
        text = curse_text(plugin)
        assert 'busy' in text
        assert 'quiet' not in text
