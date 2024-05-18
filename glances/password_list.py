#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances passwords list."""

from glances.logger import logger
from glances.password import GlancesPassword


class GlancesPasswordList(GlancesPassword):
    """Manage the Glances passwords list for the client|browser/server."""

    _section = "passwords"

    def __init__(self, config=None, args=None):
        super().__init__()
        # password_dict is a dict (JSON compliant)
        # {'host': 'password', ... }
        # Load the configuration file
        self._password_dict = self.load(config)

    def load(self, config):
        """Load the password from the configuration file."""
        password_dict = {}

        if config is None:
            logger.warning("No configuration file available. Cannot load password list.")
        elif not config.has_section(self._section):
            logger.warning(f"No [{self._section}] section in the configuration file. Cannot load password list.")
        else:
            logger.info(f"Start reading the [{self._section}] section in the configuration file")

            password_dict = dict(config.items(self._section))

            # Password list loaded
            logger.info(f"{len(password_dict)} password(s) loaded from the configuration file")

        return password_dict

    def get_password(self, host=None):
        """Get the password from a Glances client or server.

        If host=None, return the current server list (dict).
        Else, return the host's password (or the default one if defined or None)
        """
        if host is None:
            return self._password_dict

        try:
            return self._password_dict[host]
        except (KeyError, TypeError):
            try:
                return self._password_dict['default']
            except (KeyError, TypeError):
                return None

    def set_password(self, host, password):
        """Set a password for a specific host."""
        self._password_dict[host] = password
