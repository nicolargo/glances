#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the SMART data reader."""

import logging
from functools import partial
from types import SimpleNamespace

import pytest

import glances.plugins.smart.data as smart_data


def test_missing_smartctl_returns_no_device(monkeypatch):
    """pySMART >= 1.4 raises FileNotFoundError when smartctl is not installed:
    it must not crash the Glances update (it killed the Web server at startup)."""

    def no_smartctl(**kwargs):
        raise FileNotFoundError("Command smartctl doesn't exist!")

    monkeypatch.setattr(smart_data, 'DeviceList', no_smartctl, raising=False)  # absent without pySMART
    monkeypatch.setattr(smart_data, 'import_error_tag', False)
    assert smart_data.get_smart_data([]) == []
    assert smart_data.import_error_tag is True


@pytest.fixture
def mixed_smart_devices(monkeypatch):
    """Drive real pySMART scanning with healthy and unsupported devices."""
    pySMART = pytest.importorskip('pySMART')

    def scan():
        return [
            '/dev/nvme0 -d nvme # ...',
            '/dev/sda -d usbsunplus # /dev/sda [USB Sunplus], ATA device',
            '/dev/sdb -d usbjmicron # /dev/sdb [USB JMicron], ATA device',
        ]

    fake_smartctl = SimpleNamespace(scan=scan)

    def fake_device(name, interface=None, smartctl=None):
        if interface in ('usbsunplus', 'usbjmicron'):
            raise ValueError(f'Unknown interface: {interface} specified for {name}')
        return SimpleNamespace(
            name=name.removeprefix('/dev/'),
            model='Test NVMe',
            interface=interface,
            capacity='500 GB',
            serial='test-serial',
            attributes=[],
            if_attributes=None,
        )

    monkeypatch.setattr(pySMART.device_list, 'Device', fake_device)
    monkeypatch.setattr(smart_data, 'DeviceList', partial(pySMART.DeviceList, smartctl=fake_smartctl))
    monkeypatch.setattr(smart_data, 'import_error_tag', False)
    monkeypatch.setattr(smart_data, '_skipped_devices', set(), raising=False)
    return fake_device


def test_unknown_interface_skips_device_keeps_others(mixed_smart_devices):
    """Issue #3806: an unknown interface must not hide healthy SMART devices."""

    result = smart_data.get_smart_data([])

    assert [device['DeviceName'] for device in result] == ['nvme0 Test NVMe']
    assert smart_data.import_error_tag is False


def test_device_list_value_error_disables_plugin(monkeypatch):
    """Issue #3806: a whole-list ValueError must disable SMART without crashing."""

    def broken(**kwargs):
        raise ValueError('Unable to initialize SMART device list')

    monkeypatch.setattr(smart_data, 'DeviceList', broken, raising=False)
    monkeypatch.setattr(smart_data, 'import_error_tag', False)

    assert smart_data.get_smart_data([]) == []
    assert smart_data.import_error_tag is True


def test_skipped_device_logs_one_warning_without_traceback(mixed_smart_devices, caplog):
    """Issue #3806: repeated refreshes must warn once without pySMART tracebacks."""
    with caplog.at_level(logging.DEBUG):
        first_result = smart_data.get_smart_data([])
        second_result = smart_data.get_smart_data([])

    assert [device['DeviceName'] for device in first_result] == ['nvme0 Test NVMe']
    assert [device['DeviceName'] for device in second_result] == ['nvme0 Test NVMe']
    assert not any(record.getMessage().startswith('Error parsing device') for record in caplog.records)
    for device, interface in (('/dev/sda', 'usbsunplus'), ('/dev/sdb', 'usbjmicron')):
        warnings = [
            record for record in caplog.records if record.levelno == logging.WARNING and device in record.getMessage()
        ]
        assert len(warnings) == 1
        assert f'Unknown interface: {interface} specified for {device}' in warnings[0].getMessage()
        assert warnings[0].exc_info is None


def test_root_logger_filters_restored(mixed_smart_devices, monkeypatch):
    """Issue #3806: SMART scanning must restore root filters on success or failure."""
    root_logger = logging.getLogger()
    filters_before = list(root_logger.filters)

    smart_data.get_smart_data([])
    assert root_logger.filters == filters_before

    def broken(**kwargs):
        raise ValueError('Unable to initialize SMART device list')

    monkeypatch.setattr(smart_data, 'DeviceList', broken)
    assert smart_data.get_smart_data([]) == []
    assert root_logger.filters == filters_before


def test_unrelated_root_errors_not_suppressed(mixed_smart_devices, monkeypatch, caplog):
    """Issue #3806: suppressing pySMART noise must preserve unrelated root errors."""
    pySMART = pytest.importorskip('pySMART')

    def fake_device(name, interface=None, smartctl=None):
        if interface == 'nvme':
            logging.getLogger().error('unrelated error')
        return mixed_smart_devices(name, interface=interface, smartctl=smartctl)

    monkeypatch.setattr(pySMART.device_list, 'Device', fake_device)
    with caplog.at_level(logging.DEBUG):
        smart_data.get_smart_data([])

    assert any(
        record.name == 'root' and record.levelno == logging.ERROR and record.getMessage() == 'unrelated error'
        for record in caplog.records
    )


@pytest.mark.parametrize('malformed_first', [True, False], ids=['malformed-message', 'missing-exception'])
def test_filter_never_raises(mixed_smart_devices, monkeypatch, caplog, malformed_first):
    """Issue #3806: unexpected root records must not interrupt healthy SMART devices."""
    pySMART = pytest.importorskip('pySMART')
    root_logger = logging.getLogger()
    # Handlers may reject the malformed message; only filter failures are under test.
    monkeypatch.setattr(logging, 'raiseExceptions', False)

    def fake_device(name, interface=None, smartctl=None):
        if interface == 'nvme':
            record = root_logger.makeRecord(
                root_logger.name,
                logging.ERROR,
                pySMART.device_list.__file__,
                1,
                'Error parsing device /dev/sdb',
                (),
                exc_info=None,
            )
            if malformed_first:
                root_logger.info('%s %s', 'x')
                root_logger.handle(record)
            else:
                root_logger.handle(record)
                root_logger.info('%s %s', 'x')
        return mixed_smart_devices(name, interface=interface, smartctl=smartctl)

    monkeypatch.setattr(pySMART.device_list, 'Device', fake_device)
    with caplog.at_level(logging.DEBUG):
        result = smart_data.get_smart_data([])

    assert [device['DeviceName'] for device in result] == ['nvme0 Test NVMe']
    assert smart_data.import_error_tag is False
