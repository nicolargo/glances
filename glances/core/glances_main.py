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
"""
Main Glances script
"""

# Import system libs
import argparse
import sys

# Import Glances libs
from glances.core.glances_config import Config
from glances.core.glances_globals import (
    __appname__,
    __psutil_version__,
    __version__
)


class GlancesMain(object):
    """
    Main class to manage Glances instance
    """

    # Default stats' refresh time is 3 seconds
    refresh_time = 3
    # Set the default cache lifetime to 1 second (only for server)
    # !!! Todo: configuration from the command line
    cached_time = 1
    # Default network bitrate is display in bit per second
    # network_bytepersec_tag = False
    # Display (or not) module
    # diskio_tag = True
    # fs_tag = True
    # hddtemp_flag = True
    # network_tag = True
    # sensors_tag = True
    # process_tag = True
    # Display property
    # use_bold = True
    # percpu_tag = False
    # Default configuration file
    # conf_file_tag = True
    # conf_file = ""
    # Bind IP address (default is all interfaces)
    # bind_ip = "0.0.0.0"
    # By default, Glances is ran in standalone mode (no client/server)
    client_tag = False
    # server_tag = False
    # Server IP address (no default value)
    # server_ip = None
    # Server TCP port number (default is 61209)
    server_port = 61209
    # Web Server TCP port number (default is 61208)
    web_server_port = 61208
    # Default username/password for client/server mode
    username = "glances"
    password = ""
    # Output type (default is no output)
    # output_list = ['html', 'csv']
    html_tag = False
    csv_tag = False
    output_file = None
    output_folder = None

    def __init__(self):
        """Manage the command line arguments."""
        self.args = self.parse_args()

    def init_args(self):
        """Init all the command line arguments."""
        version = "Glances v" + __version__ + " with psutil v" + __psutil_version__
        parser = argparse.ArgumentParser(prog=__appname__, conflict_handler='resolve')
        parser.add_argument('--version', action='version', version=version)
        parser.add_argument('-b', '--byte', action='store_true', default=False,
                            dest='byte', help=_('display network rate in byte per second'))
        parser.add_argument('-B', '--bind', default='0.0.0.0', dest='bind_address',
                            help=_('bind server to the given IPv4/IPv6 address or hostname'))
        parser.add_argument('-c', '--client', dest='client',
                            help=_('connect to a Glances server by IPv4/IPv6 address or hostname'))
        parser.add_argument('-C', '--config', dest='conf_file',
                            help=_('path to the configuration file'))
        parser.add_argument('--disable-bold', action='store_false', default=True,
                            dest='disable_bold', help=_('disable bold mode in the terminal'))
        parser.add_argument('--disable-diskio', action='store_true', default=False,
                            dest='disable_diskio', help=_('disable disk I/O module'))
        parser.add_argument('--disable-fs', action='store_true', default=False,
                            dest='disable_fs', help=_('disable filesystem module'))
        parser.add_argument('--disable-network', action='store_true', default=False,
                            dest='disable_network', help=_('disable network module'))
        parser.add_argument('--disable-sensors', action='store_true', default=False,
                            dest='disable_sensors', help=_('disable sensors module'))
        parser.add_argument('--disable-process', action='store_true', default=False,
                            dest='disable_process', help=_('disable process module'))
        parser.add_argument('--disable-log', action='store_true', default=False,
                            dest='disable_log', help=_('disable log module'))
        parser.add_argument('-f', '--file', dest='file',
                            help=_('set the HTML output folder or CSV file'))
        parser.add_argument('-o', '--output', choices=['HTML', 'CSV'], dest='output',
                            help=_("Define additional HTML or CSV output"))
        parser.add_argument('-p', '--port', default=self.server_port, type=int, dest='port',
                            help=_('define the client/server TCP port [default: %d]') % self.server_port)
        parser.add_argument('-P', '--password', dest='password_arg',
                            help=_('old method to define a client/server password'))
        parser.add_argument('--password', action='store_true', default=False, dest='password_prompt',
                            help=_('define a client/server password from the prompt'))
        parser.add_argument('-s', '--server', action='store_true', default=False,
                            dest='server', help=_('run Glances in server mode'))
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
        parser.add_argument('-t', '--time', default=self.refresh_time, type=int,
                            dest='seconds', help=_('set refresh time in seconds [default: %s sec]') % self.refresh_time)
        parser.add_argument('-w', '--webserver', action='store_true', default=False,
                            dest='webserver', help=_('run Glances in web server mode'))
        parser.add_argument('-1', '--percpu', action='store_true', default=False,
                            dest='percpu', help=_('start Glances in per CPU mode'))

        return parser

    def parse_args(self):
        """Parse command line arguments."""
        args = self.init_args().parse_args()

        # Load the configuration file, it it exists
        self.config = Config(args.conf_file)

        # In web server mode, default:
        # - refresh time: 5 sec
        # - host port: 61208
        if args.webserver:
            args.time = 5
            args.port = self.web_server_port

        # Server or client login/password
        args.username = self.username
        if args.password_arg is not None:
            # Password is passed as an argument
            args.password = args.password_arg
        elif args.password_prompt:
            # Interactive password
            if args.server:
                args.password = self.__get_password(
                    description=_("Define the password for the Glances server"),
                    confirm=True)
            elif args.client:
                args.password = self.__get_password(
                    description=_("Enter the Glances server password"),
                    confirm=False)
        else:
            # Default is no password
            args.password = self.password

        # !!! Change global variables regarding to user args
        # !!! To be refactor to use directly the args list in the code
        self.server_tag = args.server
        self.webserver_tag = args.webserver
        if args.client is not None:
            self.client_tag = True
            self.server_ip = args.client

        if args.output is not None:
            setattr(self, args.output.lower() + '_tag', True)
        if args.file is not None:
            output_file = args.file
            output_folder = args.file
        # /!!!

        # Interactive cmds like CLI args?
        # By default help is hidden
        args.help_tag = False

        # Display Rx and Tx, not the sum for the network
        args.network_sum = False
        args.network_cumul = False

        return args

    def __get_password(self, description='', confirm=False):
        """
        Read a password from the command line (with confirmation if confirm = True)
        """
        import getpass

        if description != '':
            sys.stdout.write("%s\n" % description)

        password1 = getpass.getpass(_("Password: "))
        if confirm:
            password2 = getpass.getpass(_("Password (confirm): "))
        else:
            return password1

        if password1 == password2:
            return password1
        else:
            sys.stdout.write(_("[Warning] Passwords did not match, please try again...\n"))
            return self.__get_password(description=description, confirm=confirm)

    def is_standalone(self):
        """
        Return True if Glances is running in standalone mode
        """
        return not self.client_tag and not self.server_tag and not self.webserver_tag

    def is_client(self):
        """
        Return True if Glances is running in client mode
        """
        return self.client_tag and not self.server_tag

    def is_server(self):
        """
        Return True if Glances is running in server mode
        """
        return not self.client_tag and self.server_tag

    def is_webserver(self):
        """
        Return True if Glances is running in Web server mode
        """
        return not self.client_tag and self.webserver_tag

    def get_config(self):
        """
        Return configuration file object
        """
        return self.config

    def get_args(self):
        """
        Return the arguments
        """
        return self.args
