#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the GPU plugin (ARM backend)."""

import pytest

from glances.globals import LINUX
from glances.plugins.gpu.cards.arm import (
    ArmGPU,
    aggregate_fdinfo,
    compute_mem_percent,
    get_device_list,
    get_device_name,
    parse_fdinfo,
)

ARM_TEST_DATA_ROOT = './tests-data/plugins/gpu/arm'
ARM_DRM_ROOT = f'{ARM_TEST_DATA_ROOT}/sys/class/drm'
ARM_PROC_ROOT = f'{ARM_TEST_DATA_ROOT}/proc'


@pytest.fixture
def arm_backend():
    """Return an ArmGPU instance wired to the test fixtures."""
    return ArmGPU(drm_root_folder=ARM_DRM_ROOT, proc_root_folder=ARM_PROC_ROOT)


@pytest.fixture
def gpu_plugin(glances_stats):
    """Return the GPU plugin instance from glances_stats."""
    return glances_stats.get_plugin('gpu')


class TestArmFdinfoParser:
    """Unit tests for the fdinfo parser (pure, no I/O)."""

    def test_valid_panthor_record(self):
        text = (
            "pos:\t0\n"
            "drm-driver:\tpanthor\n"
            "drm-pdev:\tfe9b0000.gpu\n"
            "drm-engine-fragment:\t1000 ns\n"
            "drm-engine-vertex-tiler:\t2000 ns\n"
            "drm-total-memory:\t2048 KiB\n"
            "drm-resident-memory:\t1024 KiB\n"
        )
        record = parse_fdinfo(text)
        assert record is not None
        assert record['driver'] == 'panthor'
        assert record['pdev'] == 'fe9b0000.gpu'
        assert record['engine_total_ns'] == 3000
        assert record['mem_total_bytes'] == 2048 * 1024
        assert record['mem_used_bytes'] == 1024 * 1024

    def test_not_a_drm_fd(self):
        assert parse_fdinfo("pos:\t0\nflags:\t02100002\n") is None

    def test_empty_text(self):
        assert parse_fdinfo("") is None

    def test_missing_driver_line(self):
        text = "pos:\t0\ndrm-pdev:\tfe9b0000.gpu\ndrm-engine-foo:\t1 ns\n"
        assert parse_fdinfo(text) is None

    def test_memory_default_unit_is_kib(self):
        text = "drm-driver:\tmsm\ndrm-total-memory:\t1\n"
        record = parse_fdinfo(text)
        assert record is not None
        assert record['mem_total_bytes'] == 1024

    def test_unknown_memory_unit_ignored(self):
        text = "drm-driver:\tmsm\ndrm-total-memory:\t42 QB\n"
        record = parse_fdinfo(text)
        assert record is not None
        assert record['mem_total_bytes'] == 0

    def test_malformed_lines_do_not_crash(self):
        text = "drm-driver:\tpanthor\ndrm-engine-bogus:\tnotanumber ns\ndrm-total-memory:\txyz\nno-colon-here\n"
        record = parse_fdinfo(text)
        assert record is not None
        assert record['engine_total_ns'] == 0
        assert record['mem_total_bytes'] == 0


class TestArmComputeHelpers:
    """Unit tests for small helpers."""

    def test_compute_mem_percent_none(self):
        assert compute_mem_percent(None) is None

    def test_compute_mem_percent_zero_total(self):
        assert compute_mem_percent({'mem_total_bytes': 0, 'mem_used_bytes': 0}) is None

    def test_compute_mem_percent_half(self):
        snapshot = {'mem_total_bytes': 1000, 'mem_used_bytes': 500}
        assert compute_mem_percent(snapshot) == 50

    def test_compute_mem_percent_clamped(self):
        snapshot = {'mem_total_bytes': 100, 'mem_used_bytes': 500}
        assert compute_mem_percent(snapshot) == 100

    def test_get_device_name_known(self):
        assert get_device_name('panthor') == 'Mali (Panthor)'
        assert get_device_name('msm') == 'Adreno (msm)'

    def test_get_device_name_unknown(self):
        assert get_device_name('unknown-driver-xyz') == 'ARM GPU'


