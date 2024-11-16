#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Alert plugin."""

from datetime import datetime
from functools import reduce

from glances.events_list import glances_events

# from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# {
#     "begin": "begin",
#     "end": "end",
#     "state": "WARNING|CRITICAL",
#     "type": "CPU|LOAD|MEM",
#     "max": MAX,
#     "avg": AVG,
#     "min": MIN,
#     "sum": SUM,
#     "count": COUNT,
#     "top": [top3 process list],
#     "desc": "Processes description",
#     "sort": "top sort key"
#     "global": "global alert message"
# }
# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'begin': {
        'description': 'Begin timestamp of the event',
        'unit': 'timestamp',
    },
    'end': {
        'description': 'End timestamp of the event (or -1 if ongoing)',
        'unit': 'timestamp',
    },
    'state': {
        'description': 'State of the event (WARNING|CRITICAL)',
        'unit': 'string',
    },
    'type': {
        'description': 'Type of the event (CPU|LOAD|MEM)',
        'unit': 'string',
    },
    'max': {
        'description': 'Maximum value during the event period',
        'unit': 'float',
    },
    'avg': {
        'description': 'Average value during the event period',
        'unit': 'float',
    },
    'min': {
        'description': 'Minimum value during the event period',
        'unit': 'float',
    },
    'sum': {
        'description': 'Sum of the values during the event period',
        'unit': 'float',
    },
    'count': {
        'description': 'Number of values during the event period',
        'unit': 'int',
    },
    'top': {
        'description': 'Top 3 processes name during the event period',
        'unit': 'list',
    },
    'desc': {
        'description': 'Description of the event',
        'unit': 'string',
    },
    'sort': {
        'description': 'Sort key of the top processes',
        'unit': 'string',
    },
    'global_msg': {
        'description': 'Global alert message',
        'unit': 'string',
    },
}


class PluginModel(GlancesPluginModel):
    """Glances alert plugin.

    Only for display.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[], fields_description=fields_description)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'bottom'

        # Set the maximum number of events to display
        if config is not None and (config.has_section('alert') or config.has_section('alerts')):
            glances_events.set_max_events(config.get_int_value('alert', 'max_events', default=10))
            glances_events.set_min_duration(config.get_int_value('alert', 'min_duration', default=6))
            glances_events.set_min_interval(config.get_int_value('alert', 'min_interval', default=6))
        else:
            glances_events.set_max_events(10)
            glances_events.set_min_duration(6)
            glances_events.set_min_interval(6)

    def update(self):
        """Nothing to do here. Just return the global glances_log."""
        # Set the stats to the glances_events
        self.stats = glances_events.get()

    def build_hdr_msg(self, ret):
        def cond(elem):
            return elem['end'] == -1 and 'global_msg' in elem

        global_message = [elem['global_msg'] for elem in self.stats if cond(elem)]
        title = global_message[0] if global_message else "EVENTS history"

        ret.append(self.curse_add_line(title, "TITLE"))

        return ret

    def add_new_line(self, ret, alert):
        ret.append(self.curse_new_line())

        return ret

    def add_start_time(self, ret, alert):
        timezone = datetime.now().astimezone().tzinfo
        alert_dt = datetime.fromtimestamp(alert['begin'], tz=timezone)
        ret.append(self.curse_add_line(alert_dt.strftime("%Y-%m-%d %H:%M:%S(%z)")))

        return ret

    def add_duration(self, ret, alert):
        if alert['end'] > 0:
            # If finished display duration
            end = datetime.fromtimestamp(alert['end'])
            begin = datetime.fromtimestamp(alert['begin'])
            msg = f' ({end - begin})'
        else:
            msg = ' (ongoing)'
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_add_line(" - "))

        return ret

    def add_infos(self, ret, alert):
        if alert['end'] > 0:
            # If finished do not display status
            msg = '{} on {}'.format(alert['state'], alert['type'])
            ret.append(self.curse_add_line(msg))
        else:
            msg = str(alert['type'])
            ret.append(self.curse_add_line(msg, decoration=alert['state']))

        return ret

    def add_min_mean_max(self, ret, alert):
        if self.approx_equal(alert['min'], alert['max'], tolerance=0.1):
            msg = ' ({:.1f})'.format(alert['avg'])
        else:
            msg = ' (Min:{:.1f} Mean:{:.1f} Max:{:.1f})'.format(alert['min'], alert['avg'], alert['max'])
        ret.append(self.curse_add_line(msg))

        return ret

    def add_top_proc(self, ret, alert):
        top_process = ', '.join(alert['top'])
        if top_process != '':
            msg = f': {top_process}'
            ret.append(self.curse_add_line(msg))

        return ret

    def loop_over_alert(self, init, alert):
        steps = [
            self.add_new_line,
            self.add_start_time,
            self.add_duration,
            self.add_infos,
            self.add_min_mean_max,
            self.add_top_proc,
        ]

        return reduce(lambda ret, step: step(ret, alert), steps, init)

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        init = []

        # Only process if display plugin enable...
        if not self.stats or self.is_disabled():
            return init

        return reduce(self.loop_over_alert, self.stats, self.build_hdr_msg(init))

    def approx_equal(self, a, b, tolerance=0.0):
        """Compare a with b using the tolerance (if numerical)."""
        if str(int(a)).isdigit() and str(int(b)).isdigit():
            return abs(a - b) <= max(abs(a), abs(b)) * tolerance
        return a == b
