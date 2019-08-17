# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Alert plugin."""

from datetime import datetime

from glances.logger import logger
from glances.events import glances_events
from glances.thresholds import glances_thresholds
# from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin

# Static decision tree for the global alert message
# - msg: Message to be displayed (result of the decision tree)
# - threasholds: a list of stats to take into account
# - thresholds_min: minimal value of the threasholds sum
# -                 0: OK
# -                 1: CAREFUL
# -                 2: WARNING
# -                 3: CRITICAL
tree = [{'msg': 'No warning or critical alert detected',
         'thresholds': [],
         'thresholds_min': 0},
        {'msg': 'High CPU user mode',
         'thresholds': ['cpu_user'],
         'thresholds_min': 2},
        {'msg': 'High CPU kernel usage',
         'thresholds': ['cpu_system'],
         'thresholds_min': 2},
        {'msg': 'High CPU I/O waiting',
         'thresholds': ['cpu_iowait'],
         'thresholds_min': 2},
        {'msg': 'Large CPU stolen time. System running the hypervisor is too busy.',
         'thresholds': ['cpu_steal'],
         'thresholds_min': 2},
        {'msg': 'High CPU niced value',
         'thresholds': ['cpu_niced'],
         'thresholds_min': 2},
        {'msg': 'System overloaded in the last 5 minutes',
         'thresholds': ['load'],
         'thresholds_min': 2},
        {'msg': 'High swap (paging) usage',
         'thresholds': ['memswap'],
         'thresholds_min': 2},
        {'msg': 'High memory consumption',
         'thresholds': ['mem'],
         'thresholds_min': 2},
        ]


def global_message():
    """Parse the decision tree and return the message.

    Note: message corresponding to the current threasholds values
    """
    # Compute the weight for each item in the tree
    current_thresholds = glances_thresholds.get()
    for i in tree:
        i['weight'] = sum([current_thresholds[t].value() for t in i['thresholds'] if t in current_thresholds])
    themax = max(tree, key=lambda d: d['weight'])
    if themax['weight'] >= themax['thresholds_min']:
        # Check if the weight is > to the minimal threashold value
        return themax['msg']
    else:
        return tree[0]['msg']


class Plugin(GlancesPlugin):
    """Glances alert plugin.

    Only for display.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'bottom'

    def update(self):
        """Nothing to do here. Just return the global glances_log."""
        # Set the stats to the glances_events
        self.stats = glances_events.get()
        # Define the global message thanks to the current thresholds
        # and the decision tree
        # !!! Call directly in the msg_curse function
        # global_message()

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if display plugin enable...
        if not self.stats or self.is_disable():
            return ret

        # Build the string message
        # Header
        ret.append(self.curse_add_line(global_message(), "TITLE"))
        # Loop over alerts
        for alert in self.stats:
            # New line
            ret.append(self.curse_new_line())
            # Start
            msg = str(datetime.fromtimestamp(alert[0]))
            ret.append(self.curse_add_line(msg))
            # Duration
            if alert[1] > 0:
                # If finished display duration
                msg = ' ({})'.format(datetime.fromtimestamp(alert[1]) -
                                     datetime.fromtimestamp(alert[0]))
            else:
                msg = ' (ongoing)'
            ret.append(self.curse_add_line(msg))
            ret.append(self.curse_add_line(" - "))
            # Infos
            if alert[1] > 0:
                # If finished do not display status
                msg = '{} on {}'.format(alert[2], alert[3])
                ret.append(self.curse_add_line(msg))
            else:
                msg = str(alert[3])
                ret.append(self.curse_add_line(msg, decoration=alert[2]))
            # Min / Mean / Max
            if self.approx_equal(alert[6], alert[4], tolerance=0.1):
                msg = ' ({:.1f})'.format(alert[5])
            else:
                msg = ' (Min:{:.1f} Mean:{:.1f} Max:{:.1f})'.format(
                    alert[6], alert[5], alert[4])
            ret.append(self.curse_add_line(msg))
            # Top processes
            top_process = ', '.join([p['name'] for p in alert[9]])
            if top_process != '':
                msg = ': {}'.format(top_process)
                ret.append(self.curse_add_line(msg))

        return ret

    def approx_equal(self, a, b, tolerance=0.0):
        """Compare a with b using the tolerance (if numerical)."""
        if str(int(a)).isdigit() and str(int(b)).isdigit():
            return abs(a - b) <= max(abs(a), abs(b)) * tolerance
        else:
            return a == b
