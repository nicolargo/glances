#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the per-process GPU% column (Intel i915/xe, nvtop-style)."""

import pytest

import glances.plugins.processlist as processlist_module
from glances.globals import LINUX
from glances.outputs.glances_curses import _GlancesCurses
from glances.processes import glances_processes, sort_stats


@pytest.fixture
def process_plugin(glances_stats):
    """Return the processlist plugin with fresh process data.

    Process data is gathered by the processcount plugin update
    (processlist only reads the shared list).
    """
    process_count = glances_stats.get_plugin('processcount')
    process_count.refresh_timer.reset(0)
    process_count.update()
    return glances_stats.get_plugin('processlist')


@pytest.mark.skipif(not LINUX, reason="Per-process GPU stats are Linux-only")
class TestProcesslistGpuColumn:
    """Column merge, visibility rules and sorting."""

    def test_column_shown_with_zeros_when_idle(self, process_plugin, monkeypatch):
        monkeypatch.setattr(processlist_module, 'intel_gpu_present', lambda: True)
        monkeypatch.setattr(
            processlist_module, 'get_per_pid_gpu_percent', lambda *a, **k: {}
        )
        process_plugin.update()
        assert 'gpu_percent' in process_plugin.enable_stats
        assert process_plugin.stats
        assert all(
            isinstance(p.get('gpu_percent'), int) for p in process_plugin.stats
        )
        assert process_plugin.max_values['gpu_percent'] == 0

    def test_nonzero_values_merged_by_pid(self, process_plugin, monkeypatch):
        monkeypatch.setattr(processlist_module, 'intel_gpu_present', lambda: True)
        monkeypatch.setattr(
            processlist_module, 'get_per_pid_gpu_percent', lambda *a, **k: {}
        )
        process_plugin.update()
        target_pid = process_plugin.stats[0]['pid']
        monkeypatch.setattr(
            processlist_module,
            'get_per_pid_gpu_percent',
            lambda *a, **k: {target_pid: 77},
        )
        process_plugin.update()
        by_pid = {p['pid']: p for p in process_plugin.stats}
        assert by_pid[target_pid]['gpu_percent'] == 77
        assert process_plugin.max_values['gpu_percent'] == 77
        others = [p for pid, p in by_pid.items() if pid != target_pid]
        assert all(p['gpu_percent'] == 0 for p in others)

    def test_column_hidden_without_intel_gpu(self, process_plugin, monkeypatch):
        monkeypatch.setattr(processlist_module, 'intel_gpu_present', lambda: False)
        process_plugin.update()
        assert 'gpu_percent' not in process_plugin.enable_stats
        assert 'gpu_mem' not in process_plugin.enable_stats

    def test_mem_column_merged_by_pid(self, process_plugin, monkeypatch):
        monkeypatch.setattr(processlist_module, 'intel_gpu_present', lambda: True)
        monkeypatch.setattr(
            processlist_module, 'get_per_pid_gpu_percent', lambda *a, **k: {}
        )
        monkeypatch.setattr(
            processlist_module, 'get_mem_capacity_bytes', lambda *a, **k: 2000
        )
        process_plugin.update()
        target_pid = process_plugin.stats[0]['pid']
        monkeypatch.setattr(
            processlist_module,
            'get_per_pid_gpu_mem_bytes',
            lambda *a, **k: {target_pid: 1024},
        )
        process_plugin.update()
        assert 'gpu_mem' in process_plugin.enable_stats
        by_pid = {p['pid']: p for p in process_plugin.stats}
        # 1024 of 2000 bytes -> 51.2% of system memory.
        assert by_pid[target_pid]['gpu_mem'] == 51.2
        assert process_plugin.max_values['gpu_mem'] == 51.2
        # gpu_mem sits right after gpu_percent (or cpu_percent).
        order = process_plugin.enable_stats
        assert order.index('gpu_mem') == order.index('gpu_percent') + 1

    def test_mem_column_hidden_when_disabled(self, process_plugin, monkeypatch):
        monkeypatch.setattr(processlist_module, 'intel_gpu_present', lambda: True)
        monkeypatch.setattr(
            glances_processes, 'disable_stats', ['gpu_mem'], raising=False
        )
        process_plugin.update()
        assert 'gpu_mem' not in process_plugin.enable_stats

    def test_sort_by_gpu_mem(self):
        stats = [
            {'name': 'idle', 'gpu_mem': 0.0, 'memory_percent': 1.0},
            {'name': 'llm', 'gpu_mem': 29.2, 'memory_percent': 2.0},
            {'name': 'video', 'gpu_mem': 1.5, 'memory_percent': 3.0},
        ]
        ordered = [p['name'] for p in sort_stats(stats, 'gpu_mem')]
        assert ordered == ['llm', 'video', 'idle']

    def test_gpu_mem_next_to_gpu_in_sort_loop(self):
        from glances.processes import sort_processes_stats_list

        assert sort_processes_stats_list.index('gpu_mem') == (
            sort_processes_stats_list.index('gpu_percent') + 1
        )

    def test_mem_sort_hotkey_registered(self):
        assert _GlancesCurses._hotkeys['y'] == {'sort_key': 'gpu_mem'}

    def test_gmem_threshold_defaults(self, glances_stats):
        plugin = glances_stats.get_plugin('processlist')
        limits = plugin.get_limit(None)
        assert int(limits['processlist_gmem_careful']) == 50
        assert int(limits['processlist_gmem_warning']) == 70
        assert int(limits['processlist_gmem_critical']) == 90

    def test_column_hidden_when_disabled(self, process_plugin, monkeypatch):
        monkeypatch.setattr(processlist_module, 'intel_gpu_present', lambda: True)
        monkeypatch.setattr(
            glances_processes, 'disable_stats', ['gpu_percent'], raising=False
        )
        process_plugin.update()
        assert 'gpu_percent' not in process_plugin.enable_stats

    def test_sort_by_gpu_percent(self):
        stats = [
            {'name': 'idle', 'gpu_percent': 0, 'memory_percent': 1.0},
            {'name': 'render', 'gpu_percent': 77, 'memory_percent': 2.0},
            {'name': 'video', 'gpu_percent': 12, 'memory_percent': 3.0},
        ]
        ordered = [p['name'] for p in sort_stats(stats, 'gpu_percent')]
        assert ordered == ['render', 'video', 'idle']

    def test_gpu_next_to_cpu_in_sort_loop(self):
        # Shift+Left/Right cycles this list while the columns are shown in
        # the same order -- GPU% must directly follow CPU%.
        from glances.processes import sort_processes_stats_list

        assert sort_processes_stats_list.index('gpu_percent') == (
            sort_processes_stats_list.index('cpu_percent') + 1
        )

    def test_gpu_threshold_defaults(self, glances_stats):
        plugin = glances_stats.get_plugin('processlist')
        limits = plugin.get_limit(None)
        assert int(limits['processlist_gpu_careful']) == 50
        assert int(limits['processlist_gpu_warning']) == 70
        assert int(limits['processlist_gpu_critical']) == 90

    def test_sort_hotkey_registered(self):
        assert _GlancesCurses._hotkeys['v'] == {'sort_key': 'gpu_percent'}
