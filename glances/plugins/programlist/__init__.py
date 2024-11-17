#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Program list plugin."""

import copy

from glances.plugins.processlist import PluginModel as GlancesProcessListPluginModel
from glances.processes import glances_processes

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: if True then compute and add *_gauge and *_rate_per_is fields
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'name': {
        'description': 'Process name',
        'unit': 'string',
    },
    'cmdline': {
        'description': 'Command line with arguments',
        'unit': 'list',
    },
    'username': {
        'description': 'Process owner',
        'unit': 'string',
    },
    'nprocs': {
        'description': 'Number of children processes',
        'unit': 'number',
    },
    'num_threads': {
        'description': 'Number of threads',
        'unit': 'number',
    },
    'cpu_percent': {
        'description': 'Process CPU consumption',
        'unit': 'percent',
    },
    'memory_percent': {
        'description': 'Process memory consumption',
        'unit': 'percent',
    },
    'memory_info': {
        'description': 'Process memory information (dict with rss, vms, shared, text, lib, data, dirty keys)',
        'unit': 'byte',
    },
    'status': {
        'description': 'Process status',
        'unit': 'string',
    },
    'nice': {
        'description': 'Process nice value',
        'unit': 'number',
    },
    'cpu_times': {
        'description': 'Process CPU times (dict with user, system, iowait keys)',
        'unit': 'second',
    },
    'gids': {
        'description': 'Process group IDs (dict with real, effective, saved keys)',
        'unit': 'number',
    },
    'io_counters': {
        'description': 'Process IO counters (list with read_count, write_count, read_bytes, write_bytes, io_tag keys)',
        'unit': 'byte',
    },
}


