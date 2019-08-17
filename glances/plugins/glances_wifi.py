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

"""Wifi plugin."""

import operator

from glances.compat import nativestr, PY3
from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin

import psutil
# Use the Wifi Python lib (https://pypi.python.org/pypi/wifi)
# Linux-only
try:
    from wifi.scan import Cell
    from wifi.exceptions import InterfaceError
except ImportError as e:
    import_error_tag = True
    logger.warning("Missing Python Lib ({}), Wifi plugin is disabled".format(e))
else:
    import_error_tag = False

# Python 3 is not supported (see issue #1377)
if PY3:
    import_error_tag = True
    logger.warning("Wifi lib is not compliant with Python 3, Wifi plugin is disabled")


class Plugin(GlancesPlugin):
    """Glances Wifi plugin.

    Get stats of the current Wifi hotspots.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

    def get_key(self):
        """Return the key of the list.

        :returns: string -- SSID is the dict key
        """
        return 'ssid'

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update Wifi stats using the input method.

        Stats is a list of dict (one dict per hotspot)

        :returns: list -- Stats is a list of dict (hotspot)
        """
        # Init new stats
        stats = self.get_init_value()

        # Exist if we can not grab the stats
        if import_error_tag:
            return stats

        if self.input_method == 'local':
            # Update stats using the standard system lib

            # Grab network interface stat using the psutil net_io_counter method
            try:
                netiocounters = psutil.net_io_counters(pernic=True)
            except UnicodeDecodeError:
                return stats

            for net in netiocounters:
                # Do not take hidden interface into account
                if self.is_hide(net):
                    continue

                # Grab the stats using the Wifi Python lib
                try:
                    wifi_cells = Cell.all(net)
                except InterfaceError as e:
                    # Not a Wifi interface
                    logger.debug("WIFI plugin: Scan InterfaceError ({})".format(e))
                    pass
                except Exception as e:
                    # Other error
                    logger.debug("WIFI plugin: Can not grab cellule stats ({})".format(e))
                    pass
                else:
                    for wifi_cell in wifi_cells:
                        hotspot = {
                            'key': self.get_key(),
                            'ssid': wifi_cell.ssid,
                            'signal': wifi_cell.signal,
                            'quality': wifi_cell.quality,
                            'encrypted': wifi_cell.encrypted,
                            'encryption_type': wifi_cell.encryption_type if wifi_cell.encrypted else None
                        }
                        # Add the hotspot to the list
                        stats.append(hotspot)

        elif self.input_method == 'snmp':
            # Update stats using SNMP

            # Not implemented yet
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def get_alert(self, value):
        """Overwrite the default get_alert method.

        Alert is on signal quality where lower is better...

        :returns: string -- Signal alert
        """
        ret = 'OK'
        try:
            if value <= self.get_limit('critical', stat_name=self.plugin_name):
                ret = 'CRITICAL'
            elif value <= self.get_limit('warning', stat_name=self.plugin_name):
                ret = 'WARNING'
            elif value <= self.get_limit('careful', stat_name=self.plugin_name):
                ret = 'CAREFUL'
        except (TypeError, KeyError) as e:
            # Catch TypeError for issue1373
            ret = 'DEFAULT'

        return ret

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert on signal thresholds
        for i in self.stats:
            self.views[i[self.get_key()]]['signal']['decoration'] = self.get_alert(i['signal'])
            self.views[i[self.get_key()]]['quality']['decoration'] = self.views[i[self.get_key()]]['signal']['decoration']

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or import_error_tag or self.is_disable():
            return ret

        # Max size for the interface name
        ifname_max_width = max_width - 5

        # Build the string message
        # Header
        msg = '{:{width}}'.format('WIFI', width=ifname_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = '{:>7}'.format('dBm')
        ret.append(self.curse_add_line(msg))

        # Hotspot list (sorted by name)
        for i in sorted(self.stats, key=operator.itemgetter(self.get_key())):
            # Do not display hotspot with no name (/ssid)...
            # of ssid/signal None... See issue #1151 and #issue1973
            if i['ssid'] == '' or i['ssid'] is None or i['signal'] is None:
                continue
            ret.append(self.curse_new_line())
            # New hotspot
            hotspotname = i['ssid']
            # Add the encryption type (if it is available)
            if i['encrypted']:
                hotspotname += ' {}'.format(i['encryption_type'])
            # Cut hotspotname if it is too long
            if len(hotspotname) > ifname_max_width:
                hotspotname = '_' + hotspotname[-ifname_max_width + 1:]
            # Add the new hotspot to the message
            msg = '{:{width}}'.format(nativestr(hotspotname),
                                      width=ifname_max_width)
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format(i['signal'], width=ifname_max_width)
            ret.append(self.curse_add_line(msg,
                                           self.get_views(item=i[self.get_key()],
                                                          key='signal',
                                                          option='decoration')))

        return ret
