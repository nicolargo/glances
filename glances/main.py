#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances main class."""

import argparse
import sys
import tempfile
from logging import DEBUG
from warnings import simplefilter

from glances import __apiversion__, __version__, psutil_version
from glances.config import Config
from glances.globals import WINDOWS, disable, enable
from glances.logger import LOG_FILENAME, logger
from glances.processes import sort_processes_stats_list


class GlancesMain:
    """Main class to manage Glances instance."""

    # Default stats' minimum refresh time is 2 seconds
    DEFAULT_REFRESH_TIME = 2
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

  Monitor local machine and export stats to a InfluxDB server with 5s refresh rate (standalone mode):
    $ glances -t 5 --export influxdb

  Start a Glances XML-RPC server (server mode):
    $ glances -s

  Connect Glances to a Glances XML-RPC server (client mode):
    $ glances -c <ip_server>

  Connect Glances to a Glances server and export stats to a StatsD server (client mode):
    $ glances -c <ip_server> --export statsd

  Start TUI Central Glances Browser:
    $ glances --browser

  Start WebUI Central Glances Browser:
    $ glances --browser -w

  Display stats to stdout (one stat per line, possible to go inside stats using plugin.attribute):
    $ glances --stdout now,cpu.user,mem.used,load

  Display JSON stats to stdout (one stats per line):
    $ glances --stdout-json now,cpu,mem,load

  Display CSV stats to stdout (all stats in one line):
    $ glances --stdout-csv now,cpu.user,mem.used,load

  Enable some plugins disabled by default (comma-separated list):
    $ glances --enable-plugin sensors

  Disable some plugins (comma-separated list):
    $ glances --disable-plugin network,ports

  Disable all plugins except some (comma-separated list):
    $ glances --disable-plugin all --enable-plugin cpu,mem,load

