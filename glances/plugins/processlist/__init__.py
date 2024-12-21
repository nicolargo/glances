#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Process list plugin."""

import copy
import functools
import os

from glances.globals import WINDOWS, key_exist_value_not_none_not_v, replace_special_chars
from glances.logger import logger
from glances.outputs.glances_unicode import unicode_message
from glances.plugins.core import PluginModel as CorePluginModel
from glances.plugins.plugin.model import GlancesPluginModel
from glances.processes import glances_processes, sort_stats

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: if True then compute and add *_gauge and *_rate_per_is fields
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'pid': {
        'description': 'Process identifier (ID)',
        'unit': 'number',
    },
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


def seconds_to_hms(input_seconds):
    """Convert seconds to human-readable time."""
    minutes, seconds = divmod(input_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    hours = int(hours)
    minutes = int(minutes)
    seconds = str(int(seconds)).zfill(2)

    return hours, minutes, seconds


def split_cmdline(bare_process_name, cmdline):
    """Return path, cmd and arguments for a process cmdline based on bare_process_name.

    If first argument of cmdline starts with the bare_process_name then
    cmdline will just be considered cmd and path will be empty (see https://github.com/nicolargo/glances/issues/1795)

    :param bare_process_name: Name of the process from psutil
    :param cmdline: cmdline from psutil
    :return: Tuple with three strings, which are path, cmd and arguments of the process
    """
    if cmdline[0].startswith(bare_process_name):
        path, cmd = "", cmdline[0]
    else:
        path, cmd = os.path.split(cmdline[0])
    arguments = ' '.join(cmdline[1:])
    return path, cmd, arguments


class PluginModel(GlancesPluginModel):
    """Glances' processes plugin.

    stats is a list
    """

    # Default list of processes stats to be grabbed / displayed
    # Can be altered by glances_processes.disable_stats
    enable_stats = [
        'cpu_percent',
        'memory_percent',
        'memory_info',  # vms and rss
        'pid',
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
        'pid': '{:>{width}} ',
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
        'pid': '{:>{width}} ',
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
        super().__init__(args=args, config=config, fields_description=fields_description, stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Trying to display proc time
        self.tag_proc_time = True

        # Call CorePluginModel to get the core number (needed when not in IRIX mode / Solaris mode)
        try:
            self.nb_log_core = CorePluginModel(args=self.args).update()["log"]
        except Exception:
            self.nb_log_core = 0

        # Get the max values (dict)
        self.max_values = copy.deepcopy(glances_processes.max_values())

        # Get the maximum PID number
        # Use to optimize space (see https://github.com/nicolargo/glances/issues/959)
        self.pid_max = glances_processes.pid_max

        # Load the config file
        self.load(args, config)

        # The default sort key could also be overwrite by command line (see #1903)
        if args and args.sort_processes_key is not None:
            glances_processes.set_sort_key(args.sort_processes_key, False)

        # Note: 'glances_processes' is already init in the processes.py script

    def load(self, args, config):
        # Set the default sort key if it is defined in the configuration file
        if config is None or 'processlist' not in config.as_dict():
            return
        if 'sort_key' in config.as_dict()['processlist']:
            logger.debug(
                'Configuration overwrites processes sort key by {}'.format(config.as_dict()['processlist']['sort_key'])
            )
            glances_processes.set_sort_key(config.as_dict()['processlist']['sort_key'], False)
        if 'export' in config.as_dict()['processlist']:
            glances_processes.export_process_filter = config.as_dict()['processlist']['export']
            if args.export:
                logger.info("Export process filter is set to: {}".format(config.as_dict()['processlist']['export']))
        if 'disable_stats' in config.as_dict()['processlist']:
            logger.info(
                'Followings processes stats wil not be displayed: {}'.format(
                    config.as_dict()['processlist']['disable_stats']
                )
            )
            glances_processes.disable_stats = config.as_dict()['processlist']['disable_stats'].split(',')

    def get_key(self):
        """Return the key of the list."""
        return 'pid'

    def update(self):
        """Update processes stats using the input method."""
        # Update the stats
        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Note: Update is done in the processcount plugin
            # Just return the result
            stats = glances_processes.get_list()
        else:
            stats = self.get_init_value()

        # Get the max values (dict)
        # Use Deep copy to avoid change between update and display
        self.max_values = copy.deepcopy(glances_processes.max_values())

        # Update the stats
        self.stats = stats

        return self.stats

    def get_export(self):
        """Return the processes list to export.
        Not all the processeses are exported.
        Only the one defined in the Glances configuration file (see #794 for details).
        """
        return glances_processes.get_export()

    def get_nice_alert(self, value):
        """Return the alert relative to the Nice configuration list"""
        value = str(value)
        if self.get_limit('nice_critical') and value in self.get_limit('nice_critical'):
            return 'CRITICAL'
        if self.get_limit('nice_warning') and value in self.get_limit('nice_warning'):
            return 'WARNING'
        if self.get_limit('nice_careful') and value in self.get_limit('nice_careful'):
            return 'CAREFUL'

        return 'DEFAULT'

    def _get_process_curses_cpu_percent(self, p, selected, args):
        """Return process CPU curses"""
        if key_exist_value_not_none_not_v('cpu_percent', p, ''):
            cpu_layout = self.layout_stat['cpu'] if p['cpu_percent'] < 100 else self.layout_stat['cpu_no_digit']
            if args.disable_irix and self.nb_log_core != 0:
                msg = cpu_layout.format(p['cpu_percent'] / float(self.nb_log_core))
            else:
                msg = cpu_layout.format(p['cpu_percent'])
            alert = self.get_alert(
                p['cpu_percent'],
                highlight_zero=False,
                is_max=(p['cpu_percent'] == self.max_values['cpu_percent']),
                header="cpu",
            )
            ret = self.curse_add_line(msg, alert)
        else:
            msg = self.layout_header['cpu'].format('?')
            ret = self.curse_add_line(msg)
        return ret

    def _get_process_curses_memory_percent(self, p, selected, args):
        """Return process MEM curses"""
        if key_exist_value_not_none_not_v('memory_percent', p, ''):
            msg = self.layout_stat['mem'].format(p['memory_percent'])
            alert = self.get_alert(
                p['memory_percent'],
                highlight_zero=False,
                is_max=(p['memory_percent'] == self.max_values['memory_percent']),
                header="mem",
            )
            ret = self.curse_add_line(msg, alert)
        else:
            msg = self.layout_header['mem'].format('?')
            ret = self.curse_add_line(msg)
        return ret

    def _get_process_curses_vms(self, p, selected, args):
        """Return process VMS curses"""
        if key_exist_value_not_none_not_v('memory_info', p, '', 1) and 'vms' in p['memory_info']:
            msg = self.layout_stat['virt'].format(self.auto_unit(p['memory_info']['vms'], low_precision=False))
            ret = self.curse_add_line(msg, optional=True)
        else:
            msg = self.layout_header['virt'].format('?')
            ret = self.curse_add_line(msg)
        return ret

    def _get_process_curses_rss(self, p, selected, args):
        """Return process RSS curses"""
        if key_exist_value_not_none_not_v('memory_info', p, '', 0) and 'rss' in p['memory_info']:
            msg = self.layout_stat['res'].format(self.auto_unit(p['memory_info']['rss'], low_precision=False))
            ret = self.curse_add_line(msg, optional=True)
        else:
            msg = self.layout_header['res'].format('?')
            ret = self.curse_add_line(msg)
        return ret

    def _get_process_curses_memory_info(self, p, selected, args):
        return [
            self._get_process_curses_vms(p, selected, args),
            self._get_process_curses_rss(p, selected, args),
        ]

    def _get_process_curses_pid(self, p, selected, args):
        """Return process PID curses"""
        # Display processes, so the PID should be displayed
        msg = self.layout_stat['pid'].format(p['pid'], width=self._max_pid_size())
        return self.curse_add_line(msg)

    def _get_process_curses_username(self, p, selected, args):
        """Return process username curses"""
        if 'username' in p:
            # docker internal users are displayed as ints only, therefore str()
            # Correct issue #886 on Windows OS
            msg = self.layout_stat['user'].format(str(p['username'])[:9])
        else:
            msg = self.layout_header['user'].format('?')
        return self.curse_add_line(msg)

    def _get_process_curses_cpu_times(self, p, selected, args):
        """Return process time curses"""
        cpu_times = p['cpu_times']
        try:
            # Sum user and system time
            user_system_time = cpu_times['user'] + cpu_times['system']
        except (OverflowError, TypeError, KeyError):
            # Catch OverflowError on some Amazon EC2 server
            # See https://github.com/nicolargo/glances/issues/87
            # Also catch TypeError on macOS
            # See: https://github.com/nicolargo/glances/issues/622
            # Also catch KeyError (as no stats be present for processes of other users)
            # See: https://github.com/nicolargo/glances/issues/2831
            # logger.debug("Cannot get TIME+ ({})".format(e))
            msg = self.layout_header['time'].format('?')
            return self.curse_add_line(msg, optional=True)

        hours, minutes, seconds = seconds_to_hms(user_system_time)
        if hours > 99:
            msg = f'{hours:<7}h'
        elif 0 < hours < 100:
            msg = f'{hours}h{minutes}:{seconds}'
        else:
            msg = f'{minutes}:{seconds}'

        msg = self.layout_stat['time'].format(msg)
        if hours > 0:
            return self.curse_add_line(msg, decoration='CPU_TIME', optional=True)

        return self.curse_add_line(msg, optional=True)

    def _get_process_curses_num_threads(self, p, selected, args):
        """Return process thread curses"""
        if 'num_threads' in p:
            num_threads = p['num_threads']
            if num_threads is None:
                num_threads = '?'
            msg = self.layout_stat['thread'].format(num_threads)
        else:
            msg = self.layout_header['thread'].format('?')
        return self.curse_add_line(msg)

    def _get_process_curses_nice(self, p, selected, args):
        """Return process nice curses"""
        if 'nice' in p:
            nice = p['nice']
            if nice is None:
                nice = '?'
            msg = self.layout_stat['nice'].format(nice)
            ret = self.curse_add_line(msg, decoration=self.get_nice_alert(nice))
        else:
            msg = self.layout_header['nice'].format('?')
            ret = self.curse_add_line(msg)
        return ret

    def _get_process_curses_status(self, p, selected, args):
        """Return process status curses"""
        if 'status' in p:
            status = p['status']
            msg = self.layout_stat['status'].format(status)
            if status == 'R':
                ret = self.curse_add_line(msg, decoration='STATUS')
            else:
                ret = self.curse_add_line(msg)
        else:
            msg = self.layout_header['status'].format('?')
            ret = self.curse_add_line(msg)
        return ret

    def _get_process_curses_io_read_write(self, p, selected, args, rorw='ior'):
        """Return process IO Read or Write curses"""
        if 'io_counters' in p and p['io_counters'][4] == 1 and p['time_since_update'] != 0:
            # Display rate if stats is available and io_tag ([4]) == 1
            # IO
            io = int(
                (p['io_counters'][0 if rorw == 'ior' else 1] - p['io_counters'][2 if rorw == 'ior' else 3])
                / p['time_since_update']
            )
            if io == 0:
                msg = self.layout_stat[rorw].format("0")
            else:
                msg = self.layout_stat[rorw].format(self.auto_unit(io, low_precision=True))
            ret = self.curse_add_line(msg, optional=True, additional=True)
        else:
            msg = self.layout_header[rorw].format("?")
            ret = self.curse_add_line(msg, optional=True, additional=True)
        return ret

    def _get_process_curses_io_counters(self, p, selected, args):
        return [
            self._get_process_curses_io_read_write(p, selected, args, rorw='ior'),
            self._get_process_curses_io_read_write(p, selected, args, rorw='iow'),
        ]

    def _get_process_curses_cmdline(self, p, selected, args):
        """Return process cmdline curses"""
        ret = []
        # If no command line for the process is available, fallback to the bare process name instead
        bare_process_name = p['name']
        cmdline = p.get('cmdline', '?')
        try:
            process_decoration = 'PROCESS_SELECTED' if (selected and not args.disable_cursor) else 'PROCESS'
            if cmdline:
                path, cmd, arguments = split_cmdline(bare_process_name, cmdline)
                # Manage end of line in arguments (see #1692)
                arguments = replace_special_chars(arguments)
                if os.path.isdir(path) and not args.process_short_name:
                    msg = self.layout_stat['command'].format(path) + os.sep
                    ret.append(self.curse_add_line(msg, splittable=True))
                    ret.append(self.curse_add_line(cmd, decoration=process_decoration, splittable=True))
                else:
                    msg = self.layout_stat['command'].format(cmd)
                    ret.append(self.curse_add_line(msg, decoration=process_decoration, splittable=True))
                if arguments:
                    msg = ' ' + self.layout_stat['command'].format(arguments)
                    ret.append(self.curse_add_line(msg, splittable=True))
            else:
                msg = self.layout_stat['name'].format(bare_process_name)
                ret.append(self.curse_add_line(msg, decoration=process_decoration, splittable=True))
        except (TypeError, UnicodeEncodeError) as e:
            # Avoid crash after running fine for several hours #1335
            logger.debug(f"Can not decode command line '{cmdline}' ({e})")
            ret.append(self.curse_add_line('', splittable=True))
        return ret

    def get_process_curses_data(self, p, selected, args):
        """Get curses data to display for a process.

        - p is the process to display
        - selected is a tag=True if p is the selected process
        """
        ret = [self.curse_new_line()]

        # When a process is selected:
        # * display a special character at the beginning of the line
        # * underline the command name
        ret.append(
            self.curse_add_line(
                unicode_message('PROCESS_SELECTOR') if (selected and not args.disable_cursor) else ' ', 'SELECTED'
            )
        )

        for stat in [i for i in self.enable_stats if i not in glances_processes.disable_stats]:
            msg = getattr(self, f'_get_process_curses_{stat}')(p, selected, args)
            if isinstance(msg, list):
                # ex: _get_process_curses_command return a list, so extend
                ret.extend(msg)
            else:
                # ex: _get_process_curses_cpu return a dict, so append
                ret.append(msg)

        return ret

    def is_selected_process(self, args):
        return (
            args.is_standalone
            and self.args.enable_process_extended
            and args.cursor_position is not None
            and glances_processes.extended_process is not None
        )

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_process:
            return ret

        # Compute the sort key
        process_sort_key = glances_processes.sort_key
        processes_list_sorted = self._sort_stats(process_sort_key)

        # Display extended stats for selected process
        #############################################

        if self.is_selected_process(args):
            self._msg_curse_extended_process(ret, glances_processes.extended_process)

        # Display others processes list
        ###############################

        # Header
        self._msg_curse_header(ret, process_sort_key, args)

        # Process list
        # Loop over processes (sorted by the sort key previously compute)
        # This is a Glances bottleneck (see flame graph),
        # TODO: get_process_curses_data should be optimized
        for position, process in enumerate(processes_list_sorted):
            ret.extend(self.get_process_curses_data(process, position == args.cursor_position, args))

        # A filter is set Display the stats summaries
        if glances_processes.process_filter is not None:
            if args.reset_minmax_tag:
                args.reset_minmax_tag = not args.reset_minmax_tag
                self._mmm_reset()
            self._msg_curse_sum(ret, args=args)
            self._msg_curse_sum(ret, mmm='min', args=args)
            self._msg_curse_sum(ret, mmm='max', args=args)

        # Return the message with decoration
        return ret

    def _msg_curse_extended_process(self, ret, p):
        """Get extended curses data for the selected process (see issue #2225)

        The result depends of the process type (process or thread).

        Input p is a dict with the following keys:
        {'status': 'S',
         'memory_info': {'rss': 466890752, 'vms': 3365347328, 'shared': 68153344,
                         'text': 659456, 'lib': 0, 'data': 774647808, 'dirty': 0],
         'pid': 4980,
         'io_counters': [165385216, 0, 165385216, 0, 1],
         'num_threads': 20,
         'nice': 0,
         'memory_percent': 5.958135664449709,
         'cpu_percent': 0.0,
         'gids': {'real': 1000, 'effective': 1000, 'saved': 1000},
         'cpu_times': {'user': 696.38, 'system': 119.98, 'children_user': 0.0,
                       'children_system': 0.0, 'iowait': 0.0),
         'name': 'WebExtensions',
         'key': 'pid',
         'time_since_update': 2.1997854709625244,
         'cmdline': ['/snap/firefox/2154/usr/lib/firefox/firefox', '-contentproc', '-childID', '...'],
         'username': 'nicolargo',
         'cpu_min': 0.0,
         'cpu_max': 7.0,
         'cpu_mean': 3.2}
        """
        self._msg_curse_extended_process_thread(ret, p)

    def add_title_line(self, ret, prog):
        ret.append(self.curse_add_line("Pinned thread ", "TITLE"))
        ret.append(self.curse_add_line(prog['name'], "UNDERLINE"))
        ret.append(self.curse_add_line(" ('e' to unpin)"))

        return ret

    def add_cpu_line(self, ret, prog):
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(' CPU Min/Max/Mean: '))
        msg = '{: >7.1f}{: >7.1f}{: >7.1f}%'.format(prog['cpu_min'], prog['cpu_max'], prog['cpu_mean'])
        ret.append(self.curse_add_line(msg, decoration='INFO'))

        return ret

    def maybe_add_cpu_affinity_line(self, ret, prog):
        if 'cpu_affinity' in prog and prog['cpu_affinity'] is not None:
            ret.append(self.curse_add_line(' Affinity: '))
            ret.append(self.curse_add_line(str(len(prog['cpu_affinity'])), decoration='INFO'))
            ret.append(self.curse_add_line(' cores', decoration='INFO'))

        return ret

    def add_ionice_line(self, headers, default):
        def add_ionice_using_matches(msg, v):
            return msg + headers.get(v, default(v))

        return add_ionice_using_matches

    def get_headers(self, k):
        # Linux: The scheduling class. 0 for none, 1 for real time, 2 for best-effort, 3 for idle.
        default = {0: 'No specific I/O priority', 1: k + 'Real Time', 2: k + 'Best Effort', 3: k + 'IDLE'}

        # Windows: On Windows only ioclass is used and it can be set to 2 (normal), 1 (low) or 0 (very low).
        windows = {0: k + 'Very Low', 1: k + 'Low', 2: 'No specific I/O priority'}

        return windows if WINDOWS else default

    def maybe_add_ionice_line(self, ret, prog):
        if 'ionice' in prog and prog['ionice'] is not None and hasattr(prog['ionice'], 'ioclass'):
            msg = ' IO nice: '
            k = 'Class is '
            v = prog['ionice'].ioclass

            def default(v):
                return k + str(v)

            headers = self.get_headers(k)
            msg = self.add_ionice_line(headers, default)(msg, v)
            #  value is a number which goes from 0 to 7.
            # The higher the value, the lower the I/O priority of the process.
            if hasattr(prog['ionice'], 'value') and prog['ionice'].value != 0:
                msg += ' (value {}/7)'.format(str(prog['ionice'].value))
            ret.append(self.curse_add_line(msg, splittable=True))

        return ret

    def maybe_add_memory_swap_line(self, ret, prog):
        if 'memory_swap' in prog and prog['memory_swap'] is not None:
            ret.append(
                self.curse_add_line(
                    self.auto_unit(prog['memory_swap'], low_precision=False), decoration='INFO', splittable=True
                )
            )
            ret.append(self.curse_add_line(' swap ', splittable=True))

        return ret

    def add_memory_info_lines(self, ret, prog):
        for key, val in prog['memory_info'].items():
            ret.append(
                self.curse_add_line(
                    self.auto_unit(val, low_precision=False),
                    decoration='INFO',
                    splittable=True,
                )
            )
            ret.append(self.curse_add_line(' ' + key + ' ', splittable=True))

        return ret

    def add_memory_line(self, ret, prog):
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(' MEM Min/Max/Mean: '))
        msg = '{: >7.1f}{: >7.1f}{: >7.1f}%'.format(prog['memory_min'], prog['memory_max'], prog['memory_mean'])
        ret.append(self.curse_add_line(msg, decoration='INFO'))
        if 'memory_info' in prog and prog['memory_info'] is not None:
            ret.append(self.curse_add_line(' Memory info: '))
            steps = [self.add_memory_info_lines, self.maybe_add_memory_swap_line]
            ret = functools.reduce(lambda ret, step: step(ret, prog), steps, ret)

        return ret

    def add_io_and_network_lines(self, ret, prog):
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(' Open: '))
        for stat_prefix in ['num_threads', 'num_fds', 'num_handles', 'tcp', 'udp']:
            if stat_prefix in prog and prog[stat_prefix] is not None:
                ret.append(self.curse_add_line(str(prog[stat_prefix]), decoration='INFO'))
                ret.append(self.curse_add_line(' {} '.format(stat_prefix.replace('num_', ''))))
        return ret

    def _msg_curse_extended_process_thread(self, ret, prog):
        # `append_newlines` has dummy arguments for piping thru `functools.reduce`
        def append_newlines(ret, prog):
            (ret.append(self.curse_new_line()),)
            ret.append(self.curse_new_line())

            return ret

        steps = [
            self.add_title_line,
            self.add_cpu_line,
            self.maybe_add_cpu_affinity_line,
            self.maybe_add_ionice_line,
            self.add_memory_line,
            self.add_io_and_network_lines,
            append_newlines,
        ]

        functools.reduce(lambda ret, step: step(ret, prog), steps, ret)

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
        if 'pid' in display_stats:
            msg = self.layout_header['pid'].format('PID', width=self._max_pid_size())
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
            shortkey = "('e' to pin | 'k' to kill)"
        else:
            shortkey = ""
        if 'cmdline' in display_stats:
            msg = self.layout_header['command'].format("Command", shortkey)
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
        msg = self.layout_header['pid'].format('', width=self._max_pid_size())
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

    def _mmm_deco(self, mmm):
        """Return the decoration string for the current mmm status."""
        if mmm is not None:
            return 'DEFAULT'
        return 'FILTER'

    def _mmm_reset(self):
        """Reset the MMM stats."""
        self.mmm_min = {}
        self.mmm_max = {}

    def _sum_stats(self, key, sub_key=None, mmm=None):
        """Return the sum of the stats value for the given key.

        :param sub_key: If sub_key is set, get the p[key][sub_key]
        :param mmm: display min, max, mean or current (if mmm=None)
        """
        # Compute stats summary
        ret = 0
        for p in self.stats:
            if key not in p:
                # Correct issue #1188
                continue
            if p[key] is None:
                # Correct https://github.com/nicolargo/glances/issues/1105#issuecomment-363553788
                continue
            if sub_key is None:
                ret += p[key]
            else:
                ret += p[key][sub_key]

        # Manage Min/Max/Mean
        mmm_key = self._mmm_key(key, sub_key)
        if mmm == 'min':
            try:
                if self.mmm_min[mmm_key] > ret:
                    self.mmm_min[mmm_key] = ret
            except AttributeError:
                self.mmm_min = {}
                return 0
            except KeyError:
                self.mmm_min[mmm_key] = ret
            ret = self.mmm_min[mmm_key]
        elif mmm == 'max':
            try:
                if self.mmm_max[mmm_key] < ret:
                    self.mmm_max[mmm_key] = ret
            except AttributeError:
                self.mmm_max = {}
                return 0
            except KeyError:
                self.mmm_max[mmm_key] = ret
            ret = self.mmm_max[mmm_key]

        return ret

    def _mmm_key(self, key, sub_key):
        ret = key
        if sub_key is not None:
            ret += str(sub_key)
        return ret

    def _sort_stats(self, sorted_by=None):
        """Return the stats (dict) sorted by (sorted_by)."""
        return sort_stats(self.stats, sorted_by, reverse=glances_processes.sort_reverse)

    def _max_pid_size(self):
        """Return the maximum PID size in number of char."""
        if self.pid_max is not None:
            return len(str(self.pid_max))

        # By default return 5 (corresponding to 99999 PID number)
        return 5
