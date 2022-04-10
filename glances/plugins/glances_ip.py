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

"""IP plugin."""

import threading
from json import loads

from glances.compat import iterkeys, urlopen, queue
from glances.logger import logger
from glances.timer import Timer, getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin

# Import plugin specific dependency
try:
    import netifaces
except ImportError as e:
    import_error_tag = True
    logger.warning("Missing Python Lib ({}), IP plugin is disabled".format(e))
else:
    import_error_tag = False

# List of online services to retrieve public IP address
# List of tuple (url, json, key)
# - url: URL of the Web site
# - json: service return a JSON (True) or string (False)
# - key: key of the IP address in the JSON structure
urls = [
    #  glances_ip.py plugin relies on low rating / malicious site domain #1975
    # ('https://ip.42.pl/raw', False, None),
    ('https://httpbin.org/ip', True, 'origin'),
    ('https://api.ipify.org/?format=json', True, 'ip'),
    ('https://ipv4.jsonip.com', True, 'ip'),
]


class Plugin(GlancesPlugin):
    """Glances IP Plugin.

    stats is a dict
    """

    _default_public_refresh_interval = 300
    _default_public_ip_disabled = ["False"]

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # For public IP address
        self.public_address = ""
        self.public_address_refresh_interval = self.get_conf_value(
            "public_refresh_interval", default=self._default_public_refresh_interval
        )

        public_ip_disabled = self.get_conf_value("public_ip_disabled", default=self._default_public_ip_disabled)
        self.public_ip_disabled = True if public_ip_disabled == ["True"] else False

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update IP stats using the input method.

        :return: the stats dict
        """
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local' and not import_error_tag:
            # Update stats using the netifaces lib
            try:
                default_gw = netifaces.gateways()['default'][netifaces.AF_INET]
            except (KeyError, AttributeError) as e:
                logger.debug("Cannot grab the default gateway ({})".format(e))
                return {}

            try:
                address = netifaces.ifaddresses(default_gw[1])[netifaces.AF_INET][0]['addr']
                mask = netifaces.ifaddresses(default_gw[1])[netifaces.AF_INET][0]['netmask']

                time_since_update = getTimeSinceLastUpdate('public-ip')
                if not self.public_ip_disabled and (
                    self.stats.get('address') != address or time_since_update > self.public_address_refresh_interval
                ):
                    self.public_address = PublicIpAddress().get()
            except (KeyError, AttributeError) as e:
                logger.debug("Cannot grab IP information: {}".format(e))
            else:
                stats['address'] = address
                stats['mask'] = mask
                stats['mask_cidr'] = self.ip_to_cidr(stats['mask'])
                stats['gateway'] = default_gw[0]
                stats['public_address'] = self.public_address

        elif self.input_method == 'snmp':
            # Not implemented yet
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics information
        # Optional
        for key in iterkeys(self.stats):
            self.views[key]['optional'] = True

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled() or import_error_tag:
            return ret

        # Build the string message
        msg = ' - '
        ret.append(self.curse_add_line(msg))
        msg = 'IP '
        ret.append(self.curse_add_line(msg, 'TITLE'))
        if 'address' in self.stats:
            msg = '{}'.format(self.stats['address'])
            ret.append(self.curse_add_line(msg))
        if 'mask_cidr' in self.stats:
            # VPN with no internet access (issue #842)
            msg = '/{}'.format(self.stats['mask_cidr'])
            ret.append(self.curse_add_line(msg))
        try:
            msg_pub = '{}'.format(self.stats['public_address'])
        except (UnicodeEncodeError, KeyError):
            # Add KeyError exception (see https://github.com/nicolargo/glances/issues/1469)
            pass
        else:
            if self.stats['public_address']:
                msg = ' Pub '
                ret.append(self.curse_add_line(msg, 'TITLE'))
                ret.append(self.curse_add_line(msg_pub))

        return ret

    @staticmethod
    def ip_to_cidr(ip):
        """Convert IP address to CIDR.

        Example: '255.255.255.0' will return 24
        """
        # Thanks to @Atticfire
        # See https://github.com/nicolargo/glances/issues/1417#issuecomment-469894399
        if ip is None:
            # Correct issue #1528
            return 0
        return sum(bin(int(x)).count('1') for x in ip.split('.'))


class PublicIpAddress(object):
    """Get public IP address from online services."""

    def __init__(self, timeout=2):
        """Init the class."""
        self.timeout = timeout

    def get(self):
        """Get the first public IP address returned by one of the online services."""
        q = queue.Queue()

        for u, j, k in urls:
            t = threading.Thread(target=self._get_ip_public, args=(q, u, j, k))
            t.daemon = True
            t.start()

        timer = Timer(self.timeout)
        ip = None
        while not timer.finished() and ip is None:
            if q.qsize() > 0:
                ip = q.get()

        if ip is None:
            return None

        return ', '.join(set([x.strip() for x in ip.split(',')]))

    def _get_ip_public(self, queue_target, url, json=False, key=None):
        """Request the url service and put the result in the queue_target."""
        try:
            response = urlopen(url, timeout=self.timeout).read().decode('utf-8')
        except Exception as e:
            logger.debug("IP plugin - Cannot open URL {} ({})".format(url, e))
            queue_target.put(None)
        else:
            # Request depend on service
            try:
                if not json:
                    queue_target.put(response)
                else:
                    queue_target.put(loads(response)[key])
            except ValueError:
                queue_target.put(None)
