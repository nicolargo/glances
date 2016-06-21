# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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
import types

from glances.globals import WINDOWS
from glances.ports_list import GlancesPortsList
from glances.timer import Timer, Counter
from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances ports scanner plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)
        self.args = args
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.stats = GlancesPortsList(config=config, args=args).get_ports_list()

        # Init global Timer
        self.timer_ports = Timer(0)

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the ports list."""

        if self.args.disable_ports:
            return {}

        if self.input_method == 'local':
            # Only refresh every refresh seconds (define in the configuration file)
            if self.timer_ports.finished():
                # Run ports scanner
                thread = threading.Thread(target=self._port_scan_all, args=(self.stats,))
                thread.start()
                # Restart timer
                if len(self.stats) > 0:
                    self.timer_ports = Timer(int(self.stats[0]['refresh']))
                else:
                    self.timer_ports = Timer(0)
        else:
            # Not available in SNMP mode
            pass

        return self.stats

    def get_alert(self, port, header="", log=False):
        """Return the alert status relative to the port scan return value."""

        if port['status'] is None:
            return 'CAREFUL'

        if port['status'] == 0:
            return 'CRITICAL'

        return 'OK'

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        # Only process if stats exist and display plugin enable...
        ret = []

        if not self.stats or self.args.disable_ports:
            return ret

        # Build the string message
        for p in self.stats:
            if p['status'] is None:
                status = 'Scanning'
            elif isinstance(p['status'], types.BooleanType) and p['status'] is True:
                status = 'Open'
            elif p['status'] == 0:
                status = 'Timeout'
            else:
                # Convert second to ms
                status = '{0:.0f}ms'.format(p['status'] * 1000.0)

            msg = '{:14.14} '.format(p['description'])
            ret.append(self.curse_add_line(msg))
            msg = '{:>8}'.format(status)
            ret.append(self.curse_add_line(msg, self.get_alert(p)))
            ret.append(self.curse_new_line())

        # Delete the last empty line
        try:
            ret.pop()
        except IndexError:
            pass

        return ret

    def _port_scan_all(self, stats):
        """Scan all host/port of the given stats"""
        for p in stats:
            self._port_scan(p)

    def _port_scan(self, port):
        """Scan the port structure (dict) and update the status key"""
        if int(port['port']) == 0:
            return self._port_scan_icmp(port)
        else:
            return self._port_scan_tcp(port)

    def _resolv_name(self, hostname):
        """Convert hostname to IP address"""
        ip = hostname
        try:
            ip = socket.gethostbyname(hostname)
        except Exception as e:
            logger.debug("{0}: Can not convert {1} to IP address ({2})".format(self.plugin_name, hostname, e))
        return ip

    def _port_scan_icmp(self, port):
        """Scan the (ICMP) port structure (dict) and update the status key"""
        ret = None

        # Create the ping command
        # Use the system ping command because it already have the steacky bit set
        # Python can not create ICMP packet with non root right
        cmd = ['ping', '-n' if WINDOWS else '-c', '1', self._resolv_name(port['host'])]
        fnull = open(os.devnull, 'w')

        try:
            counter = Counter()
            ret = subprocess.check_call(cmd, stdout=fnull, stderr=fnull, close_fds=True)
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        except Exception as e:
            logger.debug("{0}: Error while pinging host ({2})".format(self.plugin_name, port['host'], e))

        logger.info("Ping {} ({}) in {} second".format(port['host'], self._resolv_name(port['host']), port['status']))
        return ret

    def _port_scan_tcp(self, port):
        """Scan the (TCP) port structure (dict) and update the status key"""
        ret = None

        # Create and configure the scanning socket
        try:
            socket.setdefaulttimeout(int(port['timeout']))
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            logger.debug("{0}: Error while creating scanning socket".format(self.plugin_name))

        # Scan port
        ip = self._resolv_name(port['host'])
        counter = Counter()
        try:
            ret = _socket.connect_ex((ip, int(port['port'])))
        except Exception as e:
            logger.debug("{0}: Error while scanning port {1} ({2})".format(self.plugin_name, port, e))
        else:
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        finally:
            _socket.close()

        return ret
