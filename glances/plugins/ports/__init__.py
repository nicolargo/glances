#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Ports scanner plugin."""

import numbers
import os
import socket
import subprocess
import threading
import time
from functools import partial, reduce

from glances.globals import BSD, MACOS, WINDOWS, bool_type
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel
from glances.ports_list import GlancesPortsList
from glances.timer import Counter
from glances.web_list import GlancesWebList

try:
    import requests

    requests_tag = True
except ImportError as e:
    requests_tag = False
    logger.warning(f"Missing Python Lib ({e}), Ports plugin is limited to port scanning")

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


class PluginModel(GlancesPluginModel):
    """Glances ports scanner plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[], fields_description=fields_description)
        self.args = args
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.stats = (
            GlancesPortsList(config=config, args=args).get_ports_list()
            + GlancesWebList(config=config, args=args).get_web_list()
        )

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
                self._thread = ThreadScanner(self.stats)
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
            'CRITICAL': web['status'] not in [200, 301, 302],
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
        ret_as_dict_val = {'ret': key for key, cond in conds.items() if cond}

        return ret_as_dict_val.get('ret', 'OK')

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


class ThreadScanner(threading.Thread):
    """
    Specific thread for the port/web scanner.

    stats is a list of dict
    """

    def __init__(self, stats):
        """Init the class."""
        logger.debug(f"ports plugin - Create thread for scan list {stats}")
        super().__init__()
        # Event needed to stop properly the thread
        self._stopper = threading.Event()
        # The class return the stats as a list of dict
        self._stats = stats
        # Is part of Ports plugin
        self.plugin_name = "ports"

    def get_key(self):
        """Return the key of the list."""
        return 'indice'

    def run(self):
        """Grab the stats.

        Infinite loop, should be stopped by calling the stop() method.
        """
        for p in self._stats:
            # End of the thread has been asked
            if self.stopped():
                break
            # Scan a port (ICMP or TCP)
            if 'port' in p:
                self._port_scan(p)
                # Had to wait between two scans
                # If not, result are not ok
                time.sleep(1)
            # Scan an URL
            elif 'url' in p and requests_tag:
                self._web_scan(p)
            # Add the key for every element
            p['key'] = self.get_key()

    @property
    def stats(self):
        """Stats getter."""
        return self._stats

    @stats.setter
    def stats(self, value):
        """Stats setter."""
        self._stats = value

    def stop(self, timeout=None):
        """Stop the thread."""
        logger.debug(f"ports plugin - Close thread for scan list {self._stats}")
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.is_set()

    def _web_scan(self, web):
        """Scan the  Web/URL (dict) and update the status key."""
        try:
            req = requests.head(
                web['url'],
                allow_redirects=True,
                verify=web['ssl_verify'],
                proxies=web['proxies'],
                timeout=web['timeout'],
            )
        except Exception as e:
            logger.debug(e)
            web['status'] = 'Error'
            web['elapsed'] = 0
        else:
            web['status'] = req.status_code
            web['elapsed'] = req.elapsed.total_seconds()
        return web

    def _port_scan(self, port):
        """Scan the port structure (dict) and update the status key."""
        if int(port['port']) == 0:
            return self._port_scan_icmp(port)
        return self._port_scan_tcp(port)

    def _resolv_name(self, hostname):
        """Convert hostname to IP address."""
        ip = hostname
        try:
            ip = socket.gethostbyname(hostname)
        except Exception as e:
            logger.debug(f"{self.plugin_name}: Cannot convert {hostname} to IP address ({e})")
        return ip

    def _port_scan_icmp(self, port):
        """Scan the (ICMP) port structure (dict) and update the status key."""
        ret = None

        # Create the ping command
        # Use the system ping command because it already have the sticky bit set
        # Python can not create ICMP packet with non root right
        if WINDOWS:
            timeout_opt = '-w'
            count_opt = '-n'
        elif MACOS or BSD:
            timeout_opt = '-t'
            count_opt = '-c'
        else:
            # Linux and co...
            timeout_opt = '-W'
            count_opt = '-c'
        # Build the command line
        # Note: Only string are allowed
        cmd = [
            'ping',
            count_opt,
            '1',
            timeout_opt,
            str(self._resolv_name(port['timeout'])),
            self._resolv_name(port['host']),
        ]
        fnull = open(os.devnull, 'w')

        try:
            counter = Counter()
            ret = subprocess.check_call(cmd, stdout=fnull, stderr=fnull, close_fds=True)
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        except subprocess.CalledProcessError:
            # Correct issue #1084: No Offline status for timed-out ports
            port['status'] = False
        except Exception as e:
            logger.debug("{}: Error while pinging host {} ({})".format(self.plugin_name, port['host'], e))

        fnull.close()

        return ret

    def _port_scan_tcp(self, port):
        """Scan the (TCP) port structure (dict) and update the status key."""
        ret = None

        # Create and configure the scanning socket
        try:
            socket.setdefaulttimeout(port['timeout'])
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            logger.debug(f"{self.plugin_name}: Error while creating scanning socket ({e})")

        # Scan port
        ip = self._resolv_name(port['host'])
        counter = Counter()
        try:
            ret = _socket.connect_ex((ip, int(port['port'])))
        except Exception as e:
            logger.debug(f"{self.plugin_name}: Error while scanning port {port} ({e})")
        else:
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        finally:
            _socket.close()

        return ret
