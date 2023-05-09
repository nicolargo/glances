# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Alert plugin."""

from datetime import datetime

from glances.events import glances_events
from glances.thresholds import glances_thresholds

# from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Static decision tree for the global alert message
# - msg: Message to be displayed (result of the decision tree)
# - thresholds: a list of stats to take into account
# - thresholds_min: minimal value of the thresholds sum
# -                 0: OK
# -                 1: CAREFUL
# -                 2: WARNING
# -                 3: CRITICAL
tree = [
    {'msg': 'No warning or critical alert detected', 'thresholds': [], 'thresholds_min': 0},
    {'msg': 'High CPU user mode', 'thresholds': ['cpu_user'], 'thresholds_min': 2},
    {'msg': 'High CPU kernel usage', 'thresholds': ['cpu_system'], 'thresholds_min': 2},
    {'msg': 'High CPU I/O waiting', 'thresholds': ['cpu_iowait'], 'thresholds_min': 2},
    {
        'msg': 'Large CPU stolen time. System running the hypervisor is too busy.',
        'thresholds': ['cpu_steal'],
        'thresholds_min': 2,
    },
    {'msg': 'High CPU niced value', 'thresholds': ['cpu_niced'], 'thresholds_min': 2},
    {'msg': 'System overloaded in the last 5 minutes', 'thresholds': ['load'], 'thresholds_min': 2},
    {'msg': 'High swap (paging) usage', 'thresholds': ['memswap'], 'thresholds_min': 2},
    {'msg': 'High memory consumption', 'thresholds': ['mem'], 'thresholds_min': 2},
]

# TODO: change the algo to use the following decision tree
# Source: Inspire by https://scoutapm.com/blog/slow_server_flow_chart
# _yes means threshold >= 2
# _no  means threshold < 2
# With threshold:
# - 0: OK
# - 1: CAREFUL
# - 2: WARNING
# - 3: CRITICAL
tree_new = {
    'cpu_iowait': {
        '_yes': {
            'memswap': {
                '_yes': {
                    'mem': {
                        '_yes': {
                            # Once you've identified the offenders, the resolution will again
                            # depend on whether their memory usage seems business-as-usual or not.
                            # For example, a memory leak can be satisfactorily addressed by a one-time
                            # or periodic restart of the process.
                            # - if memory usage seems anomalous: kill the offending processes.
                            # - if memory usage seems business-as-usual: add RAM to the server,
                            # or split high-memory using services to other servers.
                            '_msg': "Memory issue"
                        },
                        '_no': {
                            # ???
                            '_msg': "Swap issue"
                        },
                    }
                },
                '_no': {
                    # Low swap means you have a "real" IO wait problem. The next step is to see what's hogging your IO.
                    # iotop is an awesome tool for identifying io offenders. Two things to note:
                    # unless you've already installed iotop, it's probably not already on your system.
                    # Recommendation: install it before you need it - - it's no fun trying to install a troubleshooting
                    # tool on an overloaded machine (iotop requires a Linux of 2.62 or above)
                    '_msg': "I/O issue"
                },
            }
        },
        '_no': {
            'cpu_total': {
                '_yes': {
                    'cpu_user': {
                        '_yes': {
                            # We expect the user-time percentage to be high.
                            # There's most likely a program or service you've configured on you server that's
                            # hogging CPU.
                            # Checking the % user time just confirms this. When you see that the % user-time is high,
                            # it's time to see what executable is monopolizing the CPU
                            # Once you've confirmed that the % usertime is high, check the process list(also provided
                            # by top).
                            # Be default, top sorts the process list by % CPU, so you can just look at the top process
                            # or processes.
                            # If there's a single process hogging the CPU in a way that seems abnormal, it's an
                            # anomalous situation
                            # that a service restart can fix. If there are are multiple processes taking up CPU
                            # resources, or it
                            # there's one process that takes lots of resources while otherwise functioning normally,
                            # than your setup
                            # may just be underpowered. You'll need to upgrade your server(add more cores),
                            # or split services out onto
                            # other boxes. In either case, you have a resolution:
                            # - if situation seems anomalous: kill the offending processes.
                            # - if situation seems typical given history: upgrade server or add more servers.
                            '_msg': "CPU issue with user process(es)"
                        },
                        '_no': {
                            'cpu_steal': {
                                '_yes': {
                                    '_msg': "CPU issue with stolen time. System running the hypervisor may be too busy."
                                },
                                '_no': {'_msg': "CPU issue with system process(es)"},
                            }
                        },
                    }
                },
                '_no': {
                    '_yes': {
                        # ???
                        '_msg': "Memory issue"
                    },
                    '_no': {
                        # Your slowness isn't due to CPU or IO problems, so it's likely an application-specific issue.
                        # It's also possible that the slowness is being caused by another server in your cluster, or
                        # by an external service you rely on.
                        # start by checking important applications for uncharacteristic slowness(the DB is a good place
                        # to start), think through which parts of your infrastructure could be slowed down externally.
                        # For example, do you use an externally hosted email service that could slow down critical
                        # parts of your application ?
                        # If you suspect another server in your cluster, strace and lsof can provide information on
                        # what the process is doing or waiting on. Strace will show you which file descriptors are
                        # being read or written to (or being attempted to be read from) and lsof can give you a
                        # mapping of those file descriptors to network connections.
                        '_msg': "External issue"
                    },
                },
            }
        },
    }
}


def global_message():
    """Parse the decision tree and return the message.

    Note: message corresponding to the current thresholds values
    """
    # Compute the weight for each item in the tree
    current_thresholds = glances_thresholds.get()
    for i in tree:
        i['weight'] = sum([current_thresholds[t].value() for t in i['thresholds'] if t in current_thresholds])
    themax = max(tree, key=lambda d: d['weight'])
    if themax['weight'] >= themax['thresholds_min']:
        # Check if the weight is > to the minimal threshold value
        return themax['msg']
    else:
        return tree[0]['msg']


class PluginModel(GlancesPluginModel):
    """Glances alert plugin.

    Only for display.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(args=args, config=config, stats_init_value=[])

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
        if not self.stats or self.is_disabled():
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
                msg = ' ({})'.format(datetime.fromtimestamp(alert[1]) - datetime.fromtimestamp(alert[0]))
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
                msg = ' (Min:{:.1f} Mean:{:.1f} Max:{:.1f})'.format(alert[6], alert[5], alert[4])
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
