#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the configuration file."""

import builtins
import multiprocessing
import os
import re
import sys

from glances.globals import BSD, LINUX, MACOS, SUNOS, WINDOWS, ConfigParser, NoOptionError, NoSectionError, system_exec
from glances.logger import logger


def user_config_dir():
    r"""Return a list of per-user config dir (full path).

    - Linux, *BSD, SunOS: ~/.config/glances
    - macOS: ~/Library/Application Support/glances
    - Windows: %APPDATA%\glances
    """
    paths = []
    if WINDOWS:
        paths.append(os.environ.get('APPDATA'))
    elif MACOS:
        paths.append(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'))
        paths.append(os.path.expanduser('~/Library/Application Support'))
    else:
        paths.append(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'))

    return [os.path.join(path, 'glances') if path is not None else '' for path in paths]


def user_cache_dir():
    r"""Return a list of per-user cache dir (full path).

    - Linux, *BSD, SunOS: ~/.cache/glances
    - macOS: ~/Library/Caches/glances
    - Windows: {%LOCALAPPDATA%,%APPDATA%}\glances\cache
    """
    if WINDOWS:
        path = os.path.join(os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA'), 'glances', 'cache')
    elif MACOS:
        path = os.path.expanduser('~/Library/Caches/glances')
    else:
        path = os.path.join(os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache'), 'glances')

    return [path]


def system_config_dir():
    r"""Return a list of system-wide config dir (full path).

    - Linux, SunOS: /etc/glances
    - *BSD, macOS: /usr/local/etc/glances
    - Windows: %APPDATA%\glances
    """
    if LINUX or SUNOS:
        path = '/etc'
    elif BSD or MACOS:
        path = '/usr/local/etc'
    else:
        path = os.environ.get('APPDATA')
    if path is None:
        path = ''
    else:
        path = os.path.join(path, 'glances')

    return [path]


def default_config_dir():
    r"""Return a list of system-wide config dir (full path).

    - Linux, SunOS, *BSD, macOS: /usr/share/doc (as defined in the setup.py files)
    - Windows: %APPDATA%\glances
    """
    path = []
    # Add venv path (solve issue #2803)
    if in_virtualenv():
        path.append(os.path.join(sys.prefix, 'share', 'doc', 'glances'))

    # Add others system path
    if LINUX or SUNOS or BSD or MACOS:
        path.append('/usr/share/doc')
    else:
        path.append(os.environ.get('APPDATA'))

    return path


def in_virtualenv():
    # Source: https://stackoverflow.com/questions/1871549/how-to-determine-if-python-is-running-inside-a-virtualenv/1883251#1883251
    return sys.prefix != get_base_prefix_compat()


def get_base_prefix_compat():
    """Get base/real prefix, or sys.prefix if there is none."""
    # Source: https://stackoverflow.com/questions/1871549/how-to-determine-if-python-is-running-inside-a-virtualenv/1883251#1883251
    return getattr(sys, "base_prefix", None) or getattr(sys, "real_prefix", None) or sys.prefix


class Config:
    """This class is used to access/read config file, if it exists.

    :param config_dir: the path to search for config file
    :type config_dir: str or None
    """

    def __init__(self, config_dir=None):
        self.config_dir = config_dir
        self.config_filename = 'glances.conf'
        self._loaded_config_file = None
        self._config_file_paths = self.config_file_paths()

        # Re pattern for optimize research of `foo`
        self.re_pattern = re.compile(r'(\`.+?\`)')

        try:
            self.parser = ConfigParser(interpolation=None)
        except TypeError:
            self.parser = ConfigParser()

        self.read()

    def config_file_paths(self):
        r"""Get a list of config file paths.

        The list is built taking into account of the OS, priority and location.

        * custom path: /path/to/glances
        * Linux, SunOS: ~/.config/glances, /etc/glances
        * *BSD: ~/.config/glances, /usr/local/etc/glances
        * macOS: ~/.config/glances, ~/Library/Application Support/glances, /usr/local/etc/glances
        * Windows: %APPDATA%\glances

        The config file will be searched in the following order of priority:
            * /path/to/file (via -C flag)
            * user's home directory (per-user settings)
            * system-wide directory (system-wide settings)
            * default pip directory (as defined in the setup.py file)
        """
        paths = []

        # self.config_dir is the path to the config file (via -C flag)
        if self.config_dir:
            paths.append(self.config_dir)

        # user_config_dir() returns a list of paths
        paths.extend([os.path.join(path, self.config_filename) for path in user_config_dir()])

        # system_config_dir() returns a list of paths
        paths.extend([os.path.join(path, self.config_filename) for path in system_config_dir()])

        # default_config_dir() returns a list of paths
        paths.extend([os.path.join(path, self.config_filename) for path in default_config_dir()])

        return paths

    def read(self):
        """Read the config file, if it exists. Using defaults otherwise."""
        for config_file in self._config_file_paths:
            logger.debug(f'Search glances.conf file in {config_file}')
            if os.path.exists(config_file):
                try:
                    with builtins.open(config_file, encoding='utf-8') as f:
                        self.parser.read_file(f)
                        self.parser.read(f)
                    logger.info(f"Read configuration file '{config_file}'")
                except UnicodeDecodeError as err:
                    logger.error(f"Can not read configuration file '{config_file}': {err}")
                    sys.exit(1)
                # Save the loaded configuration file path (issue #374)
                self._loaded_config_file = config_file
                break

        # Set the default values for section not configured
        self.sections_set_default()

    def sections_set_default(self):
        # Globals
        if not self.parser.has_section('global'):
            self.parser.add_section('global')
        self.set_default('global', 'strftime_format', '')
        self.set_default('global', 'check_update', 'true')

        # Quicklook
        if not self.parser.has_section('quicklook'):
            self.parser.add_section('quicklook')
        self.set_default_cwc('quicklook', 'cpu')
        self.set_default_cwc('quicklook', 'mem')
        self.set_default_cwc('quicklook', 'swap')

        # CPU
        if not self.parser.has_section('cpu'):
            self.parser.add_section('cpu')
        self.set_default_cwc('cpu', 'user')
        self.set_default_cwc('cpu', 'system')
        self.set_default_cwc('cpu', 'steal')
        # By default I/O wait should be lower than 1/number of CPU cores
        iowait_bottleneck = (1.0 / multiprocessing.cpu_count()) * 100.0
        self.set_default_cwc(
            'cpu',
            'iowait',
            [
                str(iowait_bottleneck - (iowait_bottleneck * 0.20)),
                str(iowait_bottleneck - (iowait_bottleneck * 0.10)),
                str(iowait_bottleneck),
            ],
        )
        # Context switches bottleneck identification #1212
        ctx_switches_bottleneck = (500000 * 0.10) * multiprocessing.cpu_count()
        self.set_default_cwc(
            'cpu',
            'ctx_switches',
            [
                str(ctx_switches_bottleneck - (ctx_switches_bottleneck * 0.20)),
                str(ctx_switches_bottleneck - (ctx_switches_bottleneck * 0.10)),
                str(ctx_switches_bottleneck),
            ],
        )

        # Per-CPU
        if not self.parser.has_section('percpu'):
            self.parser.add_section('percpu')
        self.set_default_cwc('percpu', 'user')
        self.set_default_cwc('percpu', 'system')

        # Load
        if not self.parser.has_section('load'):
            self.parser.add_section('load')
        self.set_default_cwc('load', cwc=['0.7', '1.0', '5.0'])

        # Mem
        if not self.parser.has_section('mem'):
            self.parser.add_section('mem')
        self.set_default_cwc('mem')

        # Swap
        if not self.parser.has_section('memswap'):
            self.parser.add_section('memswap')
        self.set_default_cwc('memswap')

        # NETWORK
        if not self.parser.has_section('network'):
            self.parser.add_section('network')
        self.set_default_cwc('network', 'rx')
        self.set_default_cwc('network', 'tx')

        # FS
        if not self.parser.has_section('fs'):
            self.parser.add_section('fs')
        self.set_default_cwc('fs')

        # Sensors
        if not self.parser.has_section('sensors'):
            self.parser.add_section('sensors')
        self.set_default_cwc('sensors', 'temperature_hdd', cwc=['45', '52', '60'])
        self.set_default_cwc('sensors', 'battery', cwc=['70', '80', '90'])

        # Process list
        if not self.parser.has_section('processlist'):
            self.parser.add_section('processlist')
        self.set_default_cwc('processlist', 'cpu')
        self.set_default_cwc('processlist', 'mem')

    @property
    def loaded_config_file(self):
        """Return the loaded configuration file."""
        return self._loaded_config_file

    def as_dict(self):
        """Return the configuration as a dict"""
        dictionary = {}
        for section in self.parser.sections():
            dictionary[section] = {}
            for option in self.parser.options(section):
                dictionary[section][option] = self.parser.get(section, option)
        return dictionary

    def sections(self):
        """Return a list of all sections."""
        return self.parser.sections()

    def items(self, section):
        """Return the items list of a section."""
        return self.parser.items(section)

    def has_section(self, section):
        """Return info about the existence of a section."""
        return self.parser.has_section(section)

    def set_default_cwc(self, section, option_header=None, cwc=['50', '70', '90']):
        """Set default values for careful, warning and critical."""
        if option_header is None:
            header = ''
        else:
            header = option_header + '_'
        self.set_default(section, header + 'careful', cwc[0])
        self.set_default(section, header + 'warning', cwc[1])
        self.set_default(section, header + 'critical', cwc[2])

    def set_default(self, section, option, default):
        """If the option did not exist, create a default value."""
        if not self.parser.has_option(section, option):
            self.parser.set(section, option, default)

    def get_value(self, section, option, default=None):
        """Get the value of an option, if it exists.

        If it did not exist, then return the default value.

        It allows user to define dynamic configuration key (see issue#1204)
        Dynamic value should starts and end with the ` char
        Example: prefix=`hostname`
        """
        ret = default
        try:
            ret = self.parser.get(section, option)
        except (NoOptionError, NoSectionError):
            pass

        # Search a substring `foo` and replace it by the result of its exec
        if ret is not None:
            try:
                match = self.re_pattern.findall(ret)
                for m in match:
                    ret = ret.replace(m, system_exec(m[1:-1]))
            except TypeError:
                pass
        return ret

    def get_list_value(self, section, option, default=None, separator=','):
        """Get the list value of an option, if it exists."""
        try:
            return self.parser.get(section, option).split(separator)
        except (NoOptionError, NoSectionError):
            return default

    def get_int_value(self, section, option, default=0):
        """Get the int value of an option, if it exists."""
        try:
            return self.parser.getint(section, option)
        except (NoOptionError, NoSectionError):
            return int(default)

    def get_float_value(self, section, option, default=0.0):
        """Get the float value of an option, if it exists."""
        try:
            return self.parser.getfloat(section, option)
        except (NoOptionError, NoSectionError):
            return float(default)

    def get_bool_value(self, section, option, default=True):
        """Get the bool value of an option, if it exists."""
        try:
            return self.parser.getboolean(section, option)
        except (NoOptionError, NoSectionError):
            return bool(default)
