#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the GPU plugin (ARM and Tegra backends)."""

import os
import time

import pytest

from glances.globals import LINUX
from glances.plugins.gpu.cards import intel as intel_backend
from glances.plugins.gpu.cards import tegra
from glances.plugins.gpu.cards.arm import (
    ArmGPU,
    aggregate_fdinfo,
    compute_mem_percent,
    get_device_list,
    get_device_name,
    get_mem_capacity_bytes,
    parse_fdinfo,
)
from glances.plugins.gpu.cards.intel import IntelGPU

ARM_TEST_DATA_ROOT = './tests-data/plugins/gpu/arm'
ARM_DRM_ROOT = f'{ARM_TEST_DATA_ROOT}/sys/class/drm'
ARM_PROC_ROOT = f'{ARM_TEST_DATA_ROOT}/proc'

INTEL_TEST_DATA_ROOT = './tests-data/plugins/gpu/intel'
INTEL_DRM_ROOT = f'{INTEL_TEST_DATA_ROOT}/sys/class/drm'
INTEL_PROC_ROOT = f'{INTEL_TEST_DATA_ROOT}/proc'
# Fixture frequencies: 300 / 1450 MHz -> frequency fallback is 21 %.
INTEL_FREQ_FALLBACK = 21

TEGRA_TEST_DATA_ROOT = './tests-data/plugins/gpu/tegra'
TEGRA_GPU_FOLDER = f'{TEGRA_TEST_DATA_ROOT}/sys/devices/platform/gpu.0'
TEGRA_THERMAL_ROOT = f'{TEGRA_TEST_DATA_ROOT}/sys/class/thermal'


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

    def test_compute_mem_percent_capacity_denominator(self):
        # capacity_bytes (CmaTotal/MemTotal) overrides the fdinfo drm-total.
        snapshot = {'mem_total_bytes': 100, 'mem_used_bytes': 500}
        assert compute_mem_percent(snapshot, capacity_bytes=1000) == 50

    def test_compute_mem_percent_capacity_clamped(self):
        # used > capacity -> v3d spilled past the CMA pool; clamp to 100.
        snapshot = {'mem_total_bytes': 100, 'mem_used_bytes': 500}
        assert compute_mem_percent(snapshot, capacity_bytes=100) == 100

    def test_get_device_name_known(self):
        assert get_device_name('panthor') == 'Mali (Panthor)'
        assert get_device_name('msm') == 'Adreno (msm)'

    def test_get_device_name_unknown(self):
        assert get_device_name('unknown-driver-xyz') == 'ARM GPU'


class TestArmMemCapacity:
    """Denominator cascade for GPU mem% (issue #3611). Mocks /proc/meminfo."""

    def _write_meminfo(self, tmp_path, content):
        path = tmp_path / 'meminfo'
        path.write_text(content)
        return str(path)

    def test_cma_total_present(self, tmp_path):
        # CmaTotal > 0 -> denominator is CmaTotal (in bytes: kB * 1024).
        path = self._write_meminfo(
            tmp_path,
            "MemTotal:        8192000 kB\nCmaTotal:         262144 kB\n",
        )
        assert get_mem_capacity_bytes(path) == 262144 * 1024

    def test_cma_total_zero_falls_back_to_mem_total(self, tmp_path):
        path = self._write_meminfo(
            tmp_path,
            "MemTotal:        8192000 kB\nCmaTotal:              0 kB\n",
        )
        assert get_mem_capacity_bytes(path) == 8192000 * 1024

    def test_cma_total_absent_falls_back_to_mem_total(self, tmp_path):
        path = self._write_meminfo(tmp_path, "MemTotal:        8192000 kB\n")
        assert get_mem_capacity_bytes(path) == 8192000 * 1024

    def test_meminfo_unreadable_returns_none(self, tmp_path):
        # Non-Linux / restricted container -> None -> caller keeps legacy path.
        assert get_mem_capacity_bytes(str(tmp_path / 'does-not-exist')) is None


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
        # Numerator: 1024 + 512 = 1536 KiB resident (from fdinfo).
        # Denominator: CmaTotal = 3072 KiB (from the proc/meminfo fixture, #3611).
        # -> 1536 / 3072 = 50%
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


