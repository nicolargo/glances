#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for Glances perf."""

from glances.timer import Timer


def test_perf_update(glances_stats):
    """
    Test Glances perf.
    """
    perf_timer = Timer(6)
    counter = 0
    while not perf_timer.finished():
        glances_stats.update()
        counter += 1
    assert counter > 6
