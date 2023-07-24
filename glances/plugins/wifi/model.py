# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Wifi plugin.

Stats are retreived from the /proc/net/wireless file (Linux only).

# cat /proc/net/wireless
Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlp2s0: 0000   51.  -59.  -256        0      0      0      0   5881        0
"""

import operator

from glances.globals import nativestr, file_exists
from glances.plugins.plugin.model import GlancesPluginModel
from glances.logger import logger

WIRELESS_FILE = '/proc/net/wireless'

if file_exists(WIRELESS_FILE):
    wireless_file_exists = True
    logger.debug("Wifi plugin is enabled (%s file found)" % WIRELESS_FILE)
else:
    wireless_file_exists = False
    logger.debug("Wifi plugin is disabled (no %s file found)" % WIRELESS_FILE)


class PluginModel(GlancesPluginModel):
    """Glances Wifi plugin.

    Get stats of the current Wifi hotspots.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(args=args, config=config, stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

    def get_key(self):
        """Return the key of the list.

        :returns: string -- SSID is the dict key
        """
        return 'ssid'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update Wifi stats using the input method.

        Stats is a list of dict (one dict per hotspot)

        :returns: list -- Stats is a list of dict (hotspot)
        """
        # Init new stats
        stats = self.get_init_value()

        # Exist if we can not grab the stats
        if not wireless_file_exists:
            return stats

        if self.input_method == 'local':
            # Update stats using /proc/net/wireless file

            with open(WIRELESS_FILE, 'r') as f:
                # The first two lines are header
                f.readline()
                f.readline()
                # Others lines are Wifi stats
                wifi_stats = f.readline()
                while wifi_stats != '':
                    # Extract the stats
                    wifi_stats = wifi_stats.split()
                    # Add the Wifi link to the list
                    stats.append({
                        'key': self.get_key(),
                        'ssid': wifi_stats[0][:-1],
                        'signal': float(wifi_stats[3]),
                        'quality': float(wifi_stats[2]),
                        'noise': float(wifi_stats[4]),
                    })
                    # Next line
                    wifi_stats = f.readline()

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
        except (TypeError, KeyError):
            # Catch TypeError for issue1373
            ret = 'DEFAULT'

        return ret

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        # Add specifics information
        # Alert on signal thresholds
        for i in self.stats:
            self.views[i[self.get_key()]]['signal']['decoration'] = self.get_alert(i['signal'])
            self.views[i[self.get_key()]]['quality']['decoration'] = self.views[i[self.get_key()]]['signal'][
                'decoration'
            ]

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or not wireless_file_exists or self.is_disabled():
            return ret

        # Max size for the interface name
        if_name_max_width = max_width - 5

        # Build the string message
        # Header
        msg = '{:{width}}'.format('WIFI', width=if_name_max_width)
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
            hotspot_name = i['ssid']
            # Cut hotspot_name if it is too long
            if len(hotspot_name) > if_name_max_width:
                hotspot_name = '_' + hotspot_name[-if_name_max_width + 1:]
            # Add the new hotspot to the message
            msg = '{:{width}}'.format(nativestr(hotspot_name), width=if_name_max_width)
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format(
                i['signal'],
            )
            ret.append(
                self.curse_add_line(msg, self.get_views(item=i[self.get_key()], key='signal', option='decoration'))
            )

        return ret