# Tegra (Jetson) sysfs fallback tests against committed fixtures.
class TestTegraBackend:
    def test_is_tegra_by_name(self):
        # NVML reports names such as "Orin (nvgpu)" on Jetson.
        assert tegra.is_tegra('Orin (nvgpu)') is True  # nosec B101
        assert tegra.is_tegra('NVIDIA Tegra Xavier (nvgpu)') is True  # nosec B101

    def test_is_tegra_rejects_discrete(self):
        # A discrete GPU name with no Tegra sysfs node must not trigger.
        assert tegra.is_tegra('NVIDIA GeForce RTX 4090', gpu_device_folder='/nope') is False  # nosec B101

    def test_is_tegra_by_sysfs(self):
        assert tegra.is_tegra(None, gpu_device_folder=TEGRA_GPU_FOLDER) is True  # nosec B101
        assert tegra.is_tegra(None, gpu_device_folder='/this/does/not/exist') is False  # nosec B101

    def test_proc_permille_to_percent(self):
        # Fixture load node holds 774 per-mille -> 77 %.
        assert tegra.get_proc(gpu_device_folder=TEGRA_GPU_FOLDER) == 77  # nosec B101

    def test_proc_missing_node(self):
        assert tegra.get_proc(gpu_device_folder='/this/does/not/exist') is None  # nosec B101

    def test_temperature_picks_gpu_thermal_zone(self):
        # Must select the gpu-thermal zone (51312 -> 51 C), not cpu/soc zones.
        assert tegra.get_temperature(thermal_root=TEGRA_THERMAL_ROOT) == 51  # nosec B101

    def test_temperature_missing_root(self):
        assert tegra.get_temperature(thermal_root='/this/does/not/exist') is None  # nosec B101


@pytest.fixture
def intel_gpu():
    """Return an IntelGPU instance wired to the test fixtures."""
    return IntelGPU(drm_root_folder=INTEL_DRM_ROOT, proc_root_folder=INTEL_PROC_ROOT)


# Intel (i915/xe) fdinfo engine-busy tests against committed fixtures.
class TestIntelFdinfoParser:
    """Unit tests for the Intel fdinfo parser (pure, no I/O)."""

    def test_valid_i915_record(self):
        text = (
            "pos:\t0\n"
            "drm-driver:\ti915\n"
            "drm-pdev:\t0000:00:02.0\n"
            "drm-engine-render:\t5000000 ns\n"
            "drm-engine-copy:\t3000000 ns\n"
            "drm-engine-video:\t0 ns\n"
            "drm-engine-capacity-video:\t2\n"
            "drm-engine-video-enhance:\t0 ns\n"
        )
        record = intel_backend.parse_fdinfo(text)
        assert record is not None
        assert record['driver'] == 'i915'
        assert record['pdev'] == '0000:00:02.0'
        # Capacity entries are counts, not time -- must be excluded.
        assert record['engine_total_ns'] == 8000000

    def test_not_a_drm_fd(self):
        assert intel_backend.parse_fdinfo("pos:\t0\nflags:\t02100002\n") is None

    def test_empty_text(self):
        assert intel_backend.parse_fdinfo("") is None

    def test_missing_driver_line(self):
        text = "pos:\t0\ndrm-pdev:\t0000:00:02.0\ndrm-engine-render:\t1 ns\n"
        assert intel_backend.parse_fdinfo(text) is None

    def test_malformed_lines_do_not_crash(self):
        text = "drm-driver:\ti915\ndrm-engine-render:\tnotanumber ns\nno-colon-here\n"
        record = intel_backend.parse_fdinfo(text)
        assert record is not None
        assert record['engine_total_ns'] == 0

    def test_non_ns_unit_ignored(self):
        text = "drm-driver:\ti915\ndrm-engine-render:\t100 ticks\n"
        record = intel_backend.parse_fdinfo(text)
        assert record is not None
        assert record['engine_total_ns'] == 0


