#!/usr/bin/env python
#
# SPDX-FileCopyrightText: 2026 Aditya Raj Singh <aditya@bncw.in>
#
# SPDX-License-Identifier: LGPL-3.0-only

from collections import namedtuple
from unittest.mock import patch

from glances.cpu_percent import cpu_percent


def test_percpu_uses_guest_nice_value():
    cpu_times_type = namedtuple(
        'scputimes',
        'user nice system idle iowait irq softirq steal guest guest_nice',
    )
    cpu_times = cpu_times_type(
        user=1.0,
        nice=2.0,
        system=3.0,
        idle=4.0,
        iowait=5.0,
        irq=6.0,
        softirq=7.0,
        steal=8.0,
        guest=9.0,
        guest_nice=10.0,
    )

    with patch('glances.cpu_percent.psutil.cpu_times_percent', return_value=[cpu_times]):
        stats = cpu_percent._compute_percpu()

    assert stats[0]['steal'] == 8.0
    assert stats[0]['guest_nice'] == 10.0