"""

    def __init__(self):
        """Manage the command line arguments."""
        # Read the command line arguments
        self.args = self.parse_args()

    def version_msg(self):
        """Return the version message."""
        version = f'Glances version:\t{__version__}\n'
        version += f'Glances API version:\t{__apiversion__}\n'
        version += f'PsUtil version:\t\t{psutil_version}\n'
        version += f'Log file:\t\t{LOG_FILENAME}\n'
        return version

    def init_args(self):
        """Init all the command line arguments."""
        parser = argparse.ArgumentParser(
            prog='glances',
            conflict_handler='resolve',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self.example_of_use,
        )
        parser.add_argument('-V', '--version', action='version', version=self.version_msg())
        parser.add_argument('-d', '--debug', action='store_true', default=False, dest='debug', help='enable debug mode')
        parser.add_argument('-C', '--config', dest='conf_file', help='path to the configuration file')
        parser.add_argument('-P', '--plugins', dest='plugin_dir', help='path to additional plugin directory')
        # Disable plugin
        parser.add_argument(
            '--modules-list',
            '--module-list',
            action='store_true',
            default=False,
            dest='modules_list',
            help='display modules (plugins & exports) list and exit',
        )
        parser.add_argument(
            '--disable-plugin',
            '--disable-plugins',
            '--disable',
            dest='disable_plugin',
            help='disable plugin (comma-separated list or all). If all is used, \
                then you need to configure --enable-plugin.',
        )
        parser.add_argument(
            '--enable-plugin',
            '--enable-plugins',
            '--enable',
            dest='enable_plugin',
            help='enable plugin (comma-separated list)',
        )
        parser.add_argument(
            '--disable-process',
            action='store_true',
            default=False,
            dest='disable_process',
            help='disable process module',
        )
        # Enable or disable option
        parser.add_argument(
            '--disable-webui',
            action='store_true',
            default=False,
            dest='disable_webui',
            help='disable the Web Interface',
        )
        parser.add_argument(
            '--light',
            '--enable-light',
            action='store_true',
            default=False,
            dest='enable_light',
            help='light mode for Curses UI (disable all but the top menu)',
        )
        parser.add_argument(
            '-0',
            '--disable-irix',
            action='store_true',
            default=False,
            dest='disable_irix',
            help='task\'s cpu usage will be divided by the total number of CPUs',
        )
        parser.add_argument(
            '-1',
            '--percpu',
            '--per-cpu',
            action='store_true',
            default=False,
            dest='percpu',
            help='start Glances in per CPU mode',
        )
        parser.add_argument(
            '-2',
            '--disable-left-sidebar',
            action='store_true',
            default=False,
            dest='disable_left_sidebar',
            help='disable network, disk I/O, FS and sensors modules',
        )
        parser.add_argument(
            '-3',
            '--disable-quicklook',
            action='store_true',
            default=False,
            dest='disable_quicklook',
            help='disable quick look module',
        )
        parser.add_argument(
            '-4',
            '--full-quicklook',
            action='store_true',
            default=False,
            dest='full_quicklook',
            help='disable all but quick look and load',
        )
        parser.add_argument(
            '-5',
            '--disable-top',
            action='store_true',
            default=False,
            dest='disable_top',
            help='disable top menu (QL, CPU, MEM, SWAP and LOAD)',
        )
        parser.add_argument(
            '-6', '--meangpu', action='store_true', default=False, dest='meangpu', help='start Glances in mean GPU mode'
        )
        parser.add_argument(
            '--disable-history',
            action='store_true',
            default=False,
            dest='disable_history',
            help='disable stats history',
        )
        parser.add_argument(
            '--disable-bold',
            action='store_true',
            default=False,
            dest='disable_bold',
            help='disable bold mode in the terminal',
        )
        parser.add_argument(
            '--disable-bg',
            action='store_true',
            default=False,
            dest='disable_bg',
            help='disable background colors in the terminal',
        )
        parser.add_argument(
            '--enable-irq', action='store_true', default=False, dest='enable_irq', help='enable IRQ module'
        )
        parser.add_argument(
            '--enable-process-extended',
            action='store_true',
            default=False,
            dest='enable_process_extended',
            help='enable extended stats on top process',
        )
        parser.add_argument(
            '--disable-separator',
            action='store_false',
            default=True,
            dest='enable_separator',
            help='disable separator in the UI (between top and others modules)',
        )
        parser.add_argument(
            '--disable-cursor',
            action='store_true',
            default=False,
            dest='disable_cursor',
            help='disable cursor (process selection) in the UI',
        )
        # Sort processes list
        parser.add_argument(
            '--sort-processes',
            dest='sort_processes_key',
            choices=sort_processes_stats_list,
            help='Sort processes by: {}'.format(', '.join(sort_processes_stats_list)),
        )
        # Display processes list by program name and not by thread
        parser.add_argument(
            '--programs',
            '--program',
            action='store_true',
            default=False,
            dest='programs',
            help='Accumulate processes by program',
        )
        # Export modules feature
        parser.add_argument('--export', dest='export', help='enable export module (comma-separated list)')
        parser.add_argument(
            '--export-csv-file', default='./glances.csv', dest='export_csv_file', help='file path for CSV exporter'
        )
        parser.add_argument(
            '--export-csv-overwrite',
            action='store_true',
            default=False,
            dest='export_csv_overwrite',
            help='overwrite existing CSV file',
        )
        parser.add_argument(
            '--export-json-file', default='./glances.json', dest='export_json_file', help='file path for JSON exporter'
        )
        parser.add_argument(
            '--export-graph-path',
            default=tempfile.gettempdir(),
            dest='export_graph_path',
            help='Folder for Graph exporter',
        )
        parser.add_argument(
            '--export-process-filter',
            default=None,
            type=str,
            dest='export_process_filter',
            help='set the export process filter (comman separated list of regular expression)',
        )
        # Client/Server option
        parser.add_argument(
            '-c', '--client', dest='client', help='connect to a Glances server by IPv4/IPv6 address or hostname'
        )
        parser.add_argument(
            '-s', '--server', action='store_true', default=False, dest='server', help='run Glances in server mode'
        )
        parser.add_argument(
            '--browser',
            action='store_true',
            default=False,
            dest='browser',
            help='start TUI Central Glances Browser (use --browser -w to start WebUI Central Glances Browser)',
        )
        parser.add_argument(
            '--disable-autodiscover',
            action='store_true',
            default=False,
            dest='disable_autodiscover',
            help='disable autodiscover feature',
        )
        parser.add_argument(
            '-p',
            '--port',
            default=None,
            type=int,
            dest='port',
            help=f'define the client/server TCP port [default: {self.server_port}]',
        )
        parser.add_argument(
            '-B',
            '--bind',
            default='0.0.0.0',
            dest='bind_address',
            help='bind server to the given IPv4/IPv6 address or hostname',
        )
        parser.add_argument(
            '--username',
            action='store_true',
            default=False,
            dest='username_prompt',
            help='define a client/server username',
        )
        parser.add_argument(
            '--password',
            action='store_true',
            default=False,
            dest='password_prompt',
            help='define a client/server password',
        )
        parser.add_argument('-u', dest='username_used', help='use the given client/server username')
        parser.add_argument('--snmp-community', default='public', dest='snmp_community', help='SNMP community')
        parser.add_argument('--snmp-port', default=161, type=int, dest='snmp_port', help='SNMP port')
        parser.add_argument('--snmp-version', default='2c', dest='snmp_version', help='SNMP version (1, 2c or 3)')
        parser.add_argument('--snmp-user', default='private', dest='snmp_user', help='SNMP username (only for SNMPv3)')
        parser.add_argument(
            '--snmp-auth', default='password', dest='snmp_auth', help='SNMP authentication key (only for SNMPv3)'
        )
        parser.add_argument(
            '--snmp-force', action='store_true', default=False, dest='snmp_force', help='force SNMP mode'
        )
        parser.add_argument(
            '-t',
            '--time',
            default=self.DEFAULT_REFRESH_TIME,
            type=float,
            dest='time',
            help=f'set minimum refresh rate in seconds [default: {self.DEFAULT_REFRESH_TIME} sec]',
        )
        parser.add_argument(
            '-w',
            '--webserver',
            action='store_true',
            default=False,
            dest='webserver',
            help='run Glances in web server mode (FastAPI, Uvicorn, Jinja2 libs needed)',
        )
        parser.add_argument(
            '--cached-time',
            default=self.cached_time,
            type=int,
            dest='cached_time',
            help=f'set the server cache time [default: {self.cached_time} sec]',
        )
        parser.add_argument(
            '--stop-after',
            default=None,
            type=int,
            dest='stop_after',
            help='stop Glances after n refresh',
        )
        parser.add_argument(
            '--open-web-browser',
            action='store_true',
            default=False,
            dest='open_web_browser',
            help='try to open the Web UI in the default Web browser',
        )
        # Display options
        parser.add_argument(
            '-q',
            '--quiet',
            default=False,
            action='store_true',
            dest='quiet',
            help='do not display the curses interface',
        )
        parser.add_argument(
            '-f',
            '--process-filter',
            default=None,
            type=str,
            dest='process_filter',
            help='set the process filter pattern (regular expression)',
        )
        parser.add_argument(
            '--process-short-name',
            action='store_true',
            default=True,
            dest='process_short_name',
            help='force short name for processes name',
        )
        parser.add_argument(
            '--process-long-name',
            action='store_false',
            default=False,
            dest='process_short_name',
            help='force long name for processes name',
        )
        parser.add_argument(
            '--stdout',
            default=None,
            dest='stdout',
            help='display stats to stdout, one stat per line (comma-separated list of plugins/plugins.attribute)',
        )
        parser.add_argument(
            '--stdout-json',
            default=None,
            dest='stdout_json',
            help='display stats to stdout, JSON format (comma-separated list of plugins/plugins.attribute)',
        )
        parser.add_argument(
            '--stdout-csv',
            default=None,
            dest='stdout_csv',
            help='display stats to stdout, CSV format (comma-separated list of plugins/plugins.attribute)',
        )
        parser.add_argument(
            '--issue',
            default=None,
            action='store_true',
            dest='stdout_issue',
            help='test all plugins and exit (please copy/paste the output if you open an issue)',
        )
        parser.add_argument(
            '--trace-malloc',
            default=False,
            action='store_true',
            dest='trace_malloc',
            help='trace memory allocation and display it at the end of the process (python 3.4 or higher needed)',
        )
        parser.add_argument(
            '--memory-leak',
            default=False,
            action='store_true',
            dest='memory_leak',
            help='test memory leak (python 3.4 or higher needed)',
        )
        parser.add_argument(
            '--api-doc', default=None, action='store_true', dest='stdout_apidoc', help='display fields descriptions'
        )
        if not WINDOWS:
            parser.add_argument(
                '--hide-kernel-threads',
                action='store_true',
                default=False,
                dest='no_kernel_threads',
                help='hide kernel threads in the process list (not available on Windows)',
            )
        parser.add_argument(
            '-b',
            '--byte',
            action='store_true',
            default=False,
            dest='byte',
            help='display network rate in bytes per second',
        )
        parser.add_argument(
            '--diskio-show-ramfs',
            action='store_true',
            default=False,
            dest='diskio_show_ramfs',
            help='show RAM Fs in the DiskIO plugin',
        )
        parser.add_argument(
            '--diskio-iops',
            action='store_true',
            default=False,
            dest='diskio_iops',
            help='show IO per second in the DiskIO plugin',
        )
        parser.add_argument(
            '--fahrenheit',
            action='store_true',
            default=False,
            dest='fahrenheit',
            help='display temperature in Fahrenheit (default is Celsius)',
        )
        parser.add_argument(
            '--fs-free-space',
            action='store_true',
            default=False,
            dest='fs_free_space',
            help='display FS free space instead of used',
        )
        parser.add_argument(
            '--sparkline',
            action='store_true',
            default=False,
            dest='sparkline',
            help='display sparklines instead of bar in the curses interface',
        )
        parser.add_argument(
            '--disable-unicode',
            action='store_true',
            default=False,
            dest='disable_unicode',
            help='disable unicode characters in the curses interface',
        )
        parser.add_argument(
            '--hide-public-info',
            action='store_true',
            default=False,
            help='hide public information (like public IP)',
        )
        # Globals options
        parser.add_argument(
            '--disable-check-update',
            action='store_true',
            default=False,
            dest='disable_check_update',
            help='disable online Glances version ckeck',
        )
        parser.add_argument(
            '--strftime',
            dest='strftime_format',
            default='',
            help='strftime format string for displaying current date in standalone mode',
        )

        return parser

    def init_debug(self, args):
        """Init Glances debug mode."""
        if args.debug:
            logger.setLevel(DEBUG)
        else:
            simplefilter("ignore")

    def init_refresh_rate(self, args):
        """Init Glances refresh rate"""
        if self.config.has_section('global'):
            global_refresh = self.config.get_float_value('global', 'refresh', default=self.DEFAULT_REFRESH_TIME)
        else:
            global_refresh = self.DEFAULT_REFRESH_TIME

        # The configuration key can be overwrite from the command line (-t <time>)
        if args.time == self.DEFAULT_REFRESH_TIME:
            args.time = global_refresh

        logger.debug(f'Global refresh rate is set to {args.time} seconds')

    def init_plugins(self, args):
        """Init Glances plugins"""
        # Allow users to disable plugins from the glances.conf (issue #1378)
        for s in self.config.sections():
            if self.config.has_section(s) and (self.config.get_bool_value(s, 'disable', False)):
                disable(args, s)
                logger.debug(f'{s} disabled by the configuration file')
        # The configuration key can be overwrite from the command line
        if args and args.disable_plugin and 'all' in args.disable_plugin.split(','):
            if not args.enable_plugin:
                logger.critical("'all' key in --disable-plugin needs to be used with --enable-plugin")
                sys.exit(2)
            else:
                logger.info(
                    "'all' key in --disable-plugin, only plugins defined with --enable-plugin will be available"
                )
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

        # By default help is hidden
        args.help_tag = False

        # Display Rx and Tx, not the sum for the network
        args.network_sum = False
        args.network_cumul = False

        # Processlist is updated in processcount
        if getattr(args, 'enable_processlist', False) or getattr(args, 'enable_programlist', False):
            enable(args, 'processcount')

        # Set a default export_process_filter (with all process) when using the stdout mode
        if getattr(args, 'stdout', True) and args.process_filter is None:
            setattr(args, 'export_process_filter', '.*')

    def init_client_server(self, args):
        """Init Glances client/server mode."""

        # Client/server Port
        if args.port is None:
            if args.webserver:
                args.port = self.web_server_port
            else:
                args.port = self.server_port
        # Port in the -c URI #996
        if args.client is not None:
            args.client, args.port = (
                x if x else y for (x, y) in zip(args.client.partition(':')[::2], (args.client, args.port))
            )

        # Client autodiscover mode
        if args.disable_autodiscover:
            logger.info("Auto discover mode is disabled")

        # Server or client login/password
        if args.username_prompt:
            # Every username needs a password
            args.password_prompt = True
            # Prompt username
            if args.server:
                args.username = self.__get_username(description='Define the Glances server username: ')
            elif args.webserver:
                args.username = self.__get_username(description='Define the Glances webserver username: ')
            elif args.client:
                args.username = self.__get_username(description='Enter the Glances server username: ')
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
                    description=f'Define the Glances server password ({args.username} username): ',
                    confirm=True,
                    username=args.username,
                )
            elif args.webserver:
                args.password = self.__get_password(
                    description=f'Define the Glances webserver password ({args.username} username): ',
                    confirm=True,
                    username=args.username,
                )
            elif args.client:
                args.password = self.__get_password(
                    description=f'Enter the Glances server password ({args.username} username): ',
                    clear=True,
                    username=args.username,
                )
        else:
            # Default is no password
            args.password = self.password

    def init_ui_mode(self, args):
        # Manage light mode
        if getattr(args, 'enable_light', False):
            logger.info("Light mode is on")
            args.disable_left_sidebar = True
            disable(args, 'process')
            disable(args, 'alert')
            disable(args, 'amps')
            disable(args, 'containers')
            disable(args, 'vms')

        # Manage full quicklook option
        if getattr(args, 'full_quicklook', False):
            logger.info("Full quicklook mode")
            enable(args, 'quicklook')
            disable(args, 'cpu')
            disable(args, 'mem')
            disable(args, 'memswap')
            enable(args, 'load')

        # Manage disable_top option
        if getattr(args, 'disable_top', False):
            logger.info("Disable top menu")
            disable(args, 'quicklook')
            disable(args, 'cpu')
            disable(args, 'mem')
            disable(args, 'memswap')
            disable(args, 'load')

        # Memory leak
        if getattr(args, 'memory_leak', False):
            logger.info('Memory leak detection enabled')
            args.quiet = True
            if not args.stop_after:
                args.stop_after = 60
            args.time = 1
            args.disable_history = True

        # Unicode => No separator
        if args.disable_unicode:
            args.enable_separator = False

    def parse_args(self):
        """Parse command line arguments."""
        args = self.init_args().parse_args()

        # Load the configuration file, if it exists
        # This function should be called after the parse_args
        # because the configuration file path can be defined
        self.config = Config(args.conf_file)

        # Init Glances debug mode
        self.init_debug(args)

        # Plugins Glances refresh rate
        self.init_refresh_rate(args)

        # Manage Plugins disable/enable option
        self.init_plugins(args)

        # Init Glances client/server mode
        self.init_client_server(args)

        # Init UI mode
        self.init_ui_mode(args)

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
        if not args.process_filter and not self.is_standalone():
            logger.debug("Process filter is only available in standalone mode")

        # Cursor option is only available in standalone mode
        if not args.disable_cursor and not self.is_standalone():
            logger.debug("Cursor is only available in standalone mode")

        # Let the plugins known the Glances mode
        self.args.is_standalone = self.is_standalone()
        self.args.is_client = self.is_client()
        self.args.is_client_browser = self.is_client_browser()
        self.args.is_server = self.is_server()
        self.args.is_webserver = self.is_webserver()

        # Check mode compatibility
        self.check_mode_compatibility()

        return args

    def check_mode_compatibility(self):
        """Check mode compatibility"""
        # Server and Web server are not compatible
        if self.args.is_server and self.args.is_webserver:
            logger.critical("Server and Web server modes should not be used together")
            sys.exit(2)

        # Trace malloc option
        if getattr(self.args, 'trace_malloc', True) and not self.is_standalone():
            logger.critical("Option --trace-malloc is only available in the terminal mode")
            sys.exit(2)

        # Memory leak option
        if getattr(self.args, 'memory_leak', True) and not self.is_standalone():
            logger.critical("Option --memory-leak is only available in the terminal mode")
            sys.exit(2)

    def is_standalone(self):
        """Return True if Glances is running in standalone mode."""
        return not self.args.client and not self.args.browser and not self.args.server and not self.args.webserver

    def is_client(self):
        """Return True if Glances is running in client mode."""
        return (self.args.client or self.args.browser) and not self.args.server and not self.args.webserver

    def is_client_browser(self):
        """Return True if Glances is running in client browser mode."""
        return self.args.browser and not self.args.server and not self.args.webserver

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

    def __get_password(self, description='', confirm=False, clear=False, username='glances'):
        """Read a password from the command line.

        - if confirm = True, with confirmation
        - if clear = True, plain (clear password)
        """
        from glances.password import GlancesPassword

        password = GlancesPassword(username=username, config=self.get_config())
        return password.get_password(description, confirm, clear)