@pytest.mark.skipif(not LINUX, reason="Intel GPU backend is Linux-only")
class TestIntelBackendDiscovery:
    """Discovery tests against the committed test fixtures."""

    def test_device_enumeration(self, intel_gpu):
        assert len(intel_gpu.device_folders) == 1
        device, driver, _pdev = intel_gpu.device_folders[0]
        assert driver == 'i915'
        assert device.endswith('card0')

    def test_stats_shape(self, intel_gpu):
        stats = intel_gpu.get_device_stats()
        assert isinstance(stats, list)
        assert len(stats) == 1
        entry = stats[0]
        for key in ('key', 'gpu_id', 'name', 'mem', 'proc', 'temperature', 'fan_speed'):
            assert key in entry
        assert entry['key'] == 'gpu_id'
        assert entry['gpu_id'] == 'intel0'

    def test_mem_from_fdinfo_resident(self, intel_gpu):
        # Numerator: 1158 + 512 = 1670 KiB resident (from fdinfo).
        # No meminfo fixture -> capacity None -> denominator is the fdinfo
        # drm-total sum: 2316 + 1024 = 3340 KiB -> 1670 / 3340 = 50%.
        stats = intel_gpu.get_device_stats()
        assert stats[0]['mem'] == 50

    def test_temp_fan_always_none(self, intel_gpu):
        stats = intel_gpu.get_device_stats()
        assert stats[0]['temperature'] is None
        assert stats[0]['fan_speed'] is None

    def test_proc_first_call_uses_freq_fallback(self, intel_gpu):
        # Delta-based engine load has no previous sample on first call,
        # so the frequency ratio (300/1450 MHz) is reported.
        stats = intel_gpu.get_device_stats()
        assert stats[0]['proc'] == INTEL_FREQ_FALLBACK

    def test_proc_second_call_is_engine_busy(self, intel_gpu):
        intel_gpu.get_device_stats()
        stats = intel_gpu.get_device_stats()
        assert isinstance(stats[0]['proc'], int)
        assert 0 <= stats[0]['proc'] <= 100


class TestIntelBackendNoHardware:
    """Backend must degrade gracefully with no hardware / no sysfs."""

    def test_missing_drm_root(self):
        backend = IntelGPU(
            drm_root_folder='/this/path/does/not/exist',
            proc_root_folder='/this/path/does/not/exist',
        )
        assert backend.device_folders == []
        assert backend.get_device_stats() == []

    def test_missing_proc_root_keeps_freq_fallback(self):
        backend = IntelGPU(
            drm_root_folder=INTEL_DRM_ROOT,
            proc_root_folder='/this/path/does/not/exist',
        )
        stats = backend.get_device_stats() if LINUX else []
        if LINUX:
            assert len(stats) == 1
            assert stats[0]['proc'] == INTEL_FREQ_FALLBACK


@pytest.mark.skipif(not LINUX, reason="Intel GPU backend is Linux-only")
class TestIntelAggregation:
    """Aggregation layer tests."""

    def test_aggregate_fdinfo_sums_engine_time(self):
        devices = intel_backend.get_device_list(INTEL_DRM_ROOT)
        per_device = intel_backend.aggregate_fdinfo(INTEL_PROC_ROOT, devices)
        assert len(per_device) == 1
        bucket = next(iter(per_device.values()))
        # Client 1: 5_000_000 + 3_000_000 + 0 + 0 = 8_000_000 ns
        # Client 2: 1_000_000 + 500_000 = 1_500_000 ns
        assert bucket['engine_total_ns'] == 9_500_000


