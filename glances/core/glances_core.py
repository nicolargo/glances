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

__appname__ = 'glances'
__version__ = "2.0_Alpha"
__author__ = "Nicolas Hennion <nicolas@nicolargo.com>"
__license__ = "LGPL"

import sys
import os
import gettext
import locale
import argparse

# path definitions
work_path = os.path.realpath(os.path.dirname(__file__))
appname_path = os.path.split(sys.argv[0])[0]
sys_prefix = os.path.realpath(os.path.dirname(appname_path))

# i18n
locale.setlocale(locale.LC_ALL, '')
gettext_domain = __appname__
# get locale directory
i18n_path = os.path.realpath(os.path.join(work_path, '..', 'i18n'))
sys_i18n_path = os.path.join(sys_prefix, 'share', 'locale')
if os.path.exists(i18n_path):
    locale_dir = i18n_path
elif os.path.exists(sys_i18n_path):
    locale_dir = sys_i18n_path
else:
    locale_dir = None
gettext.install(gettext_domain, locale_dir)

# Operating system flag
# Note: Somes libs depends of OS
is_BSD = sys.platform.find('bsd') != -1
is_Linux = sys.platform.startswith('linux')
is_Mac = sys.platform.startswith('darwin')
is_Windows = sys.platform.startswith('win')

# Import PSUtil
# !!! Is it mandatory for client ?
try:
    # psutil is the main library used to grab stats
    import psutil
except ImportError:
    print('PsUtil module not found. Glances cannot start.')
    sys.exit(1)

# PSutil version
psutil_version = tuple([int(num) for num in psutil.__version__.split('.')])
# Note: this is not a mistake: psutil 0.5.1 is detected as 0.5.0
if psutil_version < (0, 5, 0):
    print('PsUtil version %s detected.' % psutil.__version__)
    print('PsUtil 0.5.1 or higher is needed. Glances cannot start.')
    sys.exit(1)

try:
    # psutil.virtual_memory() only available from psutil >= 0.6
    psutil.virtual_memory()
except Exception:
    psutil_mem_vm = False
else:
    psutil_mem_vm = True

try:
    # psutil.net_io_counters() only available from psutil >= 1.0.0
    psutil.net_io_counters()
except Exception:
    psutil_net_io_counters = False
else:
    psutil_net_io_counters = True

if not is_Mac:
    psutil_get_io_counter_tag = True
else:
    # get_io_counters() not available on OS X
    psutil_get_io_counter_tag = False

# sensors library (optional; Linux-only)
if is_Linux:
    try:
        import sensors
    except ImportError:
        sensors_lib_tag = False
    else:
        sensors_lib_tag = True
else:
    sensors_lib_tag = False

# batinfo library (optional; Linux-only)
if is_Linux:
    try:
        import batinfo
    except ImportError:
        batinfo_lib_tag = False
    else:
        batinfo_lib_tag = True
else:
    batinfo_lib_tag = False


class GlancesCore(object):
    """
    Main class to manage Glances instance
    """

    # Default stats' refresh time is 3 seconds
    refresh_time = 3
    # Set the default cache lifetime to 1 second (only for server)
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
        self.parser = argparse.ArgumentParser(
                            prog=__appname__,
                            description='Glances, an eye on your system.')
        self.init_arg()

    def init_arg(self):
        """
        Init all the command line arguments
        """

        # Version
        self.parser.add_argument('-v', '--version', 
                                 action='version', 
                                 version=_('%s v%s with PsUtil v%s') 
                                 % (__appname__, __version__, psutil.__version__))
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
                                 help=_('disable process module'), 
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
            setattr(self, o+"_tag", False)
        # Output file/folder
        self.parser.add_argument('-f', '--file',
                                 help=_('set the html output folder or csv file'))


    def parse_arg(self):
        """
        Parse command line argument
        """

        args = self.parser.parse_args()

        # Change global variables regarding to user args
        if (args.time is not None): self.refresh_time = args.time 
        self.network_bytepersec_tag = args.byte
        self.diskio_tag = args.disable_diskio
        self.fs_tag = args.disable_mount
        self.hddtemp_flag = args.disable_hddtemp 
        self.network_tag = args.disable_network
        self.process_tag = args.disable_process
        self.sensors_tag = args.disable_sensors and is_Linux and sensors_lib_tag
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
                self.password = self.get_password(
                                  description=_("Define the password for the Glances server"), 
                                  confirm=True)
            elif (self.client_tag):
                self.password = self.get_password(
                                  description=_("Enter the Glances server password"), 
                                  confirm=False)
        if (args.output is not None):
            setattr(self, args.output+"_tag", True)
        if (args.file is not None):
            output_file = args.file
            output_folder = args.file

        # !!! Debug
        print args
        # print "self.sensors_tag=%s" % self.sensors_tag
        # print "self.html_tag=%s" % self.html_tag
        # print "self.csv_tag=%s" % self.csv_tag

    def get_password(self, description='', confirm=False):
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
            return self.get_password(description=description, confirm=confirm)

    def start(self):
        """
        Start the instance
        It is the 'real' main function for Glances
        """

        self.parse_arg()
