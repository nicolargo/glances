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

"""Manage the configuration file."""

# Import system libs
import os
import sys
try:
    from configparser import ConfigParser
    from configparser import NoOptionError
except ImportError:  # Python 2
    from ConfigParser import SafeConfigParser as ConfigParser
    from ConfigParser import NoOptionError

# Import Glances lib
from glances.core.glances_globals import (
    appname,
    is_bsd,
    is_linux,
    is_mac,
    is_py3,
    is_windows,
    sys_prefix
)
from glances.core.glances_logging import logger


class Config(object):

    """This class is used to access/read config file, if it exists.

    :param config_dir: the path to search for config file
    :type config_dir: str or None
    """

    def __init__(self, config_dir=None):
        self.config_dir = config_dir
        self.config_filename = 'glances.conf'
        self._loaded_config_file = None

        self.parser = ConfigParser()
        self.read()

    def config_file_paths(self):
        r"""Get a list of config file paths.

        The list is built taking into account of the OS, priority and location.

        * custom path: /path/to/glances
        * Linux: ~/.config/glances, /etc/glances
        * BSD: ~/.config/glances, /usr/local/etc/glances
        * OS X: ~/Library/Application Support/glances, /usr/local/etc/glances
        * Windows: %APPDATA%\glances

        The config file will be searched in the following order of priority:
            * /path/to/file (via -C flag)
            * user's home directory (per-user settings)
            * system-wide directory (system-wide settings)
        """
        paths = []

        if self.config_dir:
            paths.append(self.config_dir)

        if is_linux or is_bsd:
            paths.append(
                os.path.join(os.environ.get('XDG_CONFIG_HOME') or
                             os.path.expanduser('~/.config'),
                             appname, self.config_filename))
            if is_bsd:
                paths.append(
                    os.path.join(sys.prefix, 'etc', appname, self.config_filename))
            else:
                paths.append(
                    os.path.join('/etc', appname, self.config_filename))
        elif is_mac:
            paths.append(
                os.path.join(os.path.expanduser('~/Library/Application Support/'),
                             appname, self.config_filename))
            paths.append(
                os.path.join(sys_prefix, 'etc', appname, self.config_filename))
        elif is_windows:
            paths.append(
                os.path.join(os.environ.get('APPDATA'), appname, self.config_filename))

        return paths

    def read(self):
        """Read the config file, if it exists. Using defaults otherwise."""
        for config_file in self.config_file_paths():
            if os.path.exists(config_file):
                try:
                    if is_py3:
                        self.parser.read(config_file, encoding='utf-8')
                    else:
                        self.parser.read(config_file)
                    logger.info("Read configuration file '{0}'".format(config_file))
                except UnicodeDecodeError as err:
                    logger.error("Cannot decode configuration file '{0}': {1}".format(config_file, err))
                    sys.exit(1)
                # Save the loaded configuration file path (issue #374)
                self._loaded_config_file = config_file
                break

        # Quicklook
        if not self.parser.has_section('quicklook'):
            self.parser.add_section('quicklook')
            self.parser.set('quicklook', 'cpu_careful', '50')
            self.parser.set('quicklook', 'cpu_warning', '70')
            self.parser.set('quicklook', 'cpu_critical', '90')
            self.parser.set('quicklook', 'mem_careful', '50')
            self.parser.set('quicklook', 'mem_warning', '70')
            self.parser.set('quicklook', 'mem_critical', '90')
            self.parser.set('quicklook', 'swap_careful', '50')
            self.parser.set('quicklook', 'swap_warning', '70')
            self.parser.set('quicklook', 'swap_critical', '90')

        # CPU
        if not self.parser.has_section('cpu'):
            self.parser.add_section('cpu')
            self.parser.set('cpu', 'user_careful', '50')
            self.parser.set('cpu', 'user_warning', '70')
            self.parser.set('cpu', 'user_critical', '90')
            self.parser.set('cpu', 'iowait_careful', '50')
            self.parser.set('cpu', 'iowait_warning', '70')
            self.parser.set('cpu', 'iowait_critical', '90')
            self.parser.set('cpu', 'system_careful', '50')
            self.parser.set('cpu', 'system_warning', '70')
            self.parser.set('cpu', 'system_critical', '90')
            self.parser.set('cpu', 'steal_careful', '50')
            self.parser.set('cpu', 'steal_warning', '70')
            self.parser.set('cpu', 'steal_critical', '90')

        # Per-CPU
        if not self.parser.has_section('percpu'):
            self.parser.add_section('percpu')
            self.parser.set('percpu', 'user_careful', '50')
            self.parser.set('percpu', 'user_warning', '70')
            self.parser.set('percpu', 'user_critical', '90')
            self.parser.set('percpu', 'iowait_careful', '50')
            self.parser.set('percpu', 'iowait_warning', '70')
            self.parser.set('percpu', 'iowait_critical', '90')
            self.parser.set('percpu', 'system_careful', '50')
            self.parser.set('percpu', 'system_warning', '70')
            self.parser.set('percpu', 'system_critical', '90')

        # Load
        if not self.parser.has_section('load'):
            self.parser.add_section('load')
            self.parser.set('load', 'careful', '0.7')
            self.parser.set('load', 'warning', '1.0')
            self.parser.set('load', 'critical', '5.0')

        # Mem
        if not self.parser.has_section('mem'):
            self.parser.add_section('mem')
            self.parser.set('mem', 'careful', '50')
            self.parser.set('mem', 'warning', '70')
            self.parser.set('mem', 'critical', '90')

        # Swap
        if not self.parser.has_section('memswap'):
            self.parser.add_section('memswap')
            self.parser.set('memswap', 'careful', '50')
            self.parser.set('memswap', 'warning', '70')
            self.parser.set('memswap', 'critical', '90')

        # FS
        if not self.parser.has_section('fs'):
            self.parser.add_section('fs')
            self.parser.set('fs', 'careful', '50')
            self.parser.set('fs', 'warning', '70')
            self.parser.set('fs', 'critical', '90')

        # Sensors
        if not self.parser.has_section('sensors'):
            self.parser.add_section('sensors')
            self.parser.set('sensors', 'temperature_core_careful', '60')
            self.parser.set('sensors', 'temperature_core_warning', '70')
            self.parser.set('sensors', 'temperature_core_critical', '80')
            self.parser.set('sensors', 'temperature_hdd_careful', '45')
            self.parser.set('sensors', 'temperature_hdd_warning', '52')
            self.parser.set('sensors', 'temperature_hdd_critical', '60')
            self.parser.set('sensors', 'battery_careful', '80')
            self.parser.set('sensors', 'battery_warning', '90')
            self.parser.set('sensors', 'battery_critical', '95')

        # Process list
        if not self.parser.has_section('processlist'):
            self.parser.add_section('processlist')
            self.parser.set('processlist', 'cpu_careful', '50')
            self.parser.set('processlist', 'cpu_warning', '70')
            self.parser.set('processlist', 'cpu_critical', '90')
            self.parser.set('processlist', 'mem_careful', '50')
            self.parser.set('processlist', 'mem_warning', '70')
            self.parser.set('processlist', 'mem_critical', '90')

    @property
    def loaded_config_file(self):
        """Return the loaded configuration file."""
        return self._loaded_config_file

    def items(self, section):
        """Return the items list of a section."""
        return self.parser.items(section)

    def has_section(self, section):
        """Return info about the existence of a section."""
        return self.parser.has_section(section)

    def get_value(self, section, option, default=None):
        """Get the value of an option, if it exists."""
        try:
            return self.parser.get(section, option)
        except NoOptionError:
            return default

    def get_float_value(self, section, option, default=0.0):
        """Get the float value of an option, if it exists."""
        try:
            return self.parser.getfloat(section, option)
        except NoOptionError:
            return float(default)
