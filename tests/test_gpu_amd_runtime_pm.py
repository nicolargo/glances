#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Glances contributors
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""AMD GPU sampling while runtime power management suspends the device."""

import builtins
import errno
from pathlib import Path
from unittest.mock import mock_open

import pytest

from glances.plugins.gpu.cards import amd


@pytest.mark.parametrize('busy_sensors', [('proc',), ('temperature',), ('proc', 'temperature')])
def test_suspended_gpu_keeps_available_metrics_and_recovers(tmp_path, monkeypatch, busy_sensors):
    device = tmp_path / 'card0' / 'device'
    hwmon = device / 'hwmon' / 'hwmon0'
    hwmon.mkdir(parents=True)
    proc = device / amd.GPU_PROC_PERCENT
    temperature = hwmon / 'temp1_input'
    for path, value in (
        (proc, '42'),
        (temperature, '56000'),
        (device / amd.GPU_MEM_TOTAL, '1000'),
        (device / amd.GPU_MEM_USED, '250'),
    ):
        path.write_text(value)

    blocked_paths = {path for sensor, path in (('proc', proc), ('temperature', temperature)) if sensor in busy_sensors}
    suspended = True
    busy_file = mock_open()
    busy_file.return_value.read.side_effect = OSError(errno.EBUSY, 'Device or resource busy')

    def open_sensor(path, *args, **kwargs):
        if suspended and Path(path) in blocked_paths:
            return busy_file(path, *args, **kwargs)
        return builtins.open(path, *args, **kwargs)

    monkeypatch.setattr(amd, 'open', open_sensor, raising=False)
    gpu = amd.AmdGPU(drm_root_folder=str(tmp_path))
    expected = {
        'key': 'gpu_id',
        'gpu_id': 'amd0',
        'name': 'AMD GPU',
        'mem': 25,
        'proc': None if 'proc' in busy_sensors else 42,
        'temperature': None if 'temperature' in busy_sensors else 56,
        'fan_speed': None,
    }
    assert gpu.get_device_stats() == [expected]

    suspended = False
    assert gpu.get_device_stats() == [{**expected, 'proc': 42, 'temperature': 56}]
