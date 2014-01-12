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
import psutil

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


# !!! To be deleted after 2.0 implementation
def printSyntax():
    printVersion()
    print(_("Usage: glances [options]"))
    print(_("\nOptions:"))
    print(_("\t-b\t\tDisplay network rate in Byte per second"))
    print(_("\t-B @IP|HOST\tBind server to the given IPv4/IPv6 address or hostname"))
    print(_("\t-c @IP|HOST\tConnect to a Glances server by IPv4/IPv6 address or hostname"))
    print(_("\t-C FILE\t\tPath to the configuration file"))
    print(_("\t-d\t\tDisable disk I/O module"))
    print(_("\t-e\t\tEnable sensors module"))
    print(_("\t-f FILE\t\tSet the HTML output folder or CSV file"))
    print(_("\t-h\t\tDisplay the help and exit"))
    print(_("\t-m\t\tDisable mount module"))
    print(_("\t-n\t\tDisable network module"))
    print(_("\t-o OUTPUT\tDefine additional output (available: HTML or CSV)"))
    print(_("\t-p PORT\t\tDefine the client/server TCP port (default: %d)" %
            server_port))
    print(_("\t-P PASSWORD\tDefine a client/server password"))
    print(_("\t--password\tDefine a client/server password from the prompt"))
    print(_("\t-r\t\tDisable process list"))
    print(_("\t-s\t\tRun Glances in server mode"))
    print(_("\t-t SECONDS\tSet refresh time in seconds (default: %d sec)" %
            refresh_time))
    print(_("\t-v\t\tDisplay the version and exit"))
    print(_("\t-y\t\tEnable hddtemp module"))
    print(_("\t-z\t\tDo not use the bold color attribute"))
    print(_("\t-1\t\tStart Glances in per CPU mode"))


class GlancesCore(object):
    """
    Main class to manage Glances instance
    """

    # Default stats' refresh time is 3 seconds
    refresh_time = 3

    def __init__(self):
        self.parser = argparse.ArgumentParser(
                            prog=__appname__,
                            description='Glances, an eye on your system.')
        self.init_arg()

    def init_arg(self):
        """
        Init all the command line argument
        """

        # Version
        # !!! Add Ps Util version
        self.parser.add_argument('-v', '--version', 
                                 action='version', 
                                 version='%s v%s' % (__appname__, __version__))
        # Refresh time
        self.parser.add_argument('-t', '--time',
                                 help='set refresh time in seconds (default: %s sec)' % self.refresh_time, 
                                 type=int)

    def parse_arg(self):
        """
        Parse command line argument
        """

        args = self.parser.parse_args()
        if (args.time is not None):
            self.refresh_time = args.time 

        # !!! Debug
        print "refresh_time: %s" % self.refresh_time

    def start(self):
        """
        Start the instance
        It is the 'real' main function for Glances
        """

        self.parse_arg()
