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

"""Ports scanner plugin."""

import os
import subprocess
import threading
import socket
import time
import numbers

from glances.globals import WINDOWS, MACOS, BSD
from glances.ports_list import GlancesPortsList
from glances.web_list import GlancesWebList
from glances.timer import Timer, Counter
from glances.compat import bool_type
from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin

try:
    import requests
    requests_tag = True
except ImportError as e:
    requests_tag = False
    logger.warning("Missing Python Lib ({}), Ports plugin is limited to port scanning".format(e))


class Plugin(GlancesPlugin):
    """Glances ports scanner plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     stats_init_value=[])
        self.args = args
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.stats = GlancesPortsList(config=config, args=args).get_ports_list() + GlancesWebList(config=config, args=args).get_web_list()

        # Init global Timer
        self.timer_ports = Timer(0)

        # Global Thread running all the scans
        self._thread = None

    def exit(self):
        """Overwrite the exit method to close threads."""
        if self._thread is not None:
            self._thread.stop()
        # Call the father class
        super(Plugin, self).exit()

    @GlancesPlugin._log_result_decorator
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
            if self.timer_ports.finished() and not thread_is_running:
                # Run ports scanner
                self._thread = ThreadScanner(self.stats)
                self._thread.start()
                # Restart timer
                if len(self.stats) > 0:
                    self.timer_ports = Timer(self.stats[0]['refresh'])
                else:
                    self.timer_ports = Timer(0)
        else:
            # Not available in SNMP mode
            pass

        return self.stats

    def get_key(self):
        """Return the key of the list."""
        return 'indice'

    def get_ports_alert(self, port, header="", log=False):
        """Return the alert status relative to the port scan return value."""
        ret = 'OK'
        if port['status'] is None:
            ret = 'CAREFUL'
        elif port['status'] == 0:
            ret = 'CRITICAL'
        elif (isinstance(port['status'], (float, int)) and
              port['rtt_warning'] is not None and
              port['status'] > port['rtt_warning']):
            ret = 'WARNING'

        # Get stat name
        stat_name = self.get_stat_name(header=header)

        # Manage threshold
        self.manage_threshold(stat_name, ret)

        # Manage action
        self.manage_action(stat_name,
                           ret.lower(),
                           header,
                           port[self.get_key()])

        return ret

    def get_web_alert(self, web, header="", log=False):
        """Return the alert status relative to the web/url scan return value."""
        ret = 'OK'
        if web['status'] is None:
            ret = 'CAREFUL'
        elif web['status'] not in [200, 301, 302]:
            ret = 'CRITICAL'
        elif web['rtt_warning'] is not None and web['elapsed'] > web['rtt_warning']:
            ret = 'WARNING'

        # Get stat name
        stat_name = self.get_stat_name(header=header)

        # Manage threshold
        self.manage_threshold(stat_name, ret)

        # Manage action
        self.manage_action(stat_name,
                           ret.lower(),
                           header,
                           web[self.get_key()])

        return ret

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        # Only process if stats exist and display plugin enable...
        ret = []

        if not self.stats or args.disable_ports:
            return ret

        # Max size for the interface name
        name_max_width = max_width - 7

        # Build the string message
        for p in self.stats:
            if 'host' in p:
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
                    status = '{0:.0f}ms'.format(p['status'] * 1000.0)

                msg = '{:{width}}'.format(p['description'][0:name_max_width],
                                          width=name_max_width)
                ret.append(self.curse_add_line(msg))
                msg = '{:>9}'.format(status)
                ret.append(self.curse_add_line(msg,
                                               self.get_ports_alert(p,
                                                                    header=p['indice'] + '_rtt')))
                ret.append(self.curse_new_line())
            elif 'url' in p:
                msg = '{:{width}}'.format(p['description'][0:name_max_width],
                                          width=name_max_width)
                ret.append(self.curse_add_line(msg))
                if isinstance(p['status'], numbers.Number):
                    status = 'Code {}'.format(p['status'])
                elif p['status'] is None:
                    status = 'Scanning'
                else:
                    status = p['status']
                msg = '{:>9}'.format(status)
                ret.append(self.curse_add_line(msg,
                                               self.get_web_alert(p,
                                                                  header=p['indice'] + '_rtt')))
                ret.append(self.curse_new_line())

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
        logger.debug("ports plugin - Create thread for scan list {}".format(stats))
        super(ThreadScanner, self).__init__()
        # Event needed to stop properly the thread
        self._stopper = threading.Event()
        # The class return the stats as a list of dict
        self._stats = stats
        # Is part of Ports plugin
        self.plugin_name = "ports"

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
        logger.debug("ports plugin - Close thread for scan list {}".format(self._stats))
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.isSet()

    def _web_scan(self, web):
        """Scan the  Web/URL (dict) and update the status key."""
        try:
            req = requests.head(web['url'],
                                allow_redirects=True,
                                verify=web['ssl_verify'],
                                proxies=web['proxies'],
                                timeout=web['timeout'])
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
        else:
            return self._port_scan_tcp(port)

    def _resolv_name(self, hostname):
        """Convert hostname to IP address."""
        ip = hostname
        try:
            ip = socket.gethostbyname(hostname)
        except Exception as e:
            logger.debug("{}: Cannot convert {} to IP address ({})".format(self.plugin_name, hostname, e))
        return ip

    def _port_scan_icmp(self, port):
        """Scan the (ICMP) port structure (dict) and update the status key."""
        ret = None

        # Create the ping command
        # Use the system ping command because it already have the steacky bit set
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
        cmd = ['ping',
               count_opt, '1',
               timeout_opt, str(self._resolv_name(port['timeout'])),
               self._resolv_name(port['host'])]
        fnull = open(os.devnull, 'w')

        try:
            counter = Counter()
            ret = subprocess.check_call(cmd, stdout=fnull, stderr=fnull, close_fds=True)
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        except subprocess.CalledProcessError as e:
            # Correct issue #1084: No Offline status for timeouted ports
            port['status'] = False
        except Exception as e:
            logger.debug("{}: Error while pinging host {} ({})".format(self.plugin_name, port['host'], e))

        return ret

    def _port_scan_tcp(self, port):
        """Scan the (TCP) port structure (dict) and update the status key."""
        ret = None

        # Create and configure the scanning socket
        try:
            socket.setdefaulttimeout(port['timeout'])
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            logger.debug("{}: Error while creating scanning socket".format(self.plugin_name))

        # Scan port
        ip = self._resolv_name(port['host'])
        counter = Counter()
        try:
            ret = _socket.connect_ex((ip, int(port['port'])))
        except Exception as e:
            logger.debug("{}: Error while scanning port {} ({})".format(self.plugin_name, port, e))
        else:
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        finally:
            _socket.close()

        return ret
