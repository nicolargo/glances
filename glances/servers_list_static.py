#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances server static list."""

from socket import gaierror, gethostbyname

from glances.logger import logger


class GlancesStaticServer:
    """Manage the static servers list for the client browser."""

    _section = "serverlist"

    def __init__(self, config=None, args=None):
        # server_list is a list of dict (JSON compliant)
        # [ {'key': 'zeroconf name', ip': '172.1.2.3', 'port': 61209, 'protocol': 'rpc', 'cpu': 3, 'mem': 34 ...} ... ]
        # Load server list from the Glances configuration file
        self._server_list = self.load_server_list(config)

    def load_server_list(self, config):
        """Load the server list from the configuration file."""
        server_list = []

        if config is None:
            logger.debug("No configuration file available. Cannot load server list.")
        elif not config.has_section(self._section):
            logger.warning(f"No [{self._section}] section in the configuration file. Cannot load server list.")
        else:
            logger.info(f"Start reading the [{self._section}] section in the configuration file")
            for i in range(1, 256):
                # Read the configuration
                new_server = {}
                postfix = f'server_{str(i)}_'
                for s in ['name', 'port', 'alias', 'protocol']:
                    new_server[s] = config.get_value(self._section, f'{postfix}{s}')

                if new_server['name'] is None:
                    continue

                # Type in order to support both RPC and REST servers (see #1121)
                if new_server['protocol'] is None:
                    new_server['protocol'] = 'rpc'
                new_server['protocol'] = new_server['protocol'].lower()
                if new_server['protocol'] not in ('rpc', 'rest'):
                    logger.error(f'Unknow protocol for {postfix}, skip it.')
                    continue

                # Default port
                if new_server['port'] is None:
                    new_server['port'] = '61209' if new_server['type'] == 'rpc' else '61208'

                # By default, try empty (aka no) password
                new_server['username'] = 'glances'
                new_server['password'] = ''

                try:
                    new_server['ip'] = gethostbyname(new_server['name'])
                except gaierror as e:
                    logger.error("Cannot get IP address for server {} ({})".format(new_server['name'], e))
                    continue
                new_server['key'] = new_server['name'] + ':' + new_server['port']

                # Default status is 'UNKNOWN'
                new_server['status'] = 'UNKNOWN'

                # Server type is 'STATIC'
                new_server['type'] = 'STATIC'

                # Add the server to the list
                logger.debug("Add server {} to the static list".format(new_server['name']))
                server_list.append(new_server)

            # Server list loaded
            logger.info(f"{len(server_list)} server(s) loaded from the configuration file")
            logger.debug(f"Static server list: {server_list}")

        return server_list

    def get_servers_list(self):
        """Return the current server list (list of dict)."""
        return self._server_list

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)."""
        self._server_list[server_pos][key] = value
