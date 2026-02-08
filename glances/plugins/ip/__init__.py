#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""IP plugin."""

import threading

from glances.globals import get_ip_address, json_loads, urlopen_auth
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

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


class IpPlugin(GlancesPluginModel):
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

        # Init thread to grab public IP address asynchronously
        self.public_ip_thread = None
        if not self.public_disabled:
            self.public_ip_thread = ThreadPublicIpAddress(
                url=self.public_api,
                username=self.public_username,
                password=self.public_password,
                refresh_interval=self.public_address_refresh_interval,
            )
            self.public_ip_thread.start()

    def get_first_ip(self, stats):
        stats['address'], stats['mask'] = get_ip_address()
        stats['mask_cidr'] = self.ip_to_cidr(stats['mask'])

        return stats

    def get_public_ip(self, stats):
        """Get public IP information from the background thread (non-blocking)."""
        if self.public_ip_thread is None:
            return stats

        try:
            # Read public IP info from the background thread (non-blocking)
            self.public_info = self.public_ip_thread.public_info
            if self.public_info:
                self.public_address = self.public_info.get('ip', '')
        except (KeyError, AttributeError, TypeError) as e:
            logger.debug(f"Cannot grab public IP information ({e})")

        if self.public_address:
            stats['public_address'] = (
                self.public_address if not self.args.hide_public_info else self.__hide_ip(self.public_address)
            )
            stats['public_info_human'] = self.public_info_for_human(self.public_info)

        return stats

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update IP stats using the input method.

        :return: the stats dict
        """
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            stats = self.get_stats_for_local_input(stats)

        elif self.input_method == 'snmp':
            # Not implemented yet
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def get_stats_for_local_input(self, stats):
        # Get Public and Private IP address
        if self.get_first_ip(stats):
            self.get_public_ip(stats)
        return stats

    def exit(self):
        """Overwrite the exit method to close the thread."""
        if self.public_ip_thread is not None:
            self.public_ip_thread.stop()
        # Call the parent class
        super().exit()

    def __hide_ip(self, ip):
        """Hide last to digit of the given IP address"""
        return '.'.join(ip.split('.')[0:2]) + '.*.*'

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled():
            return ret

        # Start with the private IP information
        if 'address' in self.stats:
            msg = 'IP '
            ret.append(self.curse_add_line(msg, 'TITLE', optional=True))
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


class ThreadPublicIpAddress(threading.Thread):
    """Thread class to fetch public IP address asynchronously.

    This prevents blocking the main Glances startup and update cycle.
    """

    def __init__(self, url, username, password, refresh_interval, timeout=2):
        """Init the thread.

        :param url: URL of the public IP API
        :param username: Optional username for API authentication
        :param password: Optional password for API authentication
        :param refresh_interval: Time in seconds between refreshes
        :param timeout: Timeout for the API request
        """
        logger.debug("IP plugin - Create thread for public IP address")
        super().__init__()
        self.daemon = True
        self._stopper = threading.Event()

        self.url = url
        self.username = username
        self.password = password
        self.refresh_interval = refresh_interval
        self.timeout = timeout

        # Public IP information (shared with main thread)
        self._public_info = {}
        self._public_info_lock = threading.Lock()

    def run(self):
        """Grab public IP information in a loop.

        Runs until stop() is called, refreshing at the configured interval.
        """
        while not self._stopper.is_set():
            # Fetch public IP information
            info = self._fetch_public_ip_info()
            if info is not None:
                with self._public_info_lock:
                    self._public_info = info

            # Wait for the refresh interval or until stopped
            self._stopper.wait(self.refresh_interval)

    def _fetch_public_ip_info(self):
        """Fetch public IP information from the configured API."""
        try:
            response = urlopen_auth(self.url, self.username, self.password, self.timeout).read()
            return json_loads(response)
        except Exception as e:
            logger.debug(f"IP plugin - Cannot get public IP information from {self.url} ({e})")
            return None

    @property
    def public_info(self):
        """Return the current public IP information (thread-safe)."""
        with self._public_info_lock:
            return self._public_info.copy()

    def stop(self, timeout=None):
        """Stop the thread."""
        logger.debug("IP plugin - Close thread for public IP address")
        self._stopper.set()

    def stopped(self):
        """Return True if the thread is stopped."""
        return self._stopper.is_set()
