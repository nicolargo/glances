#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances web/url list (Ports plugin)."""

from glances.globals import urlparse
from glances.logger import logger


class GlancesWebList:
    """Manage the Web/Url list for the ports plugin."""

    _section = "ports"
    _default_refresh = 60
    _default_timeout = 3

    def __init__(self, config=None, args=None):
        # web_list is a list of dict (JSON compliant)
        # [ {'url': 'http://blog.nicolargo.com',
        #    'refresh': 30,
        #    'description': 'My blog',
        #    'status': 404} ... ]
        # Load the configuration file
        self._web_list = self.load(config)

    def load(self, config):
        """Load the web list from the configuration file."""
        web_list = []

        if config is None:
            logger.debug("No configuration file available. Cannot load ports list.")
        elif not config.has_section(self._section):
            logger.debug(f"No [{self._section}] section in the configuration file. Cannot load ports list.")
        else:
            logger.debug(f"Start reading the [{self._section}] section in the configuration file")

            refresh = int(config.get_value(self._section, 'refresh', default=self._default_refresh))
            timeout = int(config.get_value(self._section, 'timeout', default=self._default_timeout))

            # Read the web/url list
            for i in range(1, 256):
                new_web = {}
                postfix = f'web_{str(i)}_'

                # Read mandatory configuration key: host
                new_web['url'] = config.get_value(self._section, '{}{}'.format(postfix, 'url'))
                if new_web['url'] is None:
                    continue
                url_parse = urlparse(new_web['url'])
                if not bool(url_parse.scheme) or not bool(url_parse.netloc):
                    logger.error(
                        'Bad URL ({}) in the [{}] section of configuration file.'.format(new_web['url'], self._section)
                    )
                    continue

                # Read optionals configuration keys
                # Default description is the URL without the http://
                new_web['description'] = config.get_value(
                    self._section, f'{postfix}description', default=f"{url_parse.netloc}"
                )

                # Default status
                new_web['status'] = None
                new_web['elapsed'] = 0

                # Refresh rate in second
                new_web['refresh'] = refresh

                # Timeout in second
                new_web['timeout'] = int(config.get_value(self._section, f'{postfix}timeout', default=timeout))

                # RTT warning
                new_web['rtt_warning'] = config.get_value(self._section, f'{postfix}rtt_warning', default=None)
                if new_web['rtt_warning'] is not None:
                    # Convert to second
                    new_web['rtt_warning'] = int(new_web['rtt_warning']) / 1000.0

                # Indice
                new_web['indice'] = 'web_' + str(i)

                # ssl_verify
                new_web['ssl_verify'] = config.get_value(self._section, f'{postfix}ssl_verify', default=True)
                # Proxy
                http_proxy = config.get_value(self._section, f'{postfix}http_proxy', default=None)

                https_proxy = config.get_value(self._section, f'{postfix}https_proxy', default=None)

                if https_proxy is None and http_proxy is None:
                    new_web['proxies'] = None
                else:
                    new_web['proxies'] = {'http': http_proxy, 'https': https_proxy}

                # Add the server to the list
                logger.debug("Add Web URL {} to the static list".format(new_web['url']))
                web_list.append(new_web)

            # Ports list loaded
            logger.debug(f"Web list loaded: {web_list}")

        return web_list

    def get_web_list(self):
        """Return the current server list (dict of dict)."""
        return self._web_list

    def set_server(self, pos, key, value):
        """Set the key to the value for the pos (position in the list)."""
        self._web_list[pos][key] = value
