#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Wifi plugin.

Stats are retrieved over nl80211 (Linux only), the same data as `iw dev <interface> link`.
When nl80211 is not available, the /proc/net/wireless file is used instead:

# cat /proc/net/wireless
Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlp2s0: 0000   51.  -59.  -256        0      0      0      0   5881        0
"""

import operator

from glances.globals import file_exists, nativestr
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel
from glances.plugins.wifi import nl80211

# Fallback when nl80211 is unavailable: the /proc/net/wireless file. It goes through
# the legacy wireless extensions, which the kernel warns about (and which return
# nothing for Wi-Fi 7 hardware), hence nl80211 first.
# Note: both only give signal information about the current hotspot
WIRELESS_FILE = '/proc/net/wireless'
wireless_file_exists = file_exists(WIRELESS_FILE)

# nl80211 has no link quality value: derive it like the cfg80211 wireless extensions
# did, so the field is unchanged: the signal clamped to [-110, -40] dBm, shifted to 0..70
QUALITY_MIN_DBM = -110
QUALITY_MAX_DBM = -40

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
        'alert': True,
    },
}


class WifiPlugin(GlancesPluginModel):
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

        if self.input_method == 'local':
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
        try:
            signals = nl80211.station_signals()
        except nl80211.Nl80211Unavailable as e:
            # No netlink or no cfg80211: use the /proc/net/wireless file instead
            logger.debug(f"Wifi plugin: nl80211 unavailable ({e}), falling back to {WIRELESS_FILE}")
            return self._get_proc_wireless_stats()
        except OSError as e:
            # Transient nl80211 error: do not fall back (reading the file logs a kernel warning)
            logger.debug(f"Wifi plugin: nl80211 error ({e})")
            return ret
        for name, signal in signals.items():
            ret.append(
                {
                    'key': self.get_key(),
                    'ssid': name,
                    'quality_link': float(min(max(signal, QUALITY_MIN_DBM), QUALITY_MAX_DBM) - QUALITY_MIN_DBM),
                    'quality_level': float(signal),
                }
            )
        return ret

    def _get_proc_wireless_stats(self):
        ret = self.get_init_value()
        if not wireless_file_exists:
            return ret
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

    def get_alert(self, value, header=None, action_key=None, log=False):
        """Overwrite the default get_alert method.

        Alert is on signal quality where lower is better...

        :returns: string -- Signal alert
        """
        critical = self.get_limit('critical', stat_name=self.plugin_name)
        warning = self.get_limit('warning', stat_name=self.plugin_name)
        careful = self.get_limit('careful', stat_name=self.plugin_name)

        # Each threshold is tested on its own. Chaining them meant the first
        # undefined level raised TypeError against None and dropped the whole
        # result to DEFAULT, so a config setting only 'careful' lost its alert
        # entirely. GlancesPluginModel.get_alert already guards each level this
        # way; `is not None` is used here because these limits are negative dBm
        # values, where a plain truthiness test would discard a 0 threshold.
        ret = 'DEFAULT' if critical is None and warning is None and careful is None else 'OK'
        try:
            if critical is not None and value <= critical:
                ret = 'CRITICAL'
            elif warning is not None and value <= warning:
                ret = 'WARNING'
            elif careful is not None and value <= careful:
                ret = 'CAREFUL'
        except TypeError:
            # A non-numeric signal level (issue #1373) is not comparable at all.
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
        if not self.stats or self.is_disabled():
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
