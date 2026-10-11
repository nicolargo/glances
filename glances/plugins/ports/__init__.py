#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Ports scanner plugin."""

import numbers
from functools import partial, reduce

from glances.globals import bool_type
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel
from glances.plugins.ports.scanner import ThreadScanner
from glances.ports_list import GlancesPortsList
from glances.web_list import GlancesWebList

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'host': {
        'description': 'Measurement is be done on this host (or IP address)',
    },
    'port': {
        'description': 'Measurement is be done on this port (0 for ICMP)',
    },
    'url': {
        'description': 'Measurement is be done on this URL (credentials are redacted)',
    },
    'description': {
        'description': 'Human readable description for the host/port',
    },
    'refresh': {
        'description': 'Refresh time (in seconds) for this host/port',
    },
    'timeout': {
        'description': 'Timeout (in seconds) for the measurement',
    },
    'status': {
        'description': 'Measurement result (in seconds)',
        'unit': 'second',
    },
    'rtt_warning': {
        'description': 'Warning threshold (in seconds) for the measurement',
        'unit': 'second',
    },
    'indice': {
        'description': 'Unique indice for the host/port',
    },
}


class PortsPlugin(GlancesPluginModel):
    """Glances ports scanner plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[], fields_description=fields_description)
        self.args = args
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        web_list = GlancesWebList(config=config, args=args)
        self.stats = GlancesPortsList(config=config, args=args).get_ports_list() + web_list.get_web_list()

        # Scan credentials, kept out of self.stats: the statistics are served
        # unauthenticated by default (GHSA-2jqf-3j6f-683p)
        self._web_secrets = web_list.get_web_secrets()

        # Global Thread running all the scans
        self._thread = None

    def exit(self):
        """Overwrite the exit method to close threads."""
        if self._thread is not None:
            self._thread.stop()
        # Call the father class
        super().exit()

    def get_key(self):
        """Return the key of the list."""
        return 'indice'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the ports list."""
        if self.input_method == 'local':
            # Only refresh:
            # * if there is not other scanning thread
            # * every refresh seconds (define in the configuration file)
            if self._thread is None:
                thread_is_running = False
            else:
                thread_is_running = self._thread.is_alive()
            if not thread_is_running:
                # Run ports scanner
                self._thread = ThreadScanner(self.stats, self._web_secrets)
                self._thread.start()
        else:
            # Not available in SNMP mode
            self.stats = None

        return self.stats

    def get_conds_if_port(self, port):
        return {
            'CAREFUL': port['status'] is None,
            'CRITICAL': port['status'] == 0,
            'WARNING': isinstance(port['status'], (float, int))
            and port['rtt_warning'] is not None
            and port['status'] > port['rtt_warning'],
        }

    def get_ports_alert(self, port, header="", log=False):
        """Return the alert status relative to the port scan return value."""

        return self.get_p_alert(self.get_conds_if_port(port), port, header, log)

    def get_conds_if_url(self, web):
        return {
            'CAREFUL': web['status'] is None,
            'CRITICAL': web['status'] is not None and web['status'] not in [200, 301, 302],
            'WARNING': web['rtt_warning'] is not None and web['elapsed'] > web['rtt_warning'],
        }

    def get_web_alert(self, web, header="", log=False):
        """Return the alert status relative to the web/url scan return value."""

        return self.get_p_alert(self.get_conds_if_url(web), web, header, log)

    def get_p_alert(self, conds, p, header="", log=False):
        ret = self.get_default_ret_value(conds)

        # Get stat name
        stat_name = self.get_stat_name(header=header)

        # Manage threshold
        self.manage_threshold(stat_name, ret)

        # Manage action
        self.manage_action(stat_name, ret.lower(), header, p[self.get_key()])

        return ret

    def get_default_ret_value(self, conds):
        # Resolve by severity, not by dict insertion order: several conditions
        # can match at once and the most severe one has to win.
        for level in ('CRITICAL', 'WARNING', 'CAREFUL'):
            if conds.get(level):
                return level

        return 'OK'

    def set_status_if_host(self, p):
        if p['host'] is None:
            status = 'None'
        elif p['status'] is None:
            status = 'Scanning'
        elif isinstance(p['status'], bool_type) and p['status'] is True:
            status = 'Open'
        elif p['status'] == 0:
            status = 'Timeout'
        else:
            # Convert second to ms
            status = '{:.0f}ms'.format(p['status'] * 1000.0)

        return status

    def set_status_if_url(self, p):
        if isinstance(p['status'], numbers.Number):
            status = 'Code {}'.format(p['status'])
        elif p['status'] is None:
            status = 'Scanning'
        else:
            status = p['status']

        return status

    def build_str(self, name_max_width, ret, p):
        helper, status = self.get_status_and_helper(p).get(True)
        msg = '{:{width}}'.format(p['description'][0:name_max_width], width=name_max_width)
        ret.append(self.curse_add_line(msg))
        msg = f'{status:>9}'
        ret.append(self.curse_add_line(msg, helper(p, header=p['indice'] + '_rtt')))
        ret.append(self.curse_new_line())

        return ret

    def get_status_and_helper(self, p):
        return {
            'host' in p: (self.get_ports_alert, self.set_status_if_host(p)) if 'host' in p else None,
            'url' in p: (self.get_web_alert, self.set_status_if_url(p)) if 'url' in p else None,
        }

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        # Only process if stats exist and display plugin enable...
        init = []

        if not self.stats or args.disable_ports:
            return init

        # Max size for the interface name
        if max_width:
            name_max_width = max_width - 7
        else:
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return init

        # Build the string message
        build_str_with_this_max_width = partial(self.build_str, name_max_width)
        ret = reduce(build_str_with_this_max_width, self.stats, init)

        # Delete the last empty line
        try:
            ret.pop()
        except IndexError:
            pass

        return ret
