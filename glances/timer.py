#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The timer manager."""

from datetime import datetime
from time import time

# Global list to manage the elapsed time
last_update_times = {}


def getTimeSinceLastUpdate(IOType):
    """Return the elapsed time since last update."""
    global last_update_times
    # assert(IOType in ['net', 'disk', 'process_disk'])
    current_time = time()
    last_time = last_update_times.get(IOType)
    if not last_time:
        time_since_update = 1
    else:
        time_since_update = current_time - last_time
    last_update_times[IOType] = current_time
    return time_since_update


class Timer:
    """The timer class. A simple chronometer."""

    def __init__(self, duration):
        self.duration = duration
        self.start()

    def start(self):
        self.target = time() + self.duration

    def reset(self, duration=None):
        if duration is not None:
            self.set(duration)
        self.start()

    def get(self):
        return self.duration - (self.target - time())

    def set(self, duration):
        self.duration = duration

    def finished(self):
        return time() > self.target


class Counter:
    """The counter class."""

    def __init__(self):
        self.start()

    def start(self):
        self.target = datetime.now()

    def reset(self):
        self.start()

    def get(self):
        return (datetime.now() - self.target).total_seconds()
