#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for Glances memory leak."""

import tracemalloc


def test_memoryleak(glances_stats_no_history, logger):
    """
    Test Glances memory leak.
    """
    tracemalloc.start()
    # First iterations just to init the stats and fill the memory
    logger.info('Please wait test is filling memory with stats')
    iteration = 100
    for _ in range(iteration):
        glances_stats_no_history.update()

    # Then iteration to measure memory leak
    logger.info('Please wait test if a memory leak is detected')
    iteration = 20
    snapshot_begin = tracemalloc.take_snapshot()
    for _ in range(iteration):
        glances_stats_no_history.update()
    snapshot_end = tracemalloc.take_snapshot()
    snapshot_diff = snapshot_end.compare_to(snapshot_begin, 'filename')
    memory_leak = sum([s.size_diff for s in snapshot_diff]) // iteration
    logger.info('Memory consume per iteration: {memory_leak} bytes')
    assert memory_leak < 1000, f'Memory leak: {memory_leak} bytes'
