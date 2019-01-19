# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""Manage the Glances web/url list (Ports plugin)."""

from glances.compat import range, urlparse
from glances.logger import logger


class GlancesWebList(object):

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
            logger.debug("No [%s] section in the configuration file. Cannot load ports list." % self._section)
        else:
            logger.debug("Start reading the [%s] section in the configuration file" % self._section)

            refresh = int(config.get_value(self._section, 'refresh', default=self._default_refresh))
            timeout = int(config.get_value(self._section, 'timeout', default=self._default_timeout))

            # Read the web/url list
            for i in range(1, 256):
                new_web = {}
                postfix = 'web_%s_' % str(i)

                # Read mandatories configuration key: host
                new_web['url'] = config.get_value(self._section, '%s%s' % (postfix, 'url'))
                if new_web['url'] is None:
                    continue
                url_parse = urlparse(new_web['url'])
                if not bool(url_parse.scheme) or not bool(url_parse.netloc):
                    logger.error('Bad URL (%s) in the [%s] section of configuration file.' % (new_web['url'],
                                                                                              self._section))
                    continue

                # Read optionals configuration keys
                # Default description is the URL without the http://
                new_web['description'] = config.get_value(self._section,
                                                          '%sdescription' % postfix,
                                                          default="%s" % url_parse.netloc)

                # Default status
                new_web['status'] = None
                new_web['elapsed'] = 0

                # Refresh rate in second
                new_web['refresh'] = refresh

                # Timeout in second
                new_web['timeout'] = int(config.get_value(self._section,
                                                          '%stimeout' % postfix,
                                                          default=timeout))

                # RTT warning
                new_web['rtt_warning'] = config.get_value(self._section,
                                                          '%srtt_warning' % postfix,
                                                          default=None)
                if new_web['rtt_warning'] is not None:
                    # Convert to second
                    new_web['rtt_warning'] = int(new_web['rtt_warning']) / 1000.0

                # Indice
                new_web['indice'] = 'web_' + str(i)
                
                # ssl_verify
                new_web['ssl_verify'] = config.get_value(self._section, 
                                                        '%sssl_verify' % postfix,
                                                         default=True)
                # Proxy
                http_proxy = config.get_value(self._section, 
                                                '%shttp_proxy' % postfix,
                                                default=None)
                
                https_proxy = config.get_value(self._section, 
                                                '%shttps_proxy' % postfix,
                                                default=None)

                if https_proxy is None and http_proxy is None:
                    new_web['proxies'] = None
                else:
                    new_web['proxies'] = {'http' : http_proxy,
                                          'https' : https_proxy }

                # Add the server to the list
                logger.debug("Add Web URL %s to the static list" % new_web['url'])
                web_list.append(new_web)

            # Ports list loaded
            logger.debug("Web list loaded: %s" % web_list)

        return web_list

    def get_web_list(self):
        """Return the current server list (dict of dict)."""
        return self._web_list

    def set_server(self, pos, key, value):
        """Set the key to the value for the pos (position in the list)."""
        self._web_list[pos][key] = value
