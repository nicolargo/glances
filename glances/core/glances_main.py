#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

# Import system libs
import sys
import os
import signal
import argparse

# Import Glances libs
# !!! Todo: rename class
# GlancesExemple
from glances.core.glances_globals import __appname__, __version__, __author__, __license__
from glances.core.glances_globals import *
from glances.core.glances_config import Config
from glances.core.glances_stats import GlancesStats, GlancesStatsServer

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
    network_bytepersec_tag = False
    # Display (or not) module
    diskio_tag = True
    fs_tag = True
    hddtemp_flag = True
    network_tag = True
    process_tag = True
    sensors_tag = True
    # Display property 
    use_bold = True
    percpu_tag = False
    # Default configuration file
    conf_file_tag = True
    conf_file = ""
    # Bind IP address (default is all interfaces)
    bind_ip = "0.0.0.0"
    # By default, Glances is ran in standalone mode (no client/server)
    client_tag = False
    server_tag = False
    # Server IP address (no default value) 
    server_ip = None
    # Server TCP port number (default is 61209)
    server_port = 61209
    # Default username/password for client/server mode
    username = "glances"
    password = ""
    # Output type
    output_list = ['html', 'csv']
    output_file = None
    output_folder = None


    def __init__(self):
        # Init and manage command line arguments
        self.init_arg()
        self.args = self.parse_arg()

        # !!! Why did not use the global glances_logs instance ?
        # Init the configuration file object
        if (self.conf_file_tag):
            # Init
            self.config = Config(self.conf_file)
        else:
            self.config = Config()
        # Load the configuration file
        self.config.load()

        # Catch the CTRL-C signal
        signal.signal(signal.SIGINT, self.__signal_handler)


    def __signal_handler(self, signal, frame):
        self.end()


    def end(self):
        """
        Stop the Glances core and exit
        """

        if (self.is_standalone()):
            # Stop the classical CLI loop
            screen.end()
        elif (self.is_client()):
            # Stop the client loop
            # !!! Uncomment
            #~ client.client_quit()
            pass
        elif (self.is_server()):
            # Stop the server loop
            # !!! Uncomment
            # server.server_close()
            pass

        # !!! Uncomment
        # if (self.csv_tag):
        #     csvoutput.exit()

        # !! Todo for htmloutput too
        # The exit should generate a new HTML page
        # to inform the user that data are not refreshed anymore

        # The end...
        sys.exit(0)


    def init_arg(self):
        """
        Init all the command line arguments
        """

        self.parser = argparse.ArgumentParser(
                            prog=__appname__,
                            description='Glances, an eye on your system.')

        # Version
        self.parser.add_argument('-v', '--version', 
                                 action='version', 
                                 version=_('%s v%s with PsUtil v%s') 
                                 % (__appname__.capitalize(), __version__, psutil_version))
        # Client mode: set the client IP/name
        self.parser.add_argument('-C', '--config',
                                 help=_('path to the configuration file'))

        # Refresh time
        self.parser.add_argument('-t', '--time',
                                 help=_('set refresh time in seconds (default: %s sec)') % self.refresh_time, 
                                 type=int)
        # Network bitrate in byte per second (default is bit per second)
        self.parser.add_argument('-b', '--byte',
                                 help=_('display network rate in byte per second (default is bit per second)'), 
                                 action='store_true')

        # Disable DiskIO module
        self.parser.add_argument('--disable_diskio',
                                 help=_('disable disk I/O module'), 
                                 action='store_false')
        # Disable HDD temperature module
        self.parser.add_argument('--disable_hddtemp',
                                 help=_('disable HDD temperature module'), 
                                 action='store_false')
        # Disable mount module
        self.parser.add_argument('--disable_mount',
                                 help=_('disable mount module'), 
                                 action='store_false')
        # Disable network module
        self.parser.add_argument('--disable_network',
                                 help=_('disable network module'), 
                                 action='store_false')
        # Enable sensors module
        self.parser.add_argument('--disable_sensors',
                                 help=_('disable sensors module'), 
                                 action='store_false')
        # Disable process module
        self.parser.add_argument('--disable_process',
                                 help=_('disable process module'), 
                                 action='store_false')

        # Bold attribute for Curse display (not supported by all terminal)
        self.parser.add_argument('-z', '--no_bold',
                                 help=_('disable bold mode in the terminal'), 
                                 action='store_false')
        # Per CPU display tag
        self.parser.add_argument('-1', '--percpu',
                                 help=_('start Glances in per CPU mode)'), 
                                 action='store_true')

        # Client mode: set the client IP/name
        self.parser.add_argument('-c', '--client',
                                 help=_('connect to a Glances server by IPv4/IPv6 address or hostname'))
        # Server mode
        self.parser.add_argument('-s', '--server',
                                 help=_('run Glances in server mode'),
                                 action='store_true')
        # Server bind IP/name
        self.parser.add_argument('-B', '--bind',
                                 help=_('bind server to the given IPv4/IPv6 address or hostname'))
        # Server TCP port
        self.parser.add_argument('-p', '--port',
                                 help=_('define the server TCP port (default: %d)') % self.server_port, 
                                 type=int)
        # Password as an argument
        self.parser.add_argument('-P', '--password_arg',
                                 help=_('define a client/server password'))
        # Password interactive
        self.parser.add_argument('--password',
                                 help=_('define a client/server password from the prompt'),
                                 action='store_true')

        # Output type
        self.parser.add_argument('-o', '--output',
                                 help=_('define additional output %s') % self.output_list, 
                                 choices=self.output_list)
        # Define output type flag to False (default is no output)
        for o in self.output_list:
            setattr(self, o + "_tag", False)
        # Output file/folder
        self.parser.add_argument('-f', '--file',
                                 help=_('set the html output folder or csv file'))


    def parse_arg(self):
        """
        Parse command line argument
        """

        args = self.parser.parse_args()

        # Default refresh time is 3 seconds
        if (args.time is None): args.time = 3

        # By default Help is hidden
        args.help_tag = False

        # !!! Change global variables regarding to user args
        # !!! To be refactor to use directly the args list in the code
        if (args.time is not None): self.refresh_time = args.time 
        self.network_bytepersec_tag = args.byte
        self.diskio_tag = args.disable_diskio
        self.fs_tag = args.disable_mount
        self.hddtemp_flag = args.disable_hddtemp 
        self.network_tag = args.disable_network
        self.process_tag = args.disable_process
        self.sensors_tag = args.disable_sensors and is_Linux # and sensors_lib_tag
        self.use_bold = args.no_bold
        self.percpu_tag = args.percpu
        if (args.config is not None):
            self.conf_file_tag = True
            self.conf_file = args.config
        if (args.bind is not None): self.bind_ip = args.bind 
        if (args.client is not None):
            self.client_tag = True
            self.server_ip = args.client
        self.server_tag = args.server
        if (args.port is not None): self.server_port = args.port 
        if (args.password_arg is not None): self.password = args.password_arg
        if (args.password):
            if (self.server_tag): 
                self.password = self.__get_password(
                                  description=_("Define the password for the Glances server"), 
                                  confirm=True)
            elif (self.client_tag):
                self.password = self.__get_password(
                                  description=_("Enter the Glances server password"), 
                                  confirm=False)
        if (args.output is not None):
            setattr(self, args.output+"_tag", True)
        if (args.file is not None):
            output_file = args.file
            output_folder = args.file
        # /!!!

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
        return not self.client_tag and not self.server_tag


    def is_client(self):
        """
        Return True if Glances is running in client mode
        """
        return self.client_tag and not self.server_tag


    def is_server(self):
        """
        Return True if Glances is running in sserver mode
        """
        return not self.client_tag and self.server_tag


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