class PluginModel(GlancesProcessListPluginModel):
    """Glances' processes plugin.

    stats is a list
    """

    # Default list of processes stats to be grabbed / displayed
    # Can be altered by glances_processes.disable_stats
    enable_stats = [
        'cpu_percent',
        'memory_percent',
        'memory_info',  # vms and rss
        'nprocs',
        'username',
        'cpu_times',
        'num_threads',
        'nice',
        'status',
        'io_counters',  # ior and iow
        'cmdline',
    ]

    # Define the header layout of the processes list columns
    layout_header = {
        'cpu': '{:<6} ',
        'mem': '{:<5} ',
        'virt': '{:<5} ',
        'res': '{:<5} ',
        'nprocs': '{:>7} ',
        'user': '{:<10} ',
        'time': '{:>8} ',
        'thread': '{:<3} ',
        'nice': '{:>3} ',
        'status': '{:>1} ',
        'ior': '{:>4} ',
        'iow': '{:<4} ',
        'command': '{} {}',
    }

    # Define the stat layout of the processes list columns
    layout_stat = {
        'cpu': '{:<6.1f}',
        'cpu_no_digit': '{:<6.0f}',
        'mem': '{:<5.1f} ',
        'virt': '{:<5} ',
        'res': '{:<5} ',
        'nprocs': '{:>7} ',
        'user': '{:<10} ',
        'time': '{:>8} ',
        'thread': '{:<3} ',
        'nice': '{:>3} ',
        'status': '{:>1} ',
        'ior': '{:>4} ',
        'iow': '{:<4} ',
        'command': '{}',
        'name': '[{}]',
    }

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config)

    def get_key(self):
        """Return the key of the list."""
        return 'name'

    def update(self):
        """Update processes stats using the input method."""
        # Update the stats
        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Note: Update is done in the processcount plugin
            # Just return the result
            stats = glances_processes.get_list(as_programs=True)
        else:
            stats = self.get_init_value()

        # Get the max values (dict)
        # Use Deep copy to avoid change between update and display
        self.max_values = copy.deepcopy(glances_processes.max_values())

        # Update the stats
        self.stats = stats

        return self.stats

    def _get_process_curses_nprocs(self, p, selected, args):
        """Return process NPROCS curses"""
        # Display the number of children processes
        msg = self.layout_stat['nprocs'].format(p['nprocs'])
        return self.curse_add_line(msg)

    def _msg_curse_header(self, ret, process_sort_key, args=None):
        """Build the header and add it to the ret dict."""
        sort_style = 'SORT'

        display_stats = [i for i in self.enable_stats if i not in glances_processes.disable_stats]

        if 'cpu_percent' in display_stats:
            if args.disable_irix and 0 < self.nb_log_core < 10:
                msg = self.layout_header['cpu'].format('CPU%/' + str(self.nb_log_core))
            elif args.disable_irix and self.nb_log_core != 0:
                msg = self.layout_header['cpu'].format('CPU%/C')
            else:
                msg = self.layout_header['cpu'].format('CPU%')
            ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'cpu_percent' else 'DEFAULT'))

        if 'memory_percent' in display_stats:
            msg = self.layout_header['mem'].format('MEM%')
            ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'memory_percent' else 'DEFAULT'))
        if 'memory_info' in display_stats:
            msg = self.layout_header['virt'].format('VIRT')
            ret.append(self.curse_add_line(msg, optional=True))
            msg = self.layout_header['res'].format('RES')
            ret.append(self.curse_add_line(msg, optional=True))
        if 'nprocs' in display_stats:
            msg = self.layout_header['nprocs'].format('NPROCS')
            ret.append(self.curse_add_line(msg))
        if 'username' in display_stats:
            msg = self.layout_header['user'].format('USER')
            ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'username' else 'DEFAULT'))
        if 'cpu_times' in display_stats:
            msg = self.layout_header['time'].format('TIME+')
            ret.append(
                self.curse_add_line(msg, sort_style if process_sort_key == 'cpu_times' else 'DEFAULT', optional=True)
            )
        if 'num_threads' in display_stats:
            msg = self.layout_header['thread'].format('THR')
            ret.append(self.curse_add_line(msg))
        if 'nice' in display_stats:
            msg = self.layout_header['nice'].format('NI')
            ret.append(self.curse_add_line(msg))
        if 'status' in display_stats:
            msg = self.layout_header['status'].format('S')
            ret.append(self.curse_add_line(msg))
        if 'io_counters' in display_stats:
            msg = self.layout_header['ior'].format('R/s')
            ret.append(
                self.curse_add_line(
                    msg, sort_style if process_sort_key == 'io_counters' else 'DEFAULT', optional=True, additional=True
                )
            )
            msg = self.layout_header['iow'].format('W/s')
            ret.append(
                self.curse_add_line(
                    msg, sort_style if process_sort_key == 'io_counters' else 'DEFAULT', optional=True, additional=True
                )
            )
        if args.is_standalone and not args.disable_cursor:
            shortkey = "('k' to kill)"
        else:
            shortkey = ""
        if 'cmdline' in display_stats:
            msg = self.layout_header['command'].format("Programs", shortkey)
            ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'name' else 'DEFAULT'))

    def _msg_curse_sum(self, ret, sep_char='_', mmm=None, args=None):
        """
        Build the sum message (only when filter is on) and add it to the ret dict.

        :param ret: list of string where the message is added
        :param sep_char: define the line separation char
        :param mmm: display min, max, mean or current (if mmm=None)
        :param args: Glances args
        """
        ret.append(self.curse_new_line())
        if mmm is None:
            ret.append(self.curse_add_line(sep_char * 69))
            ret.append(self.curse_new_line())
        # CPU percent sum
        msg = ' '
        msg += self.layout_stat['cpu'].format(self._sum_stats('cpu_percent', mmm=mmm))
        ret.append(self.curse_add_line(msg, decoration=self._mmm_deco(mmm)))
        # MEM percent sum
        msg = self.layout_stat['mem'].format(self._sum_stats('memory_percent', mmm=mmm))
        ret.append(self.curse_add_line(msg, decoration=self._mmm_deco(mmm)))
        # VIRT and RES memory sum
        if (
            'memory_info' in self.stats[0]
            and self.stats[0]['memory_info'] is not None
            and self.stats[0]['memory_info'] != ''
        ):
            # VMS
            msg = self.layout_stat['virt'].format(
                self.auto_unit(self._sum_stats('memory_info', sub_key='vms', mmm=mmm), low_precision=False)
            )
            ret.append(self.curse_add_line(msg, decoration=self._mmm_deco(mmm), optional=True))
            # RSS
            msg = self.layout_stat['res'].format(
                self.auto_unit(self._sum_stats('memory_info', sub_key='rss', mmm=mmm), low_precision=False)
            )
            ret.append(self.curse_add_line(msg, decoration=self._mmm_deco(mmm), optional=True))
        else:
            msg = self.layout_header['virt'].format('')
            ret.append(self.curse_add_line(msg))
            msg = self.layout_header['res'].format('')
            ret.append(self.curse_add_line(msg))
        # PID
        msg = self.layout_header['nprocs'].format('')
        ret.append(self.curse_add_line(msg))
        # USER
        msg = self.layout_header['user'].format('')
        ret.append(self.curse_add_line(msg))
        # TIME+
        msg = self.layout_header['time'].format('')
        ret.append(self.curse_add_line(msg, optional=True))
        # THREAD
        msg = self.layout_header['thread'].format('')
        ret.append(self.curse_add_line(msg))
        # NICE
        msg = self.layout_header['nice'].format('')
        ret.append(self.curse_add_line(msg))
        # STATUS
        msg = self.layout_header['status'].format('')
        ret.append(self.curse_add_line(msg))
        # IO read/write
        if 'io_counters' in self.stats[0] and mmm is None:
            # IO read
            io_rs = int(
                (self._sum_stats('io_counters', 0) - self._sum_stats('io_counters', sub_key=2, mmm=mmm))
                / self.stats[0]['time_since_update']
            )
            if io_rs == 0:
                msg = self.layout_stat['ior'].format('0')
            else:
                msg = self.layout_stat['ior'].format(self.auto_unit(io_rs, low_precision=True))
            ret.append(self.curse_add_line(msg, decoration=self._mmm_deco(mmm), optional=True, additional=True))
            # IO write
            io_ws = int(
                (self._sum_stats('io_counters', 1) - self._sum_stats('io_counters', sub_key=3, mmm=mmm))
                / self.stats[0]['time_since_update']
            )
            if io_ws == 0:
                msg = self.layout_stat['iow'].format('0')
            else:
                msg = self.layout_stat['iow'].format(self.auto_unit(io_ws, low_precision=True))
            ret.append(self.curse_add_line(msg, decoration=self._mmm_deco(mmm), optional=True, additional=True))
        else:
            msg = self.layout_header['ior'].format('')
            ret.append(self.curse_add_line(msg, optional=True, additional=True))
            msg = self.layout_header['iow'].format('')
            ret.append(self.curse_add_line(msg, optional=True, additional=True))
        if mmm is None:
            msg = '< {}'.format('current')
            ret.append(self.curse_add_line(msg, optional=True))
        else:
            msg = f'< {mmm}'
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '(\'M\' to reset)'
            ret.append(self.curse_add_line(msg, optional=True))
