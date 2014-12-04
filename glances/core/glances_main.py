# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

"""Glances main class."""

# Import system libs
import argparse
import os
import sys
import tempfile

# Import Glances libs
from glances.core.glances_config import Config
from glances.core.glances_globals import appname, is_windows, logger, psutil_version, version


class GlancesMain(object):

    """Main class to manage Glances instance."""

    # Default stats' refresh time is 3 seconds
    refresh_time = 3

    # Set the default cache lifetime to 1 second (only for server)
    # !!! Todo: configuration from the command line
    cached_time = 1
    # By default, Glances is ran in standalone mode (no client/server)
    client_tag = False
    # Server TCP port number (default is 61209)
    server_port = 61209
    # Web Server TCP port number (default is 61208)
    web_server_port = 61208
    # Default username/password for client/server mode
    username = "glances"
    password = ""

    def __init__(self):
        """Manage the command line arguments."""
        self.args = self.parse_args()

    def init_args(self):
        """Init all the command line arguments."""
        _version = "Glances v" + version + " with psutil v" + psutil_version
        parser = argparse.ArgumentParser(
            prog=appname, conflict_handler='resolve')
        parser.add_argument(
            '-V', '--version', action='version', version=_version)
        parser.add_argument('-d', '--debug', action='store_true', default=False,
                            dest='debug', help=_('Enable debug mode'))
        parser.add_argument('-C', '--config', dest='conf_file',
                            help=_('path to the configuration file'))
        # Enable or disable option on startup
        parser.add_argument('--disable-network', action='store_true', default=False,
                            dest='disable_network', help=_('disable network module'))
        parser.add_argument('--disable-diskio', action='store_true', default=False,
                            dest='disable_diskio', help=_('disable disk I/O module'))
        parser.add_argument('--disable-fs', action='store_true', default=False,
                            dest='disable_fs', help=_('disable filesystem module'))
        parser.add_argument('--disable-sensors', action='store_true', default=False,
                            dest='disable_sensors', help=_('disable sensors module'))
        parser.add_argument('--disable-left-sidebar', action='store_true', default=False,
                            dest='disable_left_sidebar', help=_('disable network, disk io, FS and sensors modules'))
        parser.add_argument('--disable-process', action='store_true', default=False,
                            dest='disable_process', help=_('disable process module'))
        parser.add_argument('--disable-log', action='store_true', default=False,
                            dest='disable_log', help=_('disable log module'))
        parser.add_argument('--disable-bold', action='store_false', default=True,
                            dest='disable_bold', help=_('disable bold mode in the terminal'))
        parser.add_argument('--enable-process-extended', action='store_true', default=False,
                            dest='enable_process_extended', help=_('enable extended stats on top process'))
        parser.add_argument('--enable-history', action='store_true', default=False,
                            dest='enable_history', help=_('enable the history mode'))
        parser.add_argument('--path-history', default=tempfile.gettempdir(),
                            dest='path_history', help=_('Set the export path for graph history'))
        # CSV output feature
        parser.add_argument('--output-csv', default=None,
                            dest='output_csv', help=_('export stats to a CSV file'))
        # Client/Server option
        parser.add_argument('-c', '--client', dest='client',
                            help=_('connect to a Glances server by IPv4/IPv6 address or hostname'))
        parser.add_argument('-s', '--server', action='store_true', default=False,
                            dest='server', help=_('run Glances in server mode'))
        parser.add_argument('--browser', action='store_true', default=False,
                            dest='browser', help=_('start the client browser (list of servers)'))
        parser.add_argument('--disable-autodiscover', action='store_true', default=False,
                            dest='disable_autodiscover', help=_('disable autodiscover feature'))
        parser.add_argument('-p', '--port', default=None, type=int, dest='port',
                            help=_('define the client/server TCP port [default: {0}]').format(self.server_port))
        parser.add_argument('-B', '--bind', default='0.0.0.0', dest='bind_address',
                            help=_('bind server to the given IPv4/IPv6 address or hostname'))
        parser.add_argument('--password-badidea', dest='password_arg',
                            help=_('define password from the command line'))
        parser.add_argument('--password', action='store_true', default=False, dest='password_prompt',
                            help=_('define a client/server password from the prompt or file'))
        parser.add_argument('--snmp-community', default='public', dest='snmp_community',
                            help=_('SNMP community'))
        parser.add_argument('--snmp-port', default=161, type=int,
                            dest='snmp_port', help=_('SNMP port'))
        parser.add_argument('--snmp-version', default='2c', dest='snmp_version',
                            help=_('SNMP version (1, 2c or 3)'))
        parser.add_argument('--snmp-user', default='private', dest='snmp_user',
                            help=_('SNMP username (only for SNMPv3)'))
        parser.add_argument('--snmp-auth', default='password', dest='snmp_auth',
                            help=_('SNMP authentication key (only for SNMPv3)'))
        parser.add_argument('--snmp-force', action='store_true', default=False,
                            dest='snmp_force', help=_('force SNMP mode'))
        parser.add_argument('-t', '--time', default=self.refresh_time, type=float,
                            dest='time', help=_('set refresh time in seconds [default: {0} sec]').format(self.refresh_time))
        parser.add_argument('-w', '--webserver', action='store_true', default=False,
                            dest='webserver', help=_('run Glances in web server mode'))
        # Display options
        parser.add_argument('-f', '--process-filter', default=None, type=str,
                            dest='process_filter', help=_('set the process filter pattern (regular expression)'))
        parser.add_argument('--process-short-name', action='store_true', default=False,
                            dest='process_short_name', help=_('force short name for processes name'))
        if not is_windows:
            parser.add_argument('--hide-kernel-threads', action='store_true', default=False,
                                dest='no_kernel_threads', help=_('hide kernel threads in process list'))
        parser.add_argument('--tree', action='store_true', default=False,
                            dest='process_tree', help=_('display processes as a tree'))
        parser.add_argument('-b', '--byte', action='store_true', default=False,
                            dest='byte', help=_('display network rate in byte per second'))
        parser.add_argument('-1', '--percpu', action='store_true', default=False,
                            dest='percpu', help=_('start Glances in per CPU mode'))
        parser.add_argument('--fs-free-space', action='store_false', default=False,
                            dest='fs_free_space', help=_('display FS free space instead of used'))
        parser.add_argument('--theme-white', action='store_true', default=False,
                            dest='theme_white', help=_('optimize display for white background'))

        return parser

    def parse_args(self):
        """Parse command line arguments."""
        args = self.init_args().parse_args()

        # Load the configuration file, if it exists
        self.config = Config(args.conf_file)

        # Debug mode
        if args.debug:
            from logging import DEBUG
            logger.setLevel(DEBUG)

        # Client/server Port
        if args.port is None:
            if args.webserver:
                args.port = self.web_server_port
            else:
                args.port = self.server_port

        # Autodiscover
        if args.disable_autodiscover:
            logger.info("Auto discover mode is disabled")

        # In web server mode, defaul refresh time: 5 sec
        if args.webserver:
            args.time = 5

        # Server or client login/password
        args.username = self.username
        if args.password_arg is not None:
            from hashlib import sha256
            # Password is given as an argument
            # Hash with SHA256
            # Only the SHA will be transmit on the network
            args.password = sha256(args.password_arg).hexdigest()
        elif args.password_prompt:
            # Interactive or file password
            if args.server:
                args.password = self.__get_password(
                    description=_(
                        "Define the password for the Glances server"),
                    confirm=True)
            elif args.client:
                args.password = self.__get_password(
                    description=_("Enter the Glances server password"),
                    clear=True)
        else:
            # Default is no password
            args.password = self.password

        # By default help is hidden
        args.help_tag = False

        # Display Rx and Tx, not the sum for the network
        args.network_sum = False
        args.network_cumul = False

        # Control parameter and exit if it is not OK
        self.args = args

        # Filter is only available in standalone mode
        if args.process_filter is not None and not self.is_standalone():
            logger.critical("Process filter is only available in standalone mode")
            sys.exit(2)

        # Check graph output path
        if args.enable_history and args.path_history is not None:
            if not os.access(args.path_history, os.W_OK):
                logger.critical("History output path {0} do not exist or is not writable".format(args.path_history))
                sys.exit(2)
            logger.debug("History output path is set to {0}".format(args.path_history))

        return args

    def __hash_password(self, plain_password):
        """Hash a plain password and return the hashed one."""
        from glances.core.glances_password import GlancesPassword

        password = GlancesPassword()

        return password.hash_password(plain_password)

    def __get_password(self, description='', confirm=False, clear=False):
        """Read a password from the command line.

        - if confirm = True, with confirmation
        - if clear = True, plain (clear password)
        """
        from glances.core.glances_password import GlancesPassword

        password = GlancesPassword()

        return password.get_password(description, confirm, clear)

    def is_standalone(self):
        """Return True if Glances is running in standalone mode."""
        return not self.args.client and not self.args.browser and not self.args.server and not self.args.webserver

    def is_client(self):
        """Return True if Glances is running in client mode."""
        return (self.args.client or self.args.browser) and not self.args.server

    def is_client_browser(self):
        """Return True if Glances is running in client browser mode."""
        return self.args.browser and not self.args.server

    def is_server(self):
        """Return True if Glances is running in server mode."""
        return not self.args.client and self.args.server

    def is_webserver(self):
        """Return True if Glances is running in Web server mode."""
        return not self.args.client and self.args.webserver

    def get_config(self):
        """Return configuration file object."""
        return self.config

    def get_args(self):
        """Return the arguments."""
        return self.args
