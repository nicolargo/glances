#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage Glances event class

This class is a data class for the Glances event.

event_state = "OK|CAREFUL|WARNING|CRITICAL"
event_type = "CPU*|LOAD|MEM|MON"
event_value = value

Item (or event) is defined by:
    {
        "begin": "begin",
        "end": "end",
        "state": "WARNING|CRITICAL",
        "type": "CPU|LOAD|MEM",
        "max": MAX,
        "avg": AVG,
        "min": MIN,
        "sum": SUM,
        "count": COUNT,
        "top": [top 3 process name],
        "desc": "Processes description",
        "sort": "top sort key",
        "global": "global alert message"
    }
"""

from glances.logger import logger

try:
    from pydantic.dataclasses import dataclass
except ImportError as e:
    logger.warning(f"Missing Python Lib ({e}), EventList will be skipping data validation")
    from dataclasses import dataclass

from glances.processes import sort_stats


@dataclass
class GlancesEvent:
    begin: int
    state: str
    type: str
    min: float
    max: float
    sum: float
    count: int
    avg: float
    top: list
    desc: str
    sort: str
    global_msg: str
    end: int = -1

    def is_ongoing(self):
        """Return True if the event is ongoing"""
        return self.end == -1

    def is_finished(self):
        """Return True if the event is finished"""
        return self.end != -1

    def update(
        self,
        state: str,
        value: float,
        sort_key: str = None,
        proc_list: list = None,
        proc_desc: str = None,
        global_msg: str = None,
    ):
        """Update an ongoing event"""

        self.end = -1

        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.sum += value
        self.count += 1
        self.avg = self.sum / self.count

        if state == "CRITICAL":
            # Avoid to change from CRITICAL to WARNING
            # If an events have reached the CRITICAL state, it can't go back to WARNING
            self.state = state
            # TOP PROCESS LIST (only for CRITICAL ALERT)
            self.sort = sort_key
            self.top = [p['name'] for p in sort_stats(proc_list, sort_key)[0:3]]

        # MONITORED PROCESSES DESC
        self.desc = proc_desc

        # Global message
        self.global_msg = global_msg
