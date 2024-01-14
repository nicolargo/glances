# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Wifi plugin.

Stats are retreived from the nmcli command line (Linux only):

# nmcli -t -f active,ssid,signal,security,chan dev wifi

# nmcli -t -f active,ssid,signal dev wifi
no:Livebox-C820:77
yes:Livebox-C820:72

or the /proc/net/wireless file (Linux only):

# cat /proc/net/wireless
Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlp2s0: 0000   51.  -59.  -256        0      0      0      0   5881        0
"""

import operator
from shutil import which
import threading
import time

from glances.globals import nativestr, file_exists
from glances.plugins.plugin.model import GlancesPluginModel
from glances.secure import secure_popen
from glances.logger import logger

# Test if the nmcli command exists and is executable
# it allows to get the list of the available hotspots
NMCLI_COMMAND = which('nmcli')
NMCLI_ARGS = '-t -f active,ssid,signal,security dev wifi'
nmcli_command_exists = NMCLI_COMMAND is not None

# Backup solution is to use the /proc/net/wireless file
# but it only give signal information about the current hotspot
WIRELESS_FILE = '/proc/net/wireless'
wireless_file_exists = file_exists(WIRELESS_FILE)

if not nmcli_command_exists and not wireless_file_exists:
    logger.debug("Wifi plugin is disabled (no %s command or %s file found)" % ('nmcli', WIRELESS_FILE))


class PluginModel(GlancesPluginModel):
    """Glances Wifi plugin.

    Get stats of the current Wifi hotspots.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(args=args, config=config, stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Global Thread running all the scans
        self._thread = None

    def exit(self):
        """Overwrite the exit method to close threads."""
        if self._thread is not None:
            self._thread.stop()
        # Call the father class
        super(PluginModel, self).exit()

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
        if not nmcli_command_exists and not wireless_file_exists:
            return stats

        if self.input_method == 'local' and nmcli_command_exists:
            # Only refresh if there is not other scanning thread
            if self._thread is None:
                thread_is_running = False
            else:
                thread_is_running = self._thread.is_alive()
            if not thread_is_running:
                # Run hotspot scanner thanks to the nmcli command
                self._thread = ThreadHotspot(self.get_refresh_time())
                self._thread.start()
            # Get the result (or [] if the scan is ongoing)
            stats = self._thread.stats
        elif self.input_method == 'local' and wireless_file_exists:
            # As a backup solution, use the /proc/net/wireless file
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
                    stats.append(
                        {
                            'key': self.get_key(),
                            'ssid': wifi_stats[0][:-1],
                            'signal': float(wifi_stats[3]),
                            'security': '',
                        }
                    )
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
            # No max_width defined, return an emptu curse message
            logger.debug("No max_width defined for the {} plugin, it will not be displayed.".format(self.plugin_name))
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
            if i['ssid'] == '' or i['ssid'] is None or i['signal'] is None:
                continue
            ret.append(self.curse_new_line())
            # New hotspot
            hotspot_name = i['ssid']
            # Cut hotspot_name if it is too long
            if len(hotspot_name) > if_name_max_width:
                hotspot_name = '_' + hotspot_name[-if_name_max_width - len(i['security']) + 1 :]
            # Add the new hotspot to the message
            msg = '{:{width}} {security}'.format(
                nativestr(hotspot_name), width=if_name_max_width - len(i['security']) - 1, security=i['security']
            )
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format(
                i['signal'],
            )
            ret.append(
                self.curse_add_line(msg, self.get_views(item=i[self.get_key()], key='signal', option='decoration'))
            )

        return ret


class ThreadHotspot(threading.Thread):
    """
    Specific thread for the Wifi hotspot scanner.
    """

    def __init__(self, refresh_time=2):
        """Init the class."""
        super(ThreadHotspot, self).__init__()
        # Refresh time
        self.refresh_time = refresh_time
        # Event needed to stop properly the thread
        self._stopper = threading.Event()
        # Is part of Ports plugin
        self.plugin_name = "wifi"

    def run(self):
        """Get hotspots stats using the nmcli command line"""
        while not self.stopped():
            # Run the nmcli command
            nmcli_raw = secure_popen(NMCLI_COMMAND + ' ' + NMCLI_ARGS).split('\n')
            nmcli_result = []
            for h in nmcli_raw:
                h = h.split(':')
                if len(h) != 4 or h[0] != 'yes':
                    # Do not process the line if it is not the active hotspot
                    continue
                nmcli_result.append({'key': 'ssid', 'ssid': h[1], 'signal': -float(h[2]), 'security': h[3]})
            self.thread_stats = nmcli_result
            # Wait refresh time until next scan
            # Note: nmcli cache the result for x seconds
            time.sleep(self.refresh_time)

    @property
    def stats(self):
        """Stats getter."""
        if hasattr(self, 'thread_stats'):
            return self.thread_stats
        else:
            return []

    def stop(self, timeout=None):
        """Stop the thread."""
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.is_set()
