#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Quicklook plugin stats list configuration."""

import os

import pytest

from glances.config import Config
from glances.plugins.quicklook import QuicklookPlugin


@pytest.fixture
def plugin_for(tmp_path):
    """Build a Quicklook plugin from a `[quicklook] list=...` config value."""

    def build(list_value):
        config_file = tmp_path / f'glances-{abs(hash(list_value))}.conf'
        config_file.write_text(f'[quicklook]\nlist={list_value}\n', encoding='utf-8')
        return QuicklookPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

    return build


class TestQuicklookStatsList:
    def test_a_plain_list_is_honoured(self, plugin_for):
        assert plugin_for('cpu,mem,load').stats_list == ['cpu', 'mem', 'load']

    @pytest.mark.parametrize(
        'list_value',
        [
            'cpu, mem, load',
            'cpu ,mem ,load',
            ' cpu , mem , load ',
            'cpu,\tmem,\tload',
        ],
    )
    def test_whitespace_around_items_is_ignored(self, plugin_for, list_value):
        """`list=cpu, mem, load` is how anyone writes a comma-separated value.

        glances.conf writes it that way in its own `# Available stats are:` comment, so
        a user copying that line got a list where every item but the first carried a
        leading space, matched nothing, and was discarded whole.
        """
        assert plugin_for(list_value).stats_list == ['cpu', 'mem', 'load']

    def test_a_typo_falls_back_to_the_default_not_to_everything(self, plugin_for):
        """A config mistake must not answer by displaying MORE than was asked for.

        The fallback used to be AVAILABLE_STATS_LIST, which includes both GPU entries —
        and those flip the gpu_stats polling flags. A single typo therefore started
        polling the GPU on a machine whose owner never asked for it.
        """
        plugin = plugin_for('cpu,mem,typo')

        assert plugin.stats_list == QuicklookPlugin.DEFAULT_STATS_LIST
        assert 'gpu_mem' not in plugin.stats_list
        assert 'gpu_proc' not in plugin.stats_list

    def test_the_gpu_entries_are_still_selectable_on_purpose(self, plugin_for):
        """The fallback must not become a filter: an explicit request still works."""
        assert plugin_for('cpu,gpu_mem,gpu_proc').stats_list == ['cpu', 'gpu_mem', 'gpu_proc']

    def test_no_list_configured_uses_the_default(self, tmp_path):
        config_file = tmp_path / 'glances-empty.conf'
        config_file.write_text('[quicklook]\ndisable=False\n', encoding='utf-8')
        plugin = QuicklookPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

        assert plugin.stats_list == QuicklookPlugin.DEFAULT_STATS_LIST


class TestConfigListParsing:
    """The strip belongs to `load_limits`, so every plugin reading a list gets it."""

    def test_limits_carry_stripped_items(self, plugin_for):
        assert plugin_for('cpu, mem, load').get_limits('list') == ['cpu', 'mem', 'load']

    def test_a_hide_pattern_written_with_spaces_still_hides(self, tmp_path):
        """The show/hide filters are the loudest symptom of the same parsing bug.

        Every item in those lists is used as a `re.fullmatch` pattern, so a leading
        space made the pattern match nothing at all — `hide=sda2, loop.*` hid `sda2`
        and silently kept showing every loop device.
        """
        from glances.plugins.diskio import DiskioPlugin

        config_file = tmp_path / 'glances-hide.conf'
        config_file.write_text('[diskio]\nhide=sda2, loop.*\n', encoding='utf-8')
        plugin = DiskioPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

        assert plugin.get_conf_value('hide') == ['sda2', 'loop.*']
        assert plugin.is_hide('sda2')
        assert plugin.is_hide('loop0')
        assert not plugin.is_hide('sda1')

    def test_internal_spaces_are_kept(self, tmp_path):
        """Only the edges are stripped — a value may legitimately contain spaces."""
        config_file = tmp_path / 'glances-alias.conf'
        config_file.write_text('[quicklook]\nlist=cpu\nalias=sda1:System Disk , sdb1:Data Disk\n', encoding='utf-8')
        plugin = QuicklookPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

        assert plugin.get_limits('alias') == ['sda1:System Disk', 'sdb1:Data Disk']
