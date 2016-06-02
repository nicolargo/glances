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

import os
import sys
import multiprocessing
from io import open

from glances import __appname__
from glances.compat import ConfigParser, NoOptionError
from glances.globals import BSD, LINUX, OSX, WINDOWS, sys_prefix
from glances.logger import logger


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

        if LINUX or BSD:
            paths.append(
                os.path.join(os.environ.get('XDG_CONFIG_HOME') or
                             os.path.expanduser('~/.config'),
                             __appname__, self.config_filename))
            if BSD:
                paths.append(
                    os.path.join(sys.prefix, 'etc', __appname__, self.config_filename))
            else:
                paths.append(
                    os.path.join('/etc', __appname__, self.config_filename))
        elif OSX:
            paths.append(
                os.path.join(os.path.expanduser('~/Library/Application Support/'),
                             __appname__, self.config_filename))
            paths.append(
                os.path.join(sys_prefix, 'etc', __appname__, self.config_filename))
        elif WINDOWS:
            paths.append(
                os.path.join(os.environ.get('APPDATA'), __appname__, self.config_filename))

        return paths

    def read(self):
        """Read the config file, if it exists. Using defaults otherwise."""
        for config_file in self.config_file_paths():
            if os.path.exists(config_file):
                try:
                    with open(config_file, encoding='utf-8') as f:
                        self.parser.read_file(f)
                        self.parser.read(f)
                    logger.info("Read configuration file '{}'".format(config_file))
                except UnicodeDecodeError as err:
                    logger.error("Cannot decode configuration file '{}': {}".format(config_file, err))
                    sys.exit(1)
                # Save the loaded configuration file path (issue #374)
                self._loaded_config_file = config_file
                break

        # Quicklook
        if not self.parser.has_section('quicklook'):
            self.parser.add_section('quicklook')
        self.set_default('quicklook', 'cpu_careful', '50')
        self.set_default('quicklook', 'cpu_warning', '70')
        self.set_default('quicklook', 'cpu_critical', '90')
        self.set_default('quicklook', 'mem_careful', '50')
        self.set_default('quicklook', 'mem_warning', '70')
        self.set_default('quicklook', 'mem_critical', '90')
        self.set_default('quicklook', 'swap_careful', '50')
        self.set_default('quicklook', 'swap_warning', '70')
        self.set_default('quicklook', 'swap_critical', '90')

        # CPU
        if not self.parser.has_section('cpu'):
            self.parser.add_section('cpu')
        self.set_default('cpu', 'user_careful', '50')
        self.set_default('cpu', 'user_warning', '70')
        self.set_default('cpu', 'user_critical', '90')
        self.set_default('cpu', 'system_careful', '50')
        self.set_default('cpu', 'system_warning', '70')
        self.set_default('cpu', 'system_critical', '90')
        self.set_default('cpu', 'steal_careful', '50')
        self.set_default('cpu', 'steal_warning', '70')
        self.set_default('cpu', 'steal_critical', '90')
        # By default I/O wait should be lower than 1/number of CPU cores
        iowait_bottleneck = (1.0 / multiprocessing.cpu_count()) * 100.0
        self.set_default('cpu', 'iowait_careful', str(iowait_bottleneck - (iowait_bottleneck * 0.20)))
        self.set_default('cpu', 'iowait_warning', str(iowait_bottleneck - (iowait_bottleneck * 0.10)))
        self.set_default('cpu', 'iowait_critical', str(iowait_bottleneck))
        ctx_switches_bottleneck = 56000 / multiprocessing.cpu_count()
        self.set_default('cpu', 'ctx_switches_careful', str(ctx_switches_bottleneck - (ctx_switches_bottleneck * 0.20)))
        self.set_default('cpu', 'ctx_switches_warning', str(ctx_switches_bottleneck - (ctx_switches_bottleneck * 0.10)))
        self.set_default('cpu', 'ctx_switches_critical', str(ctx_switches_bottleneck))

        # Per-CPU
        if not self.parser.has_section('percpu'):
            self.parser.add_section('percpu')
        self.set_default('percpu', 'user_careful', '50')
        self.set_default('percpu', 'user_warning', '70')
        self.set_default('percpu', 'user_critical', '90')
        self.set_default('percpu', 'system_careful', '50')
        self.set_default('percpu', 'system_warning', '70')
        self.set_default('percpu', 'system_critical', '90')

        # Load
        if not self.parser.has_section('load'):
            self.parser.add_section('load')
        self.set_default('load', 'careful', '0.7')
        self.set_default('load', 'warning', '1.0')
        self.set_default('load', 'critical', '5.0')

        # Mem
        if not self.parser.has_section('mem'):
            self.parser.add_section('mem')
        self.set_default('mem', 'careful', '50')
        self.set_default('mem', 'warning', '70')
        self.set_default('mem', 'critical', '90')

        # Swap
        if not self.parser.has_section('memswap'):
            self.parser.add_section('memswap')
        self.set_default('memswap', 'careful', '50')
        self.set_default('memswap', 'warning', '70')
        self.set_default('memswap', 'critical', '90')

        # FS
        if not self.parser.has_section('fs'):
            self.parser.add_section('fs')
        self.set_default('fs', 'careful', '50')
        self.set_default('fs', 'warning', '70')
        self.set_default('fs', 'critical', '90')

        # Sensors
        if not self.parser.has_section('sensors'):
            self.parser.add_section('sensors')
        self.set_default('sensors', 'temperature_core_careful', '60')
        self.set_default('sensors', 'temperature_core_warning', '70')
        self.set_default('sensors', 'temperature_core_critical', '80')
        self.set_default('sensors', 'temperature_hdd_careful', '45')
        self.set_default('sensors', 'temperature_hdd_warning', '52')
        self.set_default('sensors', 'temperature_hdd_critical', '60')
        self.set_default('sensors', 'battery_careful', '80')
        self.set_default('sensors', 'battery_warning', '90')
        self.set_default('sensors', 'battery_critical', '95')

        # Process list
        if not self.parser.has_section('processlist'):
            self.parser.add_section('processlist')
        self.set_default('processlist', 'cpu_careful', '50')
        self.set_default('processlist', 'cpu_warning', '70')
        self.set_default('processlist', 'cpu_critical', '90')
        self.set_default('processlist', 'mem_careful', '50')
        self.set_default('processlist', 'mem_warning', '70')
        self.set_default('processlist', 'mem_critical', '90')

    @property
    def loaded_config_file(self):
        """Return the loaded configuration file."""
        return self._loaded_config_file

    def sections(self):
        """Return a list of all sections."""
        return self.parser.sections()

    def items(self, section):
        """Return the items list of a section."""
        return self.parser.items(section)

    def has_section(self, section):
        """Return info about the existence of a section."""
        return self.parser.has_section(section)

    def set_default(self, section, option, default):
        """If the option did not exist, create a default value."""
        if not self.parser.has_option(section, option):
            self.parser.set(section, option, default)

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
