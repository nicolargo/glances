#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances ports list (Ports plugin)."""

from glances.globals import BSD
from glances.logger import logger

# XXX *BSDs: Segmentation fault (core dumped)
# -- https://bitbucket.org/al45tair/netifaces/issues/15
# Also used in the glances_ip plugin
if not BSD:
    try:
        import netifaces

        netifaces_tag = True
    except ImportError:
        netifaces_tag = False
else:
    netifaces_tag = False


class GlancesPortsList:
    """Manage the ports list for the ports plugin."""

    _section = "ports"
    _default_refresh = 60
    _default_timeout = 3

    def __init__(self, config=None, args=None):
        # ports_list is a list of dict (JSON compliant)
        # [ {'host': 'www.google.fr', 'port': 443, 'refresh': 30, 'description': Internet, 'status': True} ... ]
        # Load the configuration file
        self._ports_list = self.load(config)

    def load(self, config):
        """Load the ports list from the configuration file."""
        ports_list = []

        if config is None:
            logger.debug("No configuration file available. Cannot load ports list.")
        elif not config.has_section(self._section):
            logger.debug(f"No [{self._section}] section in the configuration file. Cannot load ports list.")
        else:
            logger.debug(f"Start reading the [{self._section}] section in the configuration file")

            refresh = int(config.get_value(self._section, 'refresh', default=self._default_refresh))
            timeout = int(config.get_value(self._section, 'timeout', default=self._default_timeout))

            # Add default gateway on top of the ports_list lists
            default_gateway = config.get_value(self._section, 'port_default_gateway', default='False')
            if default_gateway.lower().startswith('true') and netifaces_tag:
                new_port = {}
                try:
                    new_port['host'] = netifaces.gateways()['default'][netifaces.AF_INET][0]
                except KeyError:
                    new_port['host'] = None
                # ICMP
                new_port['port'] = 0
                new_port['description'] = 'DefaultGateway'
                new_port['refresh'] = refresh
                new_port['timeout'] = timeout
                new_port['status'] = None
                new_port['rtt_warning'] = None
                new_port['indice'] = 'port_0'
                logger.debug("Add default gateway {} to the static list".format(new_port['host']))
                ports_list.append(new_port)

            # Read the scan list
            for i in range(1, 256):
                new_port = {}
                postfix = f'port_{str(i)}_'

                # Read mandatory configuration key: host
                new_port['host'] = config.get_value(self._section, '{}{}'.format(postfix, 'host'))

                if new_port['host'] is None:
                    continue

                # Read optionals configuration keys
                # Port is set to 0 by default. 0 mean ICMP check instead of TCP check
                new_port['port'] = config.get_value(self._section, '{}{}'.format(postfix, 'port'), 0)
                new_port['description'] = config.get_value(
                    self._section, f'{postfix}description', default="{}:{}".format(new_port['host'], new_port['port'])
                )

                # Default status
                new_port['status'] = None

                # Refresh rate in second
                new_port['refresh'] = refresh

                # Timeout in second
                new_port['timeout'] = int(config.get_value(self._section, f'{postfix}timeout', default=timeout))

                # RTT warning
                new_port['rtt_warning'] = config.get_value(self._section, f'{postfix}rtt_warning', default=None)
                if new_port['rtt_warning'] is not None:
                    # Convert to second
                    new_port['rtt_warning'] = int(new_port['rtt_warning']) / 1000.0

                # Indice
                new_port['indice'] = 'port_' + str(i)

                # Add the server to the list
                logger.debug("Add port {}:{} to the static list".format(new_port['host'], new_port['port']))
                ports_list.append(new_port)

            # Ports list loaded
            logger.debug(f"Ports list loaded: {ports_list}")

        return ports_list

    def get_ports_list(self):
        """Return the current server list (dict of dict)."""
        return self._ports_list

    def set_server(self, pos, key, value):
        """Set the key to the value for the pos (position in the list)."""
        self._ports_list[pos][key] = value
