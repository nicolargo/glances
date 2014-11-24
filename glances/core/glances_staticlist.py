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

"""Manage the Glances server static list """

# Import Glances libs
from glances.core.glances_globals import logger


class GlancesStaticServer(object):

    """Manage the static servers list for the client browser"""

    _section = "serverlist"

    def __init__(self, config=None, args=None):
        # server_dict is a list of dict (JSON compliant)
        # [ {'key': 'zeroconf name', ip': '172.1.2.3', 'port': 61209, 'cpu': 3, 'mem': 34 ...} ... ]
        # Load the configuration file
        self._server_list = self.load(config)

    def load(self, config):
        """Load the server list from the configuration file"""

        server_list = []

        if config is None:
            logger.warning("No configuration file available. Can not load server list.")
        elif not config.has_section(self._section):
            logger.warning("No [%s] section in the configuration file. Can not load server list." % self._section)
        else:
            for i in range(1, 256):
                new_server = {}
                postfix = 'server_%s_' % str(i)
                # Read the server name (mandatory)
                new_server['name'] = config.get_raw_option(self._section, '%sname' % postfix)
                if new_server['name'] is not None:
                    # Read other optionnal information
                    for s in ['alias', 'port', 'password']:
                        new_server[s] = config.get_raw_option(self._section, '%s%s' % (postfix, s))

                    # Manage optionnal information
                    if new_server['alias'] is None:
                        new_server['alias'] = new_server['name']
                    if new_server['port'] is None:
                        new_server['port'] = 61209
                    if new_server['password'] is None:
                        new_server['password'] = ''
                    new_server['username'] = 'glances'
                    new_server['ip'] = new_server['name']
                    new_server['key'] = new_server['name'] + ':' + new_server['port']
                    new_server['status'] = 'UNKNOWN'

                    # Add the server to the list
                    logger.debug("Add server %s to the static list" % new_server['name'])
                    server_list.append(new_server)

            # Server list loaded
            logger.info("%s server(s) loaded from the configuration file" % len(server_list))
            logger.debug("Static server list: %s" % server_list)

        return server_list

    def get_servers_list(self):
        """Return the current server list (dict of dict)"""
        return self._server_list

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)"""
        self._server_list[server_pos][key] = value
