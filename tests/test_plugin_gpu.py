#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `gpu` plugin (collection)."""

from __future__ import annotations

import os
import shutil

import pytest

from glances.config import GlancesConfig
from glances.globals import LINUX
from glances.plugins.gpu.cards import intel as intel_backend
from glances.plugins.gpu.cards.intel import IntelGPU
from glances.plugins.gpu.model import PluginModel
from glances.stats_store import StatsStore

INTEL_TEST_DATA_ROOT = './tests-data/plugins/gpu/intel'
INTEL_DRM_ROOT = f'{INTEL_TEST_DATA_ROOT}/sys/class/drm'
INTEL_PROC_ROOT = f'{INTEL_TEST_DATA_ROOT}/proc'
# Fixture frequencies: 300 / 1450 MHz -> frequency fallback is 21 %.
INTEL_FREQ_FALLBACK = 21


@pytest.fixture
def store() -> StatsStore:
    return StatsStore()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfig()


class _FakeBackend:
    def __init__(self, cards):
        self._cards = cards

    def get_device_stats(self):
        return self._cards

    def exit(self):
        pass


class _BoomBackend:
    def get_device_stats(self):
        raise OSError("no device")

    def exit(self):
        pass


def _card(gpu_id="nvidia0", name="GeForce", mem=40, proc=30, temp=55):
    return {
        "key": "gpu_id",
        "gpu_id": gpu_id,
        "name": name,
        "mem": mem,
        "proc": proc,
        "temperature": temp,
        "fan_speed": 20,
    }


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "gpu"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "gpu_id"


def test_fields_watched_and_internal():
    fd = PluginModel.fields_description
    for key in ("proc", "mem", "temperature"):
        assert fd[key]["watched"] is True
        assert fd[key]["watch_direction"] == "high"
        assert set(fd[key]["default_thresholds"]) == {"careful", "warning", "critical"}
    assert fd["gpu_id"].get("primary_key") is True
    assert fd["name"].get("internal") is True
    assert fd["fan_speed"].get("internal") is True
    assert fd["fan_speed"].get("watched", False) is False


def test_gpu_temperature_thresholds_mirror_v4():
    t = PluginModel.fields_description["temperature"]["default_thresholds"]
    assert t == {"careful": 60.0, "warning": 70.0, "critical": 80.0}


@pytest.mark.asyncio
async def test_grab_stats_concatenates_backends(store, config):
    p = PluginModel(store, config)
    p._backends = [
        _FakeBackend([_card("nvidia0", "A")]),
        _FakeBackend([_card("amd0", "B")]),
    ]
    out = await p._grab_stats()
    assert [c["gpu_id"] for c in out] == ["nvidia0", "amd0"]


@pytest.mark.asyncio
async def test_grab_stats_survives_backend_failure(store, config):
    p = PluginModel(store, config)
    p._backends = [_BoomBackend(), _FakeBackend([_card("amd0", "B")])]
    out = await p._grab_stats()
    assert [c["gpu_id"] for c in out] == ["amd0"]


@pytest.mark.asyncio
async def test_grab_stats_empty_when_no_backend(store, config):
    p = PluginModel(store, config)
    p._backends = []
    assert await p._grab_stats() == []


class _ExitSpy(_FakeBackend):
    def __init__(self, calls, error=None):
        super().__init__([])
        self._calls = calls
        self._error = error

    def exit(self):
        self._calls.append(self)
        if self._error:
            raise self._error


def test_stop_calls_every_backend_exit_even_if_one_raises(store, config):
    """v4 `exit()` closes each card API (nvmlShutdown...) on shutdown; one
    failing must not leave the others open."""
    calls = []
    p = PluginModel(store, config)
    p._backends = [_ExitSpy(calls, OSError("nvml")), _ExitSpy(calls)]
    p.stop()
    assert calls == p._backends


def test_build_backends_skips_a_constructor_that_raises(monkeypatch):
    """v5 form of v4's None backend: a vendor whose init fails is left out."""
    from glances.plugins.gpu import model
    from glances.plugins.gpu.cards import nvidia

    def boom():
        raise RuntimeError("no driver")

    monkeypatch.setattr(nvidia, "NvidiaGPU", boom)
    names = [type(b).__name__ for b in model._build_backends()]
    assert names == ["AmdGPU", "IntelGPU", "ArmGPU"]


