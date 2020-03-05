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

"""Glances main class."""

import argparse
import sys
import tempfile

from glances import __version__, psutil_version
from glances.compat import input
from glances.config import Config
from glances.globals import WINDOWS
from glances.logger import logger, LOG_FILENAME


def disable(class_name, var):
    """Set disable_<var> to True in the class class_name."""
    setattr(class_name, 'disable_' + var, True)


def enable(class_name, var):
    """Set disable_<var> to False in the class class_name."""
    setattr(class_name, 'disable_' + var, False)


class GlancesMain(object):
    """Main class to manage Glances instance."""

    # Default stats' refresh time is 3 seconds
    refresh_time = 3
    # Set the default cache lifetime to 1 second (only for server)
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

    # Examples of use
    example_of_use = """
Examples of use:
  Monitor local machine (standalone mode):
    $ glances

  Display all Glances modules (plugins and exporters) and exit:
    $ glances --module-list

  Monitor local machine with the Web interface and start RESTful server:
    $ glances -w
    Glances web server started on http://0.0.0.0:61208/

  Only start RESTful API (without the WebUI):
    $ glances -w --disable-webui
    Glances API available on http://0.0.0.0:61208/api/

  Monitor local machine and export stats to a CSV file (standalone mode):
    $ glances --export csv --export-csv-file /tmp/glances.csv

  Monitor local machine and export stats to a InfluxDB server with 5s refresh time (standalone mode):
    $ glances -t 5 --export influxdb

  Start a Glances XML/RCP server (server mode):
    $ glances -s

  Connect Glances to a Glances XML/RCP server (client mode):
    $ glances -c <ip_server>

  Connect Glances to a Glances server and export stats to a StatsD server (client mode):
    $ glances -c <ip_server> --export statsd

  Start the client browser (browser mode):
    $ glances --browser

  Display stats to stdout (one stat per line):
    $ glances --stdout now,cpu.user,mem.used,load

  Display CSV stats to stdout (all stats in one line):
    $ glances --stdout-csv now,cpu.user,mem.used,load

  Disable some plugins (comma separated list):
    $ glances --disable-plugin network,ports

  Enable some plugins (comma separated list):
    $ glances --enable-plugin sensors
"""

    def __init__(self):
        """Manage the command line arguments."""
        # Read the command line arguments
        self.args = self.parse_args()

    def init_args(self):
        """Init all the command line arguments."""
        version = 'Glances v{} with PsUtil v{}\nLog file: {}'.format(__version__, psutil_version, LOG_FILENAME)
        parser = argparse.ArgumentParser(
            prog='glances',
            conflict_handler='resolve',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self.example_of_use)
        parser.add_argument(
            '-V', '--version', action='version', version=version)
        parser.add_argument('-d', '--debug', action='store_true', default=False,
                            dest='debug', help='enable debug mode')
        parser.add_argument('-C', '--config', dest='conf_file',
                            help='path to the configuration file')
        # Disable plugin
        parser.add_argument('--modules-list', '--module-list',
                            action='store_true', default=False,
                            dest='modules_list',
                            help='display modules (plugins & exports) list and exit')
        parser.add_argument('--disable-plugin', '--disable-plugins', dest='disable_plugin',
                            help='disable plugin (comma separed list)')
        parser.add_argument('--enable-plugin', '--enable-plugins', dest='enable_plugin',
                            help='enable plugin (comma separed list)')
        parser.add_argument('--disable-process', action='store_true', default=False,
                            dest='disable_process', help='disable process module')
        # Enable or disable option
        parser.add_argument('--disable-webui', action='store_true', default=False,
                            dest='disable_webui', help='disable the Web Interface')
        parser.add_argument('--light', '--enable-light', action='store_true',
                            default=False, dest='enable_light',
                            help='light mode for Curses UI (disable all but top menu)')
        parser.add_argument('-0', '--disable-irix', action='store_true', default=False,
                            dest='disable_irix', help='task\'s cpu usage will be divided by the total number of CPUs')
        parser.add_argument('-1', '--percpu', action='store_true', default=False,
                            dest='percpu', help='start Glances in per CPU mode')
        parser.add_argument('-2', '--disable-left-sidebar', action='store_true',
                            default=False, dest='disable_left_sidebar',
                            help='disable network, disk I/O, FS and sensors modules')
        parser.add_argument('-3', '--disable-quicklook', action='store_true', default=False,
                            dest='disable_quicklook', help='disable quick look module')
        parser.add_argument('-4', '--full-quicklook', action='store_true', default=False,
                            dest='full_quicklook', help='disable all but quick look and load')
        parser.add_argument('-5', '--disable-top', action='store_true',
                            default=False, dest='disable_top',
                            help='disable top menu (QL, CPU, MEM, SWAP and LOAD)')
        parser.add_argument('-6', '--meangpu', action='store_true', default=False,
                            dest='meangpu', help='start Glances in mean GPU mode')
        parser.add_argument('--disable-history', action='store_true', default=False,
                            dest='disable_history', help='disable stats history')
        parser.add_argument('--disable-bold', action='store_true', default=False,
                            dest='disable_bold', help='disable bold mode in the terminal')
        parser.add_argument('--disable-bg', action='store_true', default=False,
                            dest='disable_bg', help='disable background colors in the terminal')
        parser.add_argument('--enable-irq', action='store_true', default=False,
                            dest='enable_irq', help='enable IRQ module'),
        parser.add_argument('--enable-process-extended', action='store_true', default=False,
                            dest='enable_process_extended', help='enable extended stats on top process')
        # Export modules feature
        parser.add_argument('--export', dest='export',
                            help='enable export module (comma separed list)')
        parser.add_argument('--export-csv-file',
                            default='./glances.csv',
                            dest='export_csv_file',
                            help='file path for CSV exporter')
        parser.add_argument('--export-csv-overwrite', action='store_true', default=False,
                            dest='export_csv_overwrite', help='overwrite existing CSV file')
        parser.add_argument('--export-json-file',
                            default='./glances.json',
                            dest='export_json_file',
                            help='file path for JSON exporter')
        parser.add_argument('--export-graph-path',
                            default=tempfile.gettempdir(),
                            dest='export_graph_path',
                            help='Folder for Graph exporter')
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
                            help='define the client/server TCP port [default: {}]'.format(self.server_port))
        parser.add_argument('-B', '--bind', default='0.0.0.0', dest='bind_address',
                            help='bind server to the given IPv4/IPv6 address or hostname')
        parser.add_argument('--username', action='store_true', default=False, dest='username_prompt',
                            help='define a client/server username')
        parser.add_argument('--password', action='store_true', default=False, dest='password_prompt',
                            help='define a client/server password')
        parser.add_argument('-u', dest='username_used',
                            help='use the given client/server username')
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
                            dest='time', help='set refresh time in seconds [default: {} sec]'.format(self.refresh_time))
        parser.add_argument('-w', '--webserver', action='store_true', default=False,
                            dest='webserver', help='run Glances in web server mode (bottle needed)')
        parser.add_argument('--cached-time', default=self.cached_time, type=int,
                            dest='cached_time', help='set the server cache time [default: {} sec]'.format(self.cached_time))
        parser.add_argument('--open-web-browser', action='store_true', default=False,
                            dest='open_web_browser', help='try to open the Web UI in the default Web browser')
        # Display options
        parser.add_argument('-q', '--quiet', default=False, action='store_true',
                            dest='quiet', help='do not display the curses interface')
        parser.add_argument('-f', '--process-filter', default=None, type=str,
                            dest='process_filter', help='set the process filter pattern (regular expression)')
        parser.add_argument('--process-short-name', action='store_true', default=False,
                            dest='process_short_name', help='force short name for processes name')
        parser.add_argument('--stdout', default=None,
                            dest='stdout', help='display stats to stdout, one stat per line (comma separated list of plugins/plugins.attribute)')
        parser.add_argument('--stdout-csv', default=None,
                            dest='stdout_csv', help='display stats to stdout, csv format (comma separated list of plugins/plugins.attribute)')
        if not WINDOWS:
            parser.add_argument('--hide-kernel-threads', action='store_true', default=False,
                                dest='no_kernel_threads', help='hide kernel threads in process list (not available on Windows)')
        parser.add_argument('-b', '--byte', action='store_true', default=False,
                            dest='byte', help='display network rate in byte per second')
        parser.add_argument('--diskio-show-ramfs', action='store_true', default=False,
                            dest='diskio_show_ramfs', help='show RAM Fs in the DiskIO plugin')
        parser.add_argument('--diskio-iops', action='store_true', default=False,
                            dest='diskio_iops', help='show IO per second in the DiskIO plugin')
        parser.add_argument('--fahrenheit', action='store_true', default=False,
                            dest='fahrenheit', help='display temperature in Fahrenheit (default is Celsius)')
        parser.add_argument('--fs-free-space', action='store_true', default=False,
                            dest='fs_free_space', help='display FS free space instead of used')
        parser.add_argument('--sparkline', action='store_true', default=False,
                            dest='sparkline', help='display sparklines instead of bar in the curses interface')
        parser.add_argument('--theme-white', action='store_true', default=False,
                            dest='theme_white', help='optimize display colors for white background')
        # Globals options
        parser.add_argument('--disable-check-update', action='store_true', default=False,
                            dest='disable_check_update', help='disable online Glances version ckeck')
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
        else:
            from warnings import simplefilter
            simplefilter("ignore")

        # Plugins disable/enable
        # Allow users to disable plugins from the glances.conf (issue #1378)
        for s in self.config.sections():
            if self.config.has_section(s) \
               and (self.config.get_bool_value(s, 'disable', False)):
                disable(args, s)
                logger.debug('{} disabled by the configuration file'.format(s))
        # The configuration key can be overwrite from the command line
        if args.disable_plugin is not None:
            for p in args.disable_plugin.split(','):
                disable(args, p)
        if args.enable_plugin is not None:
            for p in args.enable_plugin.split(','):
                enable(args, p)

        # Exporters activation
        if args.export is not None:
            for p in args.export.split(','):
                setattr(args, 'export_' + p, True)

        # Client/server Port
        if args.port is None:
            if args.webserver:
                args.port = self.web_server_port
            else:
                args.port = self.server_port
        # Port in the -c URI #996
        if args.client is not None:
            args.client, args.port = (x if x else y for (x, y) in zip(args.client.partition(':')[::2], (args.client, args.port)))

        # Autodiscover
        if args.disable_autodiscover:
            logger.info("Auto discover mode is disabled")

        # In web server mode
        if args.webserver:
            args.process_short_name = True

        # Server or client login/password
        if args.username_prompt:
            # Every username needs a password
            args.password_prompt = True
            # Prompt username
            if args.server:
                args.username = self.__get_username(
                    description='Define the Glances server username: ')
            elif args.webserver:
                args.username = self.__get_username(
                    description='Define the Glances webserver username: ')
            elif args.client:
                args.username = self.__get_username(
                    description='Enter the Glances server username: ')
        else:
            if args.username_used:
                # A username has been set using the -u option ?
                args.username = args.username_used
            else:
                # Default user name is 'glances'
                args.username = self.username

        if args.password_prompt or args.username_used:
            # Interactive or file password
            if args.server:
                args.password = self.__get_password(
                    description='Define the Glances server password ({} username): '.format(
                        args.username),
                    confirm=True,
                    username=args.username)
            elif args.webserver:
                args.password = self.__get_password(
                    description='Define the Glances webserver password ({} username): '.format(
                        args.username),
                    confirm=True,
                    username=args.username)
            elif args.client:
                args.password = self.__get_password(
                    description='Enter the Glances server password ({} username): '.format(
                        args.username),
                    clear=True,
                    username=args.username)
        else:
            # Default is no password
            args.password = self.password

        # By default help is hidden
        args.help_tag = False

        # Display Rx and Tx, not the sum for the network
        args.network_sum = False
        args.network_cumul = False

        # Manage light mode
        if args.enable_light:
            logger.info("Light mode is on")
            args.disable_left_sidebar = True
            disable(args, 'process')
            disable(args, 'alert')
            disable(args, 'amps')
            disable(args, 'docker')

        # Manage full quicklook option
        if args.full_quicklook:
            logger.info("Full quicklook mode")
            enable(args, 'quicklook')
            disable(args, 'cpu')
            disable(args, 'mem')
            disable(args, 'memswap')
            enable(args, 'load')

        # Manage disable_top option
        if args.disable_top:
            logger.info("Disable top menu")
            disable(args, 'quicklook')
            disable(args, 'cpu')
            disable(args, 'mem')
            disable(args, 'memswap')
            disable(args, 'load')

        # Init the generate_graph tag
        # Should be set to True to generate graphs
        args.generate_graph = False

        # Control parameter and exit if it is not OK
        self.args = args

        # Export is only available in standalone or client mode (issue #614)
        export_tag = self.args.export is not None and any(self.args.export)
        if WINDOWS and export_tag:
            # On Windows, export is possible but only in quiet mode
            # See issue #1038
            logger.info("On Windows OS, export disable the Web interface")
            self.args.quiet = True
            self.args.webserver = False
        elif not (self.is_standalone() or self.is_client()) and export_tag:
            logger.critical("Export is only available in standalone or client mode")
            sys.exit(2)

        # Filter is only available in standalone mode
        if args.process_filter is not None and not self.is_standalone():
            logger.critical(
                "Process filter is only available in standalone mode")
            sys.exit(2)

        # Disable HDDTemp if sensors are disabled
        if getattr(args, 'disable_sensors', False):
            disable(args, 'hddtemp')
            logger.debug("Sensors and HDDTemp are disabled")

        return args

    def is_standalone(self):
        """Return True if Glances is running in standalone mode."""
        return (not self.args.client and
                not self.args.browser and
                not self.args.server and
                not self.args.webserver)

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

    def get_mode(self):
        """Return the mode."""
        return self.mode

    def __get_username(self, description=''):
        """Read an username from the command line."""
        return input(description)

    def __get_password(self, description='',
                       confirm=False, clear=False, username='glances'):
        """Read a password from the command line.

        - if confirm = True, with confirmation
        - if clear = True, plain (clear password)
        """
        from glances.password import GlancesPassword
        password = GlancesPassword(username=username)
        return password.get_password(description, confirm, clear)
