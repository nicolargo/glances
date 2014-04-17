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

# Import system libs
import os
try:
    from configparser import RawConfigParser
    from configparser import NoOptionError
except ImportError:  # Python 2
    from ConfigParser import RawConfigParser
    from ConfigParser import NoOptionError

# Import Glances lib
from glances.core.glances_globals import (
    __appname__,
    is_Linux,
    is_python3,
    work_path
)


class Config(object):
    """
    This class is used to access/read config file, if it exists

    :param location: the custom path to search for config file
    :type location: str or None
    """

    def __init__(self, location=None):
        self.location = location
        self.filename = 'glances.conf'
        self.config_path = None

        self.parser = RawConfigParser()

    def load(self):
        """
        Load a config file from the list of paths, if it exists
        """
        for path in self.get_paths_list():
            if (os.path.isfile(path) and os.path.getsize(path) > 0):
                try:
                    if is_python3:
                        self.parser.read(path, encoding='utf-8')
                    else:
                        self.parser.read(path)
                    # print(_("DEBUG: Read configuration file %s") % path)
                    self.config_path = path
                except UnicodeDecodeError as e:
                    print(_("Error decoding config file '%s': %s") % (path, e))
                    sys.exit(1)
                break

    def get_config_path(self):
        """
        Return the readed configuration file path
        """
        return self.config_path

    def get_paths_list(self):
        """
        Get a list of config file paths, taking into account of the OS,
        priority and location.

        * running from source: /path/to/glances/conf
        * Linux: ~/.config/glances, /etc/glances
        * BSD: ~/.config/glances, /usr/local/etc/glances
        * Mac: ~/Library/Application Support/glances, /usr/local/etc/glances
        * Windows: %APPDATA%\glances

        The config file will be searched in the following order of priority:
            * /path/to/file (via -C flag)
            * /path/to/glances/conf
            * user's home directory (per-user settings)
            * {/usr/local,}/etc directory (system-wide settings)
        """
        paths = []
        conf_path = os.path.realpath(os.path.join(work_path, '..', '..', 'conf'))

        if self.location is not None:
            paths.append(self.location)

        if os.path.exists(conf_path):
            paths.append(os.path.join(conf_path, self.filename))

        if is_Linux or is_BSD:
            paths.append(os.path.join(
                os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'),
                __appname__, self.filename))
        elif is_Mac:
            paths.append(os.path.join(
                os.path.expanduser('~/Library/Application Support/'),
                __appname__, self.filename))
        elif is_Windows:
            paths.append(os.path.join(
                os.environ.get('APPDATA'), __appname__, self.filename))

        if is_Linux:
            paths.append(os.path.join('/etc', __appname__, self.filename))
        elif is_BSD:
            paths.append(os.path.join(
                sys.prefix, 'etc', __appname__, self.filename))
        elif is_Mac:
            paths.append(os.path.join(
                sys_prefix, 'etc', __appname__, self.filename))

        return paths

    def items(self, section):
        """
        Return the items list of a section
        """
        return self.parser.items(section)

    def has_section(self, section):
        """
        Return info about the existence of a section
        """
        return self.parser.has_section(section)

    def get_option(self, section, option):
        """
        Get the float value of an option, if it exists
        """
        try:
            value = self.parser.getfloat(section, option)
        except NoOptionError:
            return
        else:
            return value

    def get_raw_option(self, section, option):
        """
        Get the raw value of an option, if it exists
        """
        try:
            value = self.parser.get(section, option)
        except NoOptionError:
            return
        else:
            return value
