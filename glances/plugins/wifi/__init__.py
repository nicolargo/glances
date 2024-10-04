#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Wifi plugin.

Stats are retrieved from the /proc/net/wireless file (Linux only):

# cat /proc/net/wireless
Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlp2s0: 0000   51.  -59.  -256        0      0      0      0   5881        0
"""

import operator

from glances.globals import file_exists, nativestr
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Use stats available in the /proc/net/wireless file
# Note: it only give signal information about the current hotspot
WIRELESS_FILE = '/proc/net/wireless'
wireless_file_exists = file_exists(WIRELESS_FILE)

if not wireless_file_exists:
    logger.debug(f"Wifi plugin is disabled (can not read {WIRELESS_FILE} file)")

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: if True then compute and add *_gauge and *_rate_per_is fields
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'ssid': {'description': 'Wi-Fi network name.'},
    'quality_link': {
        'description': 'Signal quality level.',
        'unit': 'dBm',
    },
    'quality_level': {
        'description': 'Signal strong level.',
        'unit': 'dBm',
    },
}


class PluginModel(GlancesPluginModel):
    """Glances Wifi plugin.

    Get stats of the current Wifi hotspots.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Global Thread running all the scans
        self._thread = None

    def exit(self):
        """Overwrite the exit method to close threads."""
        if self._thread is not None:
            self._thread.stop()
        # Call the father class
        super().exit()

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

        if self.input_method == 'local' and wireless_file_exists:
            try:
                stats = self._get_wireless_stats()
            except (PermissionError, FileNotFoundError) as e:
                logger.debug(f"Wifi plugin error: can not read {WIRELESS_FILE} file ({e})")
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # Not implemented yet
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def _get_wireless_stats(self):
        ret = self.get_init_value()
        # As a backup solution, use the /proc/net/wireless file
        with open(WIRELESS_FILE) as f:
            # The first two lines are header
            f.readline()
            f.readline()
            # Others lines are Wifi stats
            wifi_stats = f.readline()
            while wifi_stats != '':
                # Extract the stats
                wifi_stats = wifi_stats.split()
                # Add the Wifi link to the list
                ret.append(
                    {
                        'key': self.get_key(),
                        'ssid': wifi_stats[0][:-1],
                        'quality_link': float(wifi_stats[2]),
                        'quality_level': float(wifi_stats[3]),
                    }
                )
                # Next line
                wifi_stats = f.readline()
        return ret

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
        super().update_views()

        # Add specifics information
        # Alert on quality_level thresholds
        for i in self.stats:
            self.views[i[self.get_key()]]['quality_level']['decoration'] = self.get_alert(i['quality_level'])

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or not wireless_file_exists or self.is_disabled():
            return ret

        # Max size for the interface name
        if max_width:
            if_name_max_width = max_width - 5
        else:
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

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
            if i['ssid'] == '' or i['ssid'] is None or i['quality_level'] is None:
                continue
            ret.append(self.curse_new_line())
            # New hotspot
            hotspot_name = i['ssid']
            msg = '{:{width}}'.format(nativestr(hotspot_name), width=if_name_max_width)
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format(
                i['quality_level'],
            )
            ret.append(
                self.curse_add_line(
                    msg, self.get_views(item=i[self.get_key()], key='quality_level', option='decoration')
                )
            )

        return ret
