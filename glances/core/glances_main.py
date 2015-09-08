# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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
from glances.core.glances_globals import appname, is_linux, is_windows, psutil_version, version
from glances.core.glances_logging import logger


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

    # Exemple of use
    example_of_use = "\
Examples of use:\n\
\n\
Monitor local machine (standalone mode):\n\
  $ glances\n\
\n\
Monitor local machine with the Web interface (Web UI):\n\
  $ glances -w\n\
  Glances web server started on http://0.0.0.0:61208/\n\
\n\
Monitor local machine and export stats to a CSV file (standalone mode):\n\
  $ glances --export-csv\n\
\n\
Monitor local machine and export stats to a InfluxDB server with 5s refresh time (standalone mode):\n\
  $ glances -t 5 --export-influxdb\n\
\n\
Start a Glances server (server mode):\n\
  $ glances -s\n\
\n\
Connect Glances to a Glances server (client mode):\n\
  $ glances -c <ip_server>\n\
\n\
Connect Glances to a Glances server and export stats to a StatsD server (client mode):\n\
  $ glances -c <ip_server> --export-statsd\n\
\n\
Start the client browser (browser mode):\n\
  $ glances --browser\n\
    "

    def __init__(self):
        """Manage the command line arguments."""
        self.args = self.parse_args()

    def init_args(self):
        """Init all the command line arguments."""
        _version = "Glances v" + version + " with psutil v" + psutil_version
        parser = argparse.ArgumentParser(
            prog=appname,
            conflict_handler='resolve',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self.example_of_use)
        parser.add_argument(
            '-V', '--version', action='version', version=_version)
        parser.add_argument('-d', '--debug', action='store_true', default=False,
                            dest='debug', help='enable debug mode')
        parser.add_argument('-C', '--config', dest='conf_file',
                            help='path to the configuration file')
        # Enable or disable option on startup
        parser.add_argument('-3', '--disable-quicklook', action='store_true', default=False,
                            dest='disable_quicklook', help='disable quick look module')
        parser.add_argument('-4', '--full-quicklook', action='store_true', default=False,
                            dest='full_quicklook', help='disable all but quick look and load')
        parser.add_argument('--disable-cpu', action='store_true', default=False,
                            dest='disable_cpu', help='disable CPU module')
        parser.add_argument('--disable-mem', action='store_true', default=False,
                            dest='disable_mem', help='disable memory module')
        parser.add_argument('--disable-swap', action='store_true', default=False,
                            dest='disable_swap', help='disable swap module')
        parser.add_argument('--disable-load', action='store_true', default=False,
                            dest='disable_load', help='disable load module')
        parser.add_argument('--disable-network', action='store_true', default=False,
                            dest='disable_network', help='disable network module')
        parser.add_argument('--disable-ip', action='store_true', default=False,
                            dest='disable_ip', help='disable IP module')
        parser.add_argument('--disable-diskio', action='store_true', default=False,
                            dest='disable_diskio', help='disable disk I/O module')
        parser.add_argument('--disable-fs', action='store_true', default=False,
                            dest='disable_fs', help='disable filesystem module')
        parser.add_argument('--disable-sensors', action='store_true', default=False,
                            dest='disable_sensors', help='disable sensors module')
        parser.add_argument('--disable-hddtemp', action='store_true', default=False,
                            dest='disable_hddtemp', help='disable HD temperature module')
        parser.add_argument('--disable-raid', action='store_true', default=False,
                            dest='disable_raid', help='disable RAID module')
        parser.add_argument('--disable-docker', action='store_true', default=False,
                            dest='disable_docker', help='disable Docker module')
        parser.add_argument('-2', '--disable-left-sidebar', action='store_true',
                            default=False, dest='disable_left_sidebar',
                            help='disable network, disk I/O, FS and sensors modules (py3sensors needed)')
        parser.add_argument('--disable-process', action='store_true', default=False,
                            dest='disable_process', help='disable process module')
        parser.add_argument('--disable-log', action='store_true', default=False,
                            dest='disable_log', help='disable log module')
        parser.add_argument('--disable-bold', action='store_false', default=True,
                            dest='disable_bold', help='disable bold mode in the terminal')
        parser.add_argument('--enable-process-extended', action='store_true', default=False,
                            dest='enable_process_extended', help='enable extended stats on top process')
        parser.add_argument('--enable-history', action='store_true', default=False,
                            dest='enable_history', help='enable the history mode (matplotlib needed)')
        parser.add_argument('--path-history', default=tempfile.gettempdir(),
                            dest='path_history', help='set the export path for graph history')
        # Export modules feature
        parser.add_argument('--export-csv', default=None,
                            dest='export_csv', help='export stats to a CSV file')
        parser.add_argument('--export-influxdb', action='store_true', default=False,
                            dest='export_influxdb', help='export stats to an InfluxDB server (influxdb needed)')
        parser.add_argument('--export-opentsdb', action='store_true', default=False,
                            dest='export_opentsdb', help='export stats to an OpenTSDB server (potsdb needed)')
        parser.add_argument('--export-statsd', action='store_true', default=False,
                            dest='export_statsd', help='export stats to a StatsD server (statsd needed)')
        parser.add_argument('--export-rabbitmq', action='store_true', default=False,
                            dest='export_rabbitmq', help='export stats to rabbitmq broker (pika needed)')
        # Client/Server option
        parser.add_argument('-c', '--client', dest='client',
                            help='connect to a Glances server by IPv4/IPv6 address or hostname')
        parser.add_argument('-s', '--server', action='store_true', default=False,
                            dest='server', help='run Glances in server mode')
        parser.add_argument('--browser', action='store_true', default=False,
                            dest='browser', help='start the client browser (list of servers)')
        parser.add_argument('--disable-autodiscover', action='store_true', default=False,
                            dest='disable_autodiscover', help='disable autodiscover feature')
        parser.add_argument('-p', '--port', default=None, type=int, dest='port',
                            help='define the client/server TCP port [default: {0}]'.format(self.server_port))
        parser.add_argument('-B', '--bind', default='0.0.0.0', dest='bind_address',
                            help='bind server to the given IPv4/IPv6 address or hostname')
        parser.add_argument('--password', action='store_true', default=False, dest='password_prompt',
                            help='define a client/server password')
        parser.add_argument('--snmp-community', default='public', dest='snmp_community',
                            help='SNMP community')
        parser.add_argument('--snmp-port', default=161, type=int,
                            dest='snmp_port', help='SNMP port')
        parser.add_argument('--snmp-version', default='2c', dest='snmp_version',
                            help='SNMP version (1, 2c or 3)')
        parser.add_argument('--snmp-user', default='private', dest='snmp_user',
                            help='SNMP username (only for SNMPv3)')
        parser.add_argument('--snmp-auth', default='password', dest='snmp_auth',
                            help='SNMP authentication key (only for SNMPv3)')
        parser.add_argument('--snmp-force', action='store_true', default=False,
                            dest='snmp_force', help='force SNMP mode')
        parser.add_argument('-t', '--time', default=self.refresh_time, type=float,
                            dest='time', help='set refresh time in seconds [default: {0} sec]'.format(self.refresh_time))
        parser.add_argument('-w', '--webserver', action='store_true', default=False,
                            dest='webserver', help='run Glances in web server mode (bottle needed)')
        # Display options
        parser.add_argument('-q', '--quiet', default=False, action='store_true',
                            dest='quiet', help='do not display the curses interface')
        parser.add_argument('-f', '--process-filter', default=None, type=str,
                            dest='process_filter', help='set the process filter pattern (regular expression)')
        parser.add_argument('--process-short-name', action='store_true', default=False,
                            dest='process_short_name', help='force short name for processes name')
        parser.add_argument('-0', '--disable-irix', action='store_true', default=False,
                            dest='disable_irix', help='Task\'s cpu usage will be divided by the total number of CPUs')
        if not is_windows:
            parser.add_argument('--hide-kernel-threads', action='store_true', default=False,
                                dest='no_kernel_threads', help='hide kernel threads in process list')
        if is_linux:
            parser.add_argument('--tree', action='store_true', default=False,
                                dest='process_tree', help='display processes as a tree')
        parser.add_argument('-b', '--byte', action='store_true', default=False,
                            dest='byte', help='display network rate in byte per second')
        parser.add_argument('--fahrenheit', action='store_true', default=False,
                            dest='fahrenheit', help='display temperature in Fahrenheit (default is Celsius)')
        parser.add_argument('-1', '--percpu', action='store_true', default=False,
                            dest='percpu', help='start Glances in per CPU mode')
        parser.add_argument('--fs-free-space', action='store_false', default=False,
                            dest='fs_free_space', help='display FS free space instead of used')
        parser.add_argument('--theme-white', action='store_true', default=False,
                            dest='theme_white', help='optimize display colors for white background')

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
            args.process_short_name = True

        # Server or client login/password
        args.username = self.username
        if args.password_prompt:
            # Interactive or file password
            if args.server:
                args.password = self.__get_password(
                    description='Define the password for the Glances server',
                    confirm=True)
            elif args.webserver:
                args.password = self.__get_password(
                    description='Define the password for the Glances web server\nUser name: glances',
                    confirm=True)
            elif args.client:
                args.password = self.__get_password(
                    description='Enter the Glances server password',
                    clear=True)
        else:
            # Default is no password
            args.password = self.password

        # By default help is hidden
        args.help_tag = False

        # Display Rx and Tx, not the sum for the network
        args.network_sum = False
        args.network_cumul = False

        # Manage full quicklook option
        if args.full_quicklook:
            args.disable_quicklook = False
            args.disable_cpu = True
            args.disable_mem = True
            args.disable_swap = True
            args.disable_load = False
        else:
            args.disable_quicklook = False
            args.disable_cpu = False
            args.disable_mem = False
            args.disable_swap = False
            args.disable_load = False

        # Control parameter and exit if it is not OK
        self.args = args

        # Export is only available in standalone or client mode (issue #614)
        export_tag = args.export_csv or args.export_statsd or args.export_influxdb or args.export_opentsdb or args.export_rabbitmq
        if not (self.is_standalone() or self.is_client()) and export_tag:
            logger.critical("Export is only available in standalone or client mode")
            sys.exit(2)

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

        # Disable HDDTemp if sensors are disabled
        if args.disable_sensors:
            args.disable_hddtemp = True
            logger.debug("Sensors and HDDTemp are disabled")

        return args

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
