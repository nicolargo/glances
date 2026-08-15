#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for Glances memory leak."""

import time
import tracemalloc


def test_memoryleak_no_history(glances_stats_no_history, logger):
    """
    Test Glances memory leak.
    """
    tracemalloc.start()
    # First iterations just to init the stats and fill the memory
    logger.info('Please wait during memory leak test initialisation')
    iteration = 3
    for _ in range(iteration):
        glances_stats_no_history.update()
        time.sleep(1)

    # Then iteration to measure memory leak
    logger.info('Please wait during memory leak test')
    iteration = 10
    snapshot_begin = tracemalloc.take_snapshot()
    for _ in range(iteration):
        glances_stats_no_history.update()
        time.sleep(1)
    snapshot_end = tracemalloc.take_snapshot()
    snapshot_diff = snapshot_end.compare_to(snapshot_begin, 'filename')
    memory_leak = sum([s.size_diff for s in snapshot_diff]) // iteration
    logger.info(f'Memory consume per iteration: {memory_leak} bytes')
    assert memory_leak < 15000, f'Memory leak: {memory_leak} bytes'