@pytest.mark.skipif(not LINUX, reason="ARM GPU backend is Linux-only")
class TestArmBackendDiscovery:
    """Discovery tests against the committed test fixtures."""

    def test_device_enumeration(self, arm_backend):
        assert len(arm_backend.device_folders) == 1
        device, driver, _pdev = arm_backend.device_folders[0]
        assert driver == 'panthor'
        assert device.endswith('card0')

    def test_stats_shape(self, arm_backend):
        stats = arm_backend.get_device_stats()
        assert isinstance(stats, list)
        assert len(stats) == 1
        entry = stats[0]
        for key in ('key', 'gpu_id', 'name', 'mem', 'proc', 'temperature', 'fan_speed'):
            assert key in entry
        assert entry['key'] == 'gpu_id'
        assert entry['gpu_id'] == 'arm0'
        assert entry['name'] == 'Mali (Panthor)'

    def test_temperature(self, arm_backend):
        stats = arm_backend.get_device_stats()
        assert stats[0]['temperature'] == 45

    def test_fan_speed_always_none(self, arm_backend):
        stats = arm_backend.get_device_stats()
        assert stats[0]['fan_speed'] is None

    def test_mem_aggregated_from_fdinfo(self, arm_backend):
        # Two clients: 1024 + 512 KiB used over 2048 + 1024 KiB total = 50%
        stats = arm_backend.get_device_stats()
        assert stats[0]['mem'] == 50

    def test_proc_first_call_is_none(self, arm_backend):
        # Delta-based: first call has no previous sample.
        stats = arm_backend.get_device_stats()
        assert stats[0]['proc'] is None

    def test_proc_second_call_is_int(self, arm_backend):
        arm_backend.get_device_stats()
        stats = arm_backend.get_device_stats()
        assert isinstance(stats[0]['proc'], int)
        assert 0 <= stats[0]['proc'] <= 100


class TestArmBackendNoHardware:
    """Backend must degrade gracefully with no hardware / no sysfs."""

    def test_missing_drm_root(self):
        backend = ArmGPU(
            drm_root_folder='/this/path/does/not/exist',
            proc_root_folder='/this/path/does/not/exist',
        )
        assert backend.device_folders == []
        assert backend.get_device_stats() == []

    def test_missing_proc_root(self):
        backend = ArmGPU(
            drm_root_folder=ARM_DRM_ROOT,
            proc_root_folder='/this/path/does/not/exist',
        )
        stats = backend.get_device_stats() if LINUX else []
        if LINUX:
            assert len(stats) == 1
            assert stats[0]['mem'] is None
            assert stats[0]['proc'] is None


@pytest.mark.skipif(not LINUX, reason="ARM GPU backend is Linux-only")
class TestArmAggregation:
    """Aggregation layer tests."""

    def test_aggregate_fdinfo_ignores_non_drm(self):
        devices = get_device_list(ARM_DRM_ROOT)
        per_device = aggregate_fdinfo(ARM_PROC_ROOT, devices)
        assert len(per_device) == 1
        bucket = next(iter(per_device.values()))
        # Sum of the two fdinfo entries' engine counters and memory.
        # Client 1: 5_000_000 + 3_000_000 + 0 = 8_000_000 ns
        # Client 2: 1_000_000 + 500_000 = 1_500_000 ns
        assert bucket['engine_total_ns'] == 9_500_000
        assert bucket['mem_total_bytes'] == 3072 * 1024
        assert bucket['mem_used_bytes'] == 1536 * 1024


class TestGpuPluginIntegration:
    """End-to-end plugin test."""

    def test_plugin_name(self, gpu_plugin):
        assert gpu_plugin.plugin_name == 'gpu'

    def test_get_key_returns_gpu_id(self, gpu_plugin):
        assert gpu_plugin.get_key() == 'gpu_id'

    def test_update_does_not_crash(self, gpu_plugin):
        gpu_plugin.update()
        assert isinstance(gpu_plugin.get_raw(), list)

    def test_exit_tolerates_none_backends(self, gpu_plugin):
        """Regression guard: exit() must not crash if a backend failed to init."""
        saved = (gpu_plugin.nvidia, gpu_plugin.amd, gpu_plugin.intel, gpu_plugin.arm)
        try:
            gpu_plugin.nvidia = None
            gpu_plugin.amd = None
            gpu_plugin.intel = None
            gpu_plugin.arm = None
            # Should not raise
            gpu_plugin.exit()
        finally:
            gpu_plugin.nvidia, gpu_plugin.amd, gpu_plugin.intel, gpu_plugin.arm = saved

    @pytest.mark.skipif(not LINUX, reason="ARM GPU backend is Linux-only")
    def test_arm_backend_can_be_injected(self, gpu_plugin):
        gpu_plugin.arm = ArmGPU(
            drm_root_folder=ARM_DRM_ROOT,
            proc_root_folder=ARM_PROC_ROOT,
        )
        # Force a real update (the plugin rate-limits via refresh_timer).
        gpu_plugin.refresh_timer.reset(0)
        gpu_plugin.update()
        stats = gpu_plugin.get_raw()
        arm_entries = [s for s in stats if s.get('gpu_id', '').startswith('arm')]
        assert len(arm_entries) == 1
        assert arm_entries[0]['name'] == 'Mali (Panthor)'
