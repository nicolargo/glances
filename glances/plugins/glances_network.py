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
"""Network plugin."""
# SNMP OID
# http://www.net-snmp.org/docs/mibs/interfaces.html
# Dict key = interface_name

import base64
import collections
import operator

from glances.core.glances_timer import getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin
import psutil


snmp_oid = {'default': {'interface_name': '1.3.6.1.2.1.2.2.1.2',
                        'cumulative_rx': '1.3.6.1.2.1.2.2.1.10',
                        'cumulative_tx': '1.3.6.1.2.1.2.2.1.16'}}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
# 'color' define the graph color in #RGB format
items_history_list = [{'name': 'rx', 'color': '#00FF00', 'y_unit': 'bit/s'},
                      {'name': 'tx', 'color': '#FF0000', 'y_unit': 'bit/s'}]


class Plugin(GlancesPlugin):

    """Glances' network Plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args, items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

        self.args = args
        
        # Init the stats
        self.reset()

    def get_key(self):
        """Return the key of the list"""
        return 'interface_name'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []
        self.view_data = collections.defaultdict()

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update network stats using the input method.

        Stats is a list of dict (one dict per interface)
        """
        # Reset stats
        self.reset()

        if self.get_input() == 'local':
            # Update stats using the standard system lib

            # Grab network interface stat using the PsUtil net_io_counter method
            try:
                netiocounters = psutil.net_io_counters(pernic=True)
            except UnicodeDecodeError:
                return self.stats

            # Previous network interface stats are stored in the network_old variable
            if not hasattr(self, 'network_old'):
                # First call, we init the network_old var
                try:
                    self.network_old = netiocounters
                except (IOError, UnboundLocalError):
                    pass
            else:
                # By storing time data we enable Rx/s and Tx/s calculations in the
                # XML/RPC API, which would otherwise be overly difficult work
                # for users of the API
                time_since_update = getTimeSinceLastUpdate('net')

                # Loop over interfaces
                network_new = netiocounters
                for net in network_new:
                    try:
                        # Try necessary to manage dynamic network interface
                        netstat = {}
                        netstat['interface_name'] = net
                        netstat['time_since_update'] = time_since_update
                        netstat['cumulative_rx'] = network_new[net].bytes_recv
                        netstat['rx'] = (network_new[net].bytes_recv -
                                         self.network_old[net].bytes_recv)
                        netstat['cumulative_tx'] = network_new[net].bytes_sent
                        netstat['tx'] = (network_new[net].bytes_sent -
                                         self.network_old[net].bytes_sent)
                        netstat['cumulative_cx'] = (netstat['cumulative_rx'] +
                                                    netstat['cumulative_tx'])
                        netstat['cx'] = netstat['rx'] + netstat['tx']
                    except KeyError:
                        continue
                    else:
                        netstat['key'] = self.get_key()
                        self.stats.append(netstat)

                # Save stats to compute next bitrate
                self.network_old = network_new

        elif self.get_input() == 'snmp':
            # Update stats using SNMP

            # SNMP bulk command to get all network interface in one shot
            try:
                netiocounters = self.set_stats_snmp(snmp_oid=snmp_oid[self.get_short_system_name()],
                                                    bulk=True)
            except KeyError:
                netiocounters = self.set_stats_snmp(snmp_oid=snmp_oid['default'],
                                                    bulk=True)

            # Previous network interface stats are stored in the network_old variable
            if not hasattr(self, 'network_old'):
                # First call, we init the network_old var
                try:
                    self.network_old = netiocounters
                except (IOError, UnboundLocalError):
                    pass
            else:
                # See description in the 'local' block
                time_since_update = getTimeSinceLastUpdate('net')

                # Loop over interfaces
                network_new = netiocounters

                for net in network_new:
                    try:
                        # Try necessary to manage dynamic network interface
                        netstat = {}
                        # Windows: a tips is needed to convert HEX to TXT
                        # http://blogs.technet.com/b/networking/archive/2009/12/18/how-to-query-the-list-of-network-interfaces-using-snmp-via-the-ifdescr-counter.aspx
                        if self.get_short_system_name() == 'windows':
                            try:
                                netstat['interface_name'] = str(base64.b16decode(net[2:-2].upper()))
                            except TypeError:
                                netstat['interface_name'] = net
                        else:
                            netstat['interface_name'] = net
                        netstat['time_since_update'] = time_since_update
                        netstat['cumulative_rx'] = float(network_new[net]['cumulative_rx'])
                        netstat['rx'] = (float(network_new[net]['cumulative_rx']) -
                                         float(self.network_old[net]['cumulative_rx']))
                        netstat['cumulative_tx'] = float(network_new[net]['cumulative_tx'])
                        netstat['tx'] = (float(network_new[net]['cumulative_tx']) -
                                         float(self.network_old[net]['cumulative_tx']))
                        netstat['cumulative_cx'] = (netstat['cumulative_rx'] +
                                                    netstat['cumulative_tx'])
                        netstat['cx'] = netstat['rx'] + netstat['tx']
                    except KeyError:
                        continue
                    else:
                        netstat['key'] = self.get_key()
                        self.stats.append(netstat)

                # Save stats to compute next bitrate
                self.network_old = network_new

        # Update the history list
        self.update_stats_history(self.get_key())

        # Update the view
        self.update_views()
        
        return self.stats

    def update_views(self):
        """Update stats views"""
        # Call the father's method
        GlancesPlugin.update_views(self)

        # Add specifics informations
        # Alert
        for i in self.stats:
            ifrealname = i['interface_name'].split(':')[0]
            self.views[i[self.get_key()]]['rx']['decoration'] = self.get_alert(int(i['rx'] // i['time_since_update'] * 8),
                                                                               header=ifrealname + '_rx')
            self.views[i[self.get_key()]]['tx']['decoration'] = self.get_alert(int(i['tx'] // i['time_since_update'] * 8),
                                                                               header=ifrealname + '_tx')
    
    def generate_view_data(self, max_width=None):
        self.view_data = {}
        
        # Max size for the interface name
        if max_width is not None and max_width >= 23:
            # Interface size name = max_width - space for interfaces bitrate
            ifname_max_width = max_width - 14
        else:
            ifname_max_width = 9
            
        
        self.view_data['title'] = '{0:{width}}'.format(_("NETWORK"), width=ifname_max_width)
        self.view_data['network_cumul'] = self.args.network_cumul
        self.view_data['network_sum'] = self.args.network_sum
        
        if self.args.network_cumul:
            # Cumulative stats
            if self.args.network_sum:
                # Sum stats
                self.view_data['title_rx_tx'] = '{0:>14}'.format(_("Rx+Tx"))
            else:
                # Rx/Tx stats
                self.view_data['title_rx'] = '{0:>7}'.format(_("Rx"))
                self.view_data['title_tx'] = '{0:>7}'.format(_("Tx"))
        else:
            # Bitrate stats
            if self.args.network_sum:
                # Sum stats
                self.view_data['title_rx_tx'] = '{0:>14}'.format(_("Rx+Tx/s"))
            else:
                self.view_data['title_rx'] = '{0:>7}'.format(_("Rx/s"))
                self.view_data['title_tx'] = '{0:>7}'.format(_("Tx/s"))

        self.view_data['interfaces'] = []
        
        n = 0
        # Interface list (sorted by name)
        for i in sorted(self.stats, key=operator.itemgetter(self.get_key())):
            # Do not display hidden interfaces
            if self.is_hide(i['interface_name']):
                continue
            # Format stats
            # Is there an alias for the interface name ?
            ifrealname = i['interface_name'].split(':')[0]
            ifname = self.has_alias(i['interface_name'])
            if ifname is None:
                ifname = ifrealname
            if len(ifname) > ifname_max_width:
                # Cut interface name if it is too long
                ifname = '_' + ifname[-ifname_max_width + 1:]
            if self.args.byte:
                # Bytes per second (for dummy)
                if self.args.network_cumul:
                    rx = self.auto_unit(int(i['cumulative_rx']))
                    tx = self.auto_unit(int(i['cumulative_tx']))
                    sx = self.auto_unit(int(i['cumulative_tx'])
                                        + int(i['cumulative_tx']))
                else:
                    rx = self.auto_unit(int(i['rx'] // i['time_since_update']))
                    tx = self.auto_unit(int(i['tx'] // i['time_since_update']))
                    sx = self.auto_unit(int(i['rx'] // i['time_since_update'])
                                        + int(i['tx'] // i['time_since_update']))
            else:
                # Bits per second (for real network administrator | Default)
                if self.args.network_cumul:
                    rx = self.auto_unit(int(i['cumulative_rx'] * 8)) + "b"
                    tx = self.auto_unit(int(i['cumulative_tx'] * 8)) + "b"
                    sx = self.auto_unit(int(i['cumulative_rx'] * 8)
                                        + int(i['cumulative_tx'] * 8)) + "b"
                else:
                    rx = self.auto_unit(int(i['rx'] // i['time_since_update'] * 8)) + "b"
                    tx = self.auto_unit(int(i['tx'] // i['time_since_update'] * 8)) + "b"
                    sx = self.auto_unit(int(i['rx'] // i['time_since_update'] * 8) +
                                        int(i['tx'] // i['time_since_update'] * 8)) + "b"
            interface = {}
            interface['interface_name'] = '{0:{width}}'.format(ifname, width=ifname_max_width)
            if self.args.network_sum:
                interface['rx_tx'] = '{0:>14}'.format(sx)
            else:
                interface['rx'] = '{0:>7}'.format(rx)
                interface['tx'] = '{0:>7}'.format(tx)
            self.view_data['interfaces'].append(interface)
            n = n + 1
                
    def get_view_data(self, options):
        if options:
            if 'network_cumul' in options:
                self.args.network_cumul = options.get('network_cumul')
            if 'network_sum' in options:
                self.args.network_sum = options.get('network_sum')
            if 'network_by_bytes' in options:
                self.args.byte = options.get('network_by_bytes')        
        self.generate_view_data()
        return self.view_data

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""

        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_network:
            return ret

        # Build the string message
        # Header
        ret.append(self.curse_add_line(self.view_data['title'], "TITLE"))
        
        if 'title_rx_tx' in self.view_data:
            ret.append(self.curse_add_line(self.view_data['title_rx_tx']))
        else:
            ret.append(self.curse_add_line(self.view_data['title_rx']))
            ret.append(self.curse_add_line(self.view_data['title_tx']))

        
        # Interface list (sorted by name)
        for i in self.view_data['interfaces']:
            interface = i
            
            # New line
            ret.append(self.curse_new_line())
            
            ret.append(self.curse_add_line(interface['interface_name']))
            if args.network_sum:
                ret.append(self.curse_add_line(self.curse_add_line(interface['tx_rx'])))
            else:
                ret.append(self.curse_add_line(
                    self.curse_add_line(interface['rx']), self.get_views(item=i[self.get_key()], key='rx', option='decoration')))
                ret.append(self.curse_add_line(
                    self.curse_add_line(interface['tx']), self.get_views(item=i[self.get_key()], key='tx', option='decoration')))

        return ret