def test_intel_temperature_from_hwmon(tmp_path):
    """Intel temperature is the mean of hwmon temp*_input; absent hwmon -> None."""
    from glances.plugins.gpu.cards import intel

    card = tmp_path / "card0"
    (card / "device" / "hwmon" / "hwmon3").mkdir(parents=True)
    (card / "gt_act_freq_mhz").write_text("300\n")
    (card / "gt_max_freq_mhz").write_text("2000\n")
    assert intel.get_temperature(str(card)) is None

    (card / "device" / "hwmon" / "hwmon3" / "temp1_input").write_text("41000\n")
    assert intel.get_temperature(str(card)) == 41

    (card / "device" / "hwmon" / "hwmon3" / "temp2_input").write_text("45000\n")
    assert intel.get_temperature(str(card)) == 43


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

    def test_mem_temp_fan_none_without_sensors(self, intel_gpu):
        stats = intel_gpu.get_device_stats()
        assert stats[0]['mem'] is None
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
class TestIntelIdleAndPartialScan:
    """Idle GPUs read 0; an incomplete /proc view never claims it."""

    @staticmethod
    def _backend(proc_root):
        return IntelGPU(drm_root_folder=INTEL_DRM_ROOT, proc_root_folder=str(proc_root))

    @staticmethod
    def _idle_proc(tmp_path):
        # One process, no DRM fd: what a discrete card with no client looks like.
        fdinfo = tmp_path / 'proc' / '42' / 'fdinfo'
        fdinfo.mkdir(parents=True)
        (fdinfo / '0').write_text('pos:\t0\nflags:\t02\n')
        fd = tmp_path / 'proc' / '42' / 'fd'
        fd.mkdir()
        (fd / '0').symlink_to('/dev/null')
        return tmp_path / 'proc'

    def test_idle_gpu_reports_zero(self, tmp_path):
        backend = self._backend(self._idle_proc(tmp_path))
        assert backend.get_device_stats()[0]['proc'] == INTEL_FREQ_FALLBACK
        assert backend.get_device_stats()[0]['proc'] == 0

    def test_client_exit_reports_zero_not_frequency(self, tmp_path):
        proc = tmp_path / 'proc'
        shutil.copytree(INTEL_PROC_ROOT, proc, symlinks=True)
        backend = self._backend(proc)
        backend.get_device_stats()
        shutil.rmtree(proc / '1234')
        shutil.rmtree(proc / '5678')
        assert backend.get_device_stats()[0]['proc'] == 0

    def test_unreadable_process_keeps_frequency_fallback(self, tmp_path, monkeypatch):
        proc = self._idle_proc(tmp_path)
        real_listdir = os.listdir

        def listdir(path):
            if str(path).endswith(os.path.join('42', 'fd')):
                raise PermissionError(path)
            return real_listdir(path)

        monkeypatch.setattr(intel_backend.os, 'listdir', listdir)
        backend = self._backend(proc)
        backend.get_device_stats()
        # Cannot tell idle from invisible: never report 0.
        assert backend.get_device_stats()[0]['proc'] == INTEL_FREQ_FALLBACK

    def test_aggregate_complete_scan_zero_fills_idle_device(self, tmp_path):
        devices = intel_backend.get_device_list(INTEL_DRM_ROOT)
        per_device = intel_backend.aggregate_fdinfo(str(self._idle_proc(tmp_path)), devices)
        assert per_device == {devices[0][0]: {'engine_total_ns': 0}}

    def test_aggregate_skips_non_drm_fd(self, tmp_path):
        # The fdinfo of an fd not pointing into /dev/dri/ is never read.
        proc = self._idle_proc(tmp_path)
        (proc / '42' / 'fdinfo' / '0').write_text('drm-driver:\ti915\ndrm-engine-render:\t7 ns\n')
        devices = intel_backend.get_device_list(INTEL_DRM_ROOT)
        per_device = intel_backend.aggregate_fdinfo(str(proc), devices)
        assert per_device == {devices[0][0]: {'engine_total_ns': 0}}

    def test_aggregate_counts_shared_client_once(self, tmp_path):
        # dup()/fork() expose one DRM client on several fds: count it once.
        proc = tmp_path / 'proc'
        shutil.copytree(INTEL_PROC_ROOT, proc, symlinks=True)
        (proc / '1234' / 'fd' / '8').symlink_to('/dev/dri/renderD128')
        shutil.copy(proc / '1234' / 'fdinfo' / '7', proc / '1234' / 'fdinfo' / '8')
        devices = intel_backend.get_device_list(INTEL_DRM_ROOT)
        per_device = intel_backend.aggregate_fdinfo(str(proc), devices)
        assert next(iter(per_device.values()))['engine_total_ns'] == 9_500_000


class _HwmonBackend(_FakeBackend):
    # Stands for AmdGPU / IntelGPU: temperature read from hwmon, so the
    # sensors plugin already shows it.
    TEMPERATURE_IN_SENSORS = True


@pytest.mark.asyncio
async def test_cards_whose_temperature_is_in_sensors_hide_it(store, config):
    p = PluginModel(store, config)
    p._hide_temperature = False  # `config` may read the maintainer's own conf
    p._backends = [_FakeBackend([_card("nvidia0", "A")]), _HwmonBackend([_card("intel0", "B")])]
    out = await p._grab_stats()
    assert {c["gpu_id"]: c["hide_temperature"] for c in out} == {"nvidia0": False, "intel0": True}
    # The value itself is still collected (API, exports, thresholds).
    assert all(c["temperature"] == 55 for c in out)


@pytest.mark.asyncio
async def test_hide_temperature_key_hides_it_for_every_card(store, tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    conf = tmp_path / "glances.conf"
    conf.write_text("[gpu]\nhide_temperature=True\n")
    p = PluginModel(store, GlancesConfig(str(conf)))
    p._backends = [_FakeBackend([_card("nvidia0", "A")]), _HwmonBackend([_card("intel0", "B")])]
    out = await p._grab_stats()
    assert [c["hide_temperature"] for c in out] == [True, True]


def test_card_backends_declare_sensors_coverage():
    # hwmon-backed vendors only: NVML/Tegra and the ARM SoC-zone fallback are
    # not guaranteed to appear in psutil.sensors_temperatures().
    from glances.plugins.gpu.cards.amd import AmdGPU
    from glances.plugins.gpu.cards.arm import ArmGPU
    from glances.plugins.gpu.cards.nvidia import NvidiaGPU

    assert AmdGPU.TEMPERATURE_IN_SENSORS is True
    assert IntelGPU.TEMPERATURE_IN_SENSORS is True
    assert NvidiaGPU.TEMPERATURE_IN_SENSORS is False
    assert ArmGPU.TEMPERATURE_IN_SENSORS is False
