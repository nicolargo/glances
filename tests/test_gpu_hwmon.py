#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 snowyukitty
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""GPU telemetry must not depend on hwmon device numbering."""

import pytest

from glances.plugins.gpu.cards import amd, arm


@pytest.mark.parametrize('index', [0, 9, 10, 123])
@pytest.mark.parametrize('backend', [amd, arm], ids=['amd', 'arm'])
def test_temperature_hwmon_index(tmp_path, index, backend):
    card = tmp_path / 'card0'
    device = card / 'device'
    hwmon = device / 'hwmon' / f'hwmon{index}'
    hwmon.mkdir(parents=True)
    (hwmon / 'temp1_input').write_text('40000')
    (hwmon / 'temp2_input').write_text('60000')

    assert backend.get_temperature(str(device if backend is amd else card)) == 50


@pytest.mark.parametrize('index', [0, 9, 10, 123])
@pytest.mark.parametrize('integrated', [False, True], ids=['discrete', 'integrated'])
def test_amd_memory_hwmon_index(tmp_path, index, integrated):
    device = tmp_path / 'card0' / 'device'
    hwmon = device / 'hwmon' / f'hwmon{index}'
    hwmon.mkdir(parents=True)
    (device / 'gpu_busy_percent').write_text('10')
    (device / 'mem_info_vram_total').write_text('100')
    (device / 'mem_info_vram_used').write_text('20')
    (device / 'mem_info_gtt_total').write_text('300')
    (device / 'mem_info_gtt_used').write_text('180')
    if integrated:
        (hwmon / 'in1_input').write_text('900')

    stats = amd.AmdGPU(drm_root_folder=str(tmp_path)).get_device_stats()

    assert len(stats) == 1
    assert stats[0]['mem'] == (50 if integrated else 20)
    assert stats[0]['proc'] == 10


@pytest.mark.parametrize('backend', [amd, arm], ids=['amd', 'arm'])
def test_temperature_without_hwmon(tmp_path, backend):
    assert backend.get_temperature(str(tmp_path)) is None
