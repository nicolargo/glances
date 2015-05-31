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

"""Manage the Glances passwords list."""

# Import Glances libs
from glances.core.glances_logging import logger


class GlancesPassword(object):

    """Manage the Glances passwords list for the client|browser/server."""

    _section = "passwords"

    def __init__(self, config=None, args=None):
        # password_dict is a dict (JSON compliant)
        # {'host': 'password', ... }
        # Load the configuration file
        self._password_dict = self.load(config)

    def load(self, config):
        """Load the password from the configuration file."""
        password_dict = []

        if config is None:
            logger.warning("No configuration file available. Cannot load password list.")
        elif not config.has_section(self._section):
            logger.warning("No [%s] section in the configuration file. Cannot load password list." % self._section)
        else:
            logger.info("Start reading the [%s] section in the configuration file" % self._section)

            password_dict = dict(config.items(self._section))

            # Password list loaded
            logger.info("%s password(s) loaded from the configuration file" % len(password_dict))
            logger.debug("Password dictionary: %s" % password_dict)

        return password_dict

    def get_password(self, host=None):
        """
        If host=None, return the current server list (dict).
        Else, return the host's password (or the default one if defined or None)
        """
        if host is None:
            return self._password_dict
        else:
            try:
                return self._password_dict[host]
            except (KeyError, TypeError):
                try:
                    return self._password_dict['default']
                except (KeyError, TypeError):
                    return None
                return None

    def set_password(self, host, password):
        """Set a password for a specific host."""
        self._password_dict[host] = password
