#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""IP plugin."""

import threading

from glances.globals import json_loads, queue, urlopen_auth
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel
from glances.timer import Timer, getTimeSinceLastUpdate

# Import plugin specific dependency
try:
    import netifaces
except ImportError as e:
    import_error_tag = True
    logger.warning(f"Missing Python Lib ({e}), IP plugin is disabled")
else:
    import_error_tag = False

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'address': {
        'description': 'Private IP address',
    },
    'mask': {
        'description': 'Private IP mask',
    },
    'mask_cidr': {
        'description': 'Private IP mask in CIDR format',
        'unit': 'number',
    },
    'gateway': {
        'description': 'Private IP gateway',
    },
    'public_address': {
        'description': 'Public IP address',
    },
    'public_info_human': {
        'description': 'Public IP information',
    },
}


class PluginModel(GlancesPluginModel):
    """Glances IP Plugin.

    stats is a dict
    """

    _default_public_refresh_interval = 300

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, fields_description=fields_description)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Public information (see issue #2732)
        self.public_address = ""
        self.public_info = ""
        self.public_api = self.get_conf_value("public_api", default=[None])[0]
        self.public_username = self.get_conf_value("public_username", default=[None])[0]
        self.public_password = self.get_conf_value("public_password", default=[None])[0]
        self.public_field = self.get_conf_value("public_field", default=[None])
        self.public_template = self.get_conf_value("public_template", default=[None])[0]
        self.public_disabled = (
            self.get_conf_value('public_disabled', default='False')[0].lower() != 'false'
            or self.public_api is None
            or self.public_field is None
        )
        self.public_address_refresh_interval = self.get_conf_value(
            "public_refresh_interval", default=self._default_public_refresh_interval
        )

    def get_private_ip(self, stats, stop=False):
        # Get the default gateway thanks to the netifaces lib
        try:
            default_gw = netifaces.gateways()['default'][netifaces.AF_INET]
        except (KeyError, AttributeError) as e:
            logger.debug(f"Cannot grab default gateway IP address ({e})")
            stop = True
        else:
            stats['gateway'] = default_gw[0]

        return (stop, stats)

    def get_first_ip(self, stats, stop=False):
        try:
            default_gw = netifaces.gateways()['default'][netifaces.AF_INET]
            address = netifaces.ifaddresses(default_gw[1])[netifaces.AF_INET][0]['addr']
            mask = netifaces.ifaddresses(default_gw[1])[netifaces.AF_INET][0]['netmask']
        except (KeyError, AttributeError) as e:
            logger.debug(f"Cannot grab private IP address ({e})")
            stop = True
        else:
            stats['address'] = address
            stats['mask'] = mask
            stats['mask_cidr'] = self.ip_to_cidr(stats['mask'])

        return (stop, stats)

    def get_public_ip(self, stats, stop=True):
        time_since_update = getTimeSinceLastUpdate('public-ip')
        try:
            if not self.public_disabled and (
                self.public_address == "" or time_since_update > self.public_address_refresh_interval
            ):
                self.public_info = PublicIpInfo(self.public_api, self.public_username, self.public_password).get()
                self.public_address = self.public_info['ip']
        except (KeyError, AttributeError, TypeError) as e:
            logger.debug(f"Cannot grab public IP information ({e})")
        else:
            stats['public_address'] = (
                self.public_address if not self.args.hide_public_info else self.__hide_ip(self.public_address)
            )
            stats['public_info_human'] = self.public_info_for_human(self.public_info)

        return (stop, stats)

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update IP stats using the input method.

        :return: the stats dict
        """
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local' and not import_error_tag:
            stats = self.get_stats_for_local_input(stats)

        elif self.input_method == 'snmp':
            # Not implemented yet
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def get_stats_for_local_input(self, stats):
        # Private IP address
        stop, stats = self.get_private_ip(stats)
        # If multiple IP addresses are available, only the one with the default gateway is returned
        if not stop:
            stop, stats = self.get_first_ip(stats)
        # Public IP address
        if not stop:
            stop, stats = self.get_public_ip(stats)

        return stats

    def __hide_ip(self, ip):
        """Hide last to digit of the given IP address"""
        return '.'.join(ip.split('.')[0:2]) + '.*.*'

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled() or import_error_tag:
            return ret

        # Build the string message
        msg = ' - '
        ret.append(self.curse_add_line(msg, optional=True))

        # Start with the private IP information
        msg = 'IP '
        ret.append(self.curse_add_line(msg, 'TITLE', optional=True))
        if 'address' in self.stats:
            msg = '{}'.format(self.stats['address'])
            ret.append(self.curse_add_line(msg, optional=True))
        if 'mask_cidr' in self.stats:
            # VPN with no internet access (issue #842)
            msg = '/{}'.format(self.stats['mask_cidr'])
            ret.append(self.curse_add_line(msg, optional=True))

        # Then with the public IP information
        try:
            msg_pub = '{}'.format(self.stats['public_address'])
        except (UnicodeEncodeError, KeyError):
            # Add KeyError exception (see https://github.com/nicolargo/glances/issues/1469)
            pass
        else:
            if self.stats['public_address']:
                msg = ' Pub '
                ret.append(self.curse_add_line(msg, 'TITLE', optional=True))
                ret.append(self.curse_add_line(msg_pub, optional=True))

            if self.stats['public_info_human']:
                ret.append(self.curse_add_line(' {}'.format(self.stats['public_info_human']), optional=True))

        return ret

    def public_info_for_human(self, public_info):
        """Return the data to pack to the client."""
        if not public_info:
            return ''

        return self.public_template.format(**public_info)

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


class PublicIpInfo:
    """Get public IP information from online service."""

    def __init__(self, url, username, password, timeout=2):
        """Init the class."""
        self.url = url
        self.username = username
        self.password = password
        self.timeout = timeout

    def get(self):
        """Return the public IP information returned by one of the online service."""
        q = queue.Queue()

        t = threading.Thread(target=self._get_ip_public_info, args=(q, self.url, self.username, self.password))
        t.daemon = True
        t.start()

        timer = Timer(self.timeout)
        info = None
        while not timer.finished() and info is None:
            if q.qsize() > 0:
                info = q.get()

        return info

    def _get_ip_public_info(self, queue_target, url, username, password):
        """Request the url service and put the result in the queue_target."""
        try:
            response = urlopen_auth(url, username, password).read()
        except Exception as e:
            logger.debug(f"IP plugin - Cannot get public IP information from {url} ({e})")
            queue_target.put(None)
        else:
            try:
                queue_target.put(json_loads(response))
            except (ValueError, KeyError) as e:
                logger.debug(f"IP plugin - Cannot load public IP information from {url} ({e})")
                queue_target.put(None)
