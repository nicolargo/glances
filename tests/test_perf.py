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
    test_duration = 12  # seconds
    perf_timer = Timer(test_duration)
    counter = 0
    from_cache = 0
    from_update = 0
    previous_interrupts_gauge = None
    while not perf_timer.finished():
        glances_stats.update()
        # interrupts_gauge should always increase
        interrupts_gauge = glances_stats.get_plugin('cpu').get_raw().get('interrupts_gauge')
        if interrupts_gauge is not None:
            if interrupts_gauge == previous_interrupts_gauge:
                from_cache += 1
            else:
                from_update += 1
                previous_interrupts_gauge = interrupts_gauge
        counter += 1
    print(f"{counter} iterations. From cache: {from_cache} | From update: {from_update}")
    assert counter > test_duration
    assert from_update < from_cache
    assert from_cache >= test_duration * 10
    assert from_update >= (test_duration / 2) - 1
