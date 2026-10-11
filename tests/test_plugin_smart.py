#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the SMART data reader."""

import glances.plugins.smart.data as smart_data


def test_missing_smartctl_returns_no_device(monkeypatch):
    """pySMART >= 1.4 raises FileNotFoundError when smartctl is not installed:
    it must not crash the Glances update (it killed the Web server at startup)."""

    def no_smartctl():
        raise FileNotFoundError("Command smartctl doesn't exist!")

    monkeypatch.setattr(smart_data, 'DeviceList', no_smartctl)
    monkeypatch.setattr(smart_data, 'import_error_tag', False)
    assert smart_data.get_smart_data([]) == []
    assert smart_data.import_error_tag is True
