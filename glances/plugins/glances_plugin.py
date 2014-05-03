# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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
"""
I am your father...
For all Glances plugins
"""

# Import system libs
import json

# Import Glances lib
from glances.core.glances_globals import glances_logs


class GlancesPlugin(object):
    """
    Main class for Glances' plugin
    """

    def __init__(self):
        # Plugin name (= module name without glances_)
        self.plugin_name = self.__class__.__module__[len('glances_'):]

        # Init the stats list
        self.stats = None

        # Init the limits dictionnary
        self.limits = dict()

    def __repr__(self):
        # Return the raw stats
        return self.stats

    def __str__(self):
        # Return the human-readable stats
        return str(self.stats)

    def set_stats(self, input_stats):
        # Set the stats to input_stats
        self.stats = input_stats
        return self.stats

    def set_stats_snmp(self, snmp_oid={}):
        # Update stats using SNMP
        from glances.core.glances_snmp import GlancesSNMPClient

        # Init the SNMP request
        clientsnmp = GlancesSNMPClient()

        # Process the SNMP request
        snmpresult = clientsnmp.get_by_oid(*snmp_oid.values())

        # Build the internal dict with the SNMP result
        ret = {}
        for key in snmp_oid.iterkeys():
            ret[key] = snmpresult[snmp_oid[key]]

        return ret

    def get_raw(self):
        # Return the stats object
        return self.stats

    def get_stats(self):
        # Return the stats object in JSON format for the RPC API
        return json.dumps(self.stats)

    def load_limits(self, config):
        """
        Load the limits from the configuration file
        """
        if (hasattr(config, 'has_section') and
                config.has_section(self.plugin_name)):
            # print "Load limits for %s" % self.plugin_name
            for s, v in config.items(self.plugin_name):
                # Read limits
                # print "\t%s = %s" % (self.plugin_name + '_' + s, v)
                try:
                    self.limits[self.plugin_name + '_' + s] = config.get_option(self.plugin_name, s)
                except ValueError:
                    self.limits[self.plugin_name + '_' + s] = config.get_raw_option(self.plugin_name, s).split(",")

    def set_limits(self, input_limits):
        # Set the limits to input_limits
        self.limits = input_limits
        return self.limits

    def get_limits(self):
        # Return the limits object
        return self.limits

    def get_alert(self, current=0, min=0, max=100, header="", log=False):
        # Return the alert status relative to a current value
        # Use this function for minor stat
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        # stat is USER, SYSTEM, IOWAIT or STEAL
        #
        # If defined 'header' is added between the plugin name and the status
        # Only usefull for stats with several alert status
        #
        # If log=True than return the logged status

        # Compute the %
        try:
            value = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'
        except TypeError:
            return 'DEFAULT'

        # Manage limits
        ret = 'OK'
        if value > self.get_limit_critical(header=header):
            ret = 'CRITICAL'
        elif value > self.get_limit_warning(header=header):
            ret = 'WARNING'
        elif value > self.get_limit_careful(header=header):
            ret = 'CAREFUL'

        # Manage log (if needed)
        log_str = ""
        if log:
            # Add _LOG to the return string
            # So stats will be highlited with a specific color
            log_str = "_LOG"
            # Get the stat_name = plugin_name (+ header)
            if header == "":
                stat_name = self.plugin_name
            else:
                stat_name = self.plugin_name + '_' + header
            # !!! TODO: Manage the process list (last param => [])
            glances_logs.add(ret, stat_name.upper(), value, [])

        # Default is ok
        return ret + log_str

    def get_alert_log(self, current=0, min=0, max=100, header=""):
        return self.get_alert(current, min, max, header, log=True)

    def get_limit_critical(self, header=""):
        if header == "":
            return self.limits[self.plugin_name + '_' + 'critical']
        else:
            return self.limits[self.plugin_name + '_' + header + '_' + 'critical']

    def get_limit_warning(self, header=""):
        if header == "":
            return self.limits[self.plugin_name + '_' + 'warning']
        else:
            return self.limits[self.plugin_name + '_' + header + '_' + 'warning']

    def get_hide(self, header=""):
        """
        Return the hide configuration list key for the current plugin
        """
        if header == "":
            try:
                return self.limits[self.plugin_name + '_' + 'hide']
            except Exception:
                return []
        else:
            try:
                return self.limits[self.plugin_name + '_' + header + '_' + 'hide']
            except Exception:
                return []

    def is_hide(self, value, header=""):
        """
        Return True if the value is in the hide configuration list
        """
        return value in self.get_hide(header=header)

    def get_limit_careful(self, header=""):
        if header == "":
            return self.limits[self.plugin_name + '_' + 'careful']
        else:
            return self.limits[self.plugin_name + '_' + header + '_' + 'careful']

    def msg_curse(self, args):
        """
        Return default string to display in the curse interface
        """
        return [self.curse_add_line(str(self.stats))]

    def get_stats_display(self, args=None):
        # Return a dict with all the information needed to display the stat
        # key     | description
        #----------------------------
        # display | Display the stat (True or False)
        # msgdict | Message to display (list of dict [{ 'msg': msg, 'decoration': decoration } ... ])
        # column  | column number
        # line    | Line number

        display_curse = False
        column_curse = -1
        line_curse = -1

        if hasattr(self, 'display_curse'):
            display_curse = self.display_curse
        if hasattr(self, 'column_curse'):
            column_curse = self.column_curse
        if hasattr(self, 'line_curse'):
            line_curse = self.line_curse

        return {'display': display_curse,
                'msgdict': self.msg_curse(args),
                'column': column_curse,
                'line': line_curse}

    def curse_add_line(self, msg, decoration="DEFAULT", optional=False, splittable=False):
        """
        Return a dict with: { 'msg': msg, 'decoration': decoration, 'optional': False }
        with:
            msg: string
            decoration:
                DEFAULT: no decoration
                UNDERLINE: underline
                BOLD: bold
                TITLE: for stat title
                OK: Value is OK and non logged
                OK_LOG: Value is OK and logged
                CAREFUL: Value is CAREFUL and non logged
                CAREFUL_LOG: Value is CAREFUL and logged
                WARNING: Value is WARINING and non logged
                WARNING_LOG: Value is WARINING and logged
                CRITICAL: Value is CRITICAL and non logged
                CRITICAL_LOG: Value is CRITICAL and logged
            optional: True if the stat is optional (display only if space is available)
            spittable: Line can be splitted to fit on the screen (default is not)
        """

        return {'msg': msg, 'decoration': decoration, 'optional': optional, 'splittable': splittable}

    def curse_new_line(self):
        """
        Go to a new line
        """
        return self.curse_add_line('\n')

    def auto_unit(self, val, low_precision=False):
        """
        Make a nice human readable string out of val
        Number of decimal places increases as quantity approaches 1

        examples:
        CASE: 613421788        RESULT:       585M low_precision:       585M
        CASE: 5307033647       RESULT:      4.94G low_precision:       4.9G
        CASE: 44968414685      RESULT:      41.9G low_precision:      41.9G
        CASE: 838471403472     RESULT:       781G low_precision:       781G
        CASE: 9683209690677    RESULT:      8.81T low_precision:       8.8T
        CASE: 1073741824       RESULT:      1024M low_precision:      1024M
        CASE: 1181116006       RESULT:      1.10G low_precision:       1.1G

        parameter 'low_precision=True' returns less decimal places.
        potentially sacrificing precision for more readability
        """
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {
            'Y': 1208925819614629174706176,
            'Z': 1180591620717411303424,
            'E': 1152921504606846976,
            'P': 1125899906842624,
            'T': 1099511627776,
            'G': 1073741824,
            'M': 1048576,
            'K': 1024
        }

        for key in reversed(symbols):
            value = float(val) / prefix[key]
            if value > 1:
                fixed_decimal_places = 0
                if value < 10:
                    fixed_decimal_places = 2
                elif value < 100:
                    fixed_decimal_places = 1
                if low_precision:
                    if key in 'MK':
                        fixed_decimal_places = 0
                    else:
                        fixed_decimal_places = min(1, fixed_decimal_places)
                elif key in 'K':
                    fixed_decimal_places = 0
                formatter = "{0:.%df}{1}" % fixed_decimal_places
                return formatter.format(value, key)
        return "{0!s}".format(val)
