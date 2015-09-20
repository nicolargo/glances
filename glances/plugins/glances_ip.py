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

"""IP plugin."""

# Import Glances libs
from glances.core.glances_globals import is_freebsd
from glances.core.glances_logging import logger
from glances.plugins.glances_plugin import GlancesPlugin

# XXX FreeBSD: Segmentation fault (core dumped)
# -- https://bitbucket.org/al45tair/netifaces/issues/15
if not is_freebsd:
    try:
        import netifaces
        netifaces_tag = True
    except ImportError:
        netifaces_tag = False
else:
    netifaces_tag = False


class Plugin(GlancesPlugin):

    """Glances IP Plugin.

    stats is a dict
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update IP stats using the input method.

        Stats is dict
        """
        # Reset stats
        self.reset()

        if self.input_method == 'local' and netifaces_tag:
            # Update stats using the netifaces lib
            try:
                default_gw = netifaces.gateways()['default'][netifaces.AF_INET]
            except (KeyError, AttributeError) as e:
                logger.debug("Cannot grab the default gateway ({0})".format(e))
            else:
                try:
                    self.stats['address'] = netifaces.ifaddresses(default_gw[1])[netifaces.AF_INET][0]['addr']
                    self.stats['mask'] = netifaces.ifaddresses(default_gw[1])[netifaces.AF_INET][0]['netmask']
                    self.stats['mask_cidr'] = self.ip_to_cidr(self.stats['mask'])
                    self.stats['gateway'] = netifaces.gateways()['default'][netifaces.AF_INET][0]
                except (KeyError, AttributeError) as e:
                    logger.debug("Can not grab IP information (%s)".format(e))

        elif self.input_method == 'snmp':
            # Not implemented yet
            pass

        # Update the view
        self.update_views()

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        GlancesPlugin.update_views(self)

        # Add specifics informations
        # Optional
        for key in self.stats.keys():
            self.views[key]['optional'] = True

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_ip:
            return ret

        # Build the string message
        msg = ' - '
        ret.append(self.curse_add_line(msg))
        msg = 'IP '
        ret.append(self.curse_add_line(msg, 'TITLE'))
        msg = '{0:}/{1}'.format(self.stats['address'], self.stats['mask_cidr'])
        ret.append(self.curse_add_line(msg))

        return ret

    @staticmethod
    def ip_to_cidr(ip):
        """Convert IP address to CIDR.

        Example: '255.255.255.0' will return 24
        """
        return sum([int(x) << 8 for x in ip.split('.')]) // 8128