@pytest.mark.skipif(not LINUX, reason="Intel GPU backend is Linux-only")
class TestIntelPerPid:
    """Per-PID engine-time sampler (nvtop-style source for the GPU% column)."""

    PID = 424242

    def _write_fdinfo(self, proc_root, pid, render_ns):
        fdinfo_dir = os.path.join(str(proc_root), str(pid), 'fdinfo')
        os.makedirs(fdinfo_dir, exist_ok=True)
        with open(os.path.join(fdinfo_dir, '7'), 'w') as f:
            f.write(
                "pos:\t0\n"
                "drm-driver:\ti915\n"
                "drm-pdev:\t0000:00:02.0\n"
                f"drm-engine-render:\t{render_ns} ns\n"
            )

    def test_first_sighting_reports_nothing(self, tmp_path):
        self._write_fdinfo(tmp_path, self.PID, 1_000_000)
        assert intel_backend.get_per_pid_gpu_percent(str(tmp_path)) == {}

    def test_busy_pid_reports_clamped_percent(self, tmp_path):
        self._write_fdinfo(tmp_path, self.PID, 1_000_000)
        intel_backend.get_per_pid_gpu_percent(str(tmp_path))
        # +50s of engine time: busy over any sane interval -> clamped to 100.
        self._write_fdinfo(tmp_path, self.PID, 1_000_000 + 50_000_000_000)
        result = intel_backend.get_per_pid_gpu_percent(str(tmp_path))
        assert result[self.PID] == 100

    def test_idle_pid_reports_zero(self, tmp_path):
        pid = self.PID + 1
        self._write_fdinfo(tmp_path, pid, 2_000_000)
        intel_backend.get_per_pid_gpu_percent(str(tmp_path))
        time.sleep(0.02)
        result = intel_backend.get_per_pid_gpu_percent(str(tmp_path))
        assert result[pid] == 0

    def test_stale_pids_are_pruned(self, tmp_path):
        # Empty proc root: nothing reported, previous samples dropped.
        assert intel_backend.get_per_pid_gpu_percent(str(tmp_path)) == {}

    def test_presence_detection(self):
        assert intel_backend.intel_gpu_present(INTEL_DRM_ROOT) is True
        assert intel_backend.intel_gpu_present('/this/path/does/not/exist') is False


@pytest.mark.skipif(not LINUX, reason="Intel GPU backend is Linux-only")
class TestIntelMem:
    """GPU memory (resident shared buffers) from fdinfo region counters."""

    def test_parser_sums_region_counters(self):
        text = (
            "drm-driver:\ti915\n"
            "drm-pdev:\t0000:00:02.0\n"
            "drm-total-system0:\t2316 KiB\n"
            "drm-resident-system0:\t1158 KiB\n"
            "drm-shared-system0:\t100 KiB\n"
            "drm-active-system0:\t50 KiB\n"
            "drm-engine-render:\t5 ns\n"
        )
        record = intel_backend.parse_fdinfo(text)
        assert record is not None
        # Shared/active are subsets and must not double-count.
        assert record['mem_total_bytes'] == 2316 * 1024
        assert record['mem_used_bytes'] == 1158 * 1024

    def test_parser_malformed_memory_ignored(self):
        text = "drm-driver:\ti915\ndrm-total-system0:\tnotanumber\ndrm-resident-system0:\t1 QB\n"
        record = intel_backend.parse_fdinfo(text)
        assert record is not None
        assert record['mem_total_bytes'] == 0
        assert record['mem_used_bytes'] == 0

    def test_aggregation_sums_memory(self):
        devices = intel_backend.get_device_list(INTEL_DRM_ROOT)
        per_device = intel_backend.aggregate_fdinfo(INTEL_PROC_ROOT, devices)
        bucket = next(iter(per_device.values()))
        assert bucket['mem_total_bytes'] == (2316 + 1024) * 1024
        assert bucket['mem_used_bytes'] == (1158 + 512) * 1024


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
