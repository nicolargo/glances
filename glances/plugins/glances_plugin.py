#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

import json
from time import time

# Global list to manage the elapsed time
last_update_times = {}


def getTimeSinceLastUpdate(IOType):
    global last_update_times
    # assert(IOType in ['net', 'disk', 'process_disk'])
    current_time = time()
    last_time = last_update_times.get(IOType)
    if not last_time:
        time_since_update = 1
    else:
        time_since_update = current_time - last_time
    last_update_times[IOType] = current_time
    return time_since_update


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


    def load_limits(self, config):
        """
        Load the limits from the configuration file
        """

        if (config.has_section(self.plugin_name)):
            # print ">>> Load limits for %s" % self.plugin_name
            # Read LOAD limits
            for s in [ 'careful', 'warning', 'critical' ]:
                try:
                    value = config.get_option(self.plugin_name, s)
                except:
                    pass
                else:
                    self.limits[self.plugin_name + '_' + s] = value
                    # print ">>> %s = %s" % (self.plugin_name + '_' + s, value)


    def __repr__(self):
        # Return the raw stats
        return self.stats
        

    def __str__(self):
        # Return the human-readable stats
        return str(self.stats)


    def get_raw(self):
        # Return the stats object
        return self.stats


    def get_stats(self):
        # Return the stats object in JSON format for the RPC API
        return json.dumps(self.stats)


    def get_limits(self):
        # Return the limits object
        return self.limits


    def get_alert(self, current=0, min=0, max=100):
        # Return the alert status relative to a current value
        # Use this function for minor stat
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        # stat is USER, SYSTEM, IOWAIT or STEAL
        try:
            value = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        if (value > self.get_limit_critical()):
            return 'CRITICAL'
        elif (value > self.get_limit_warning()):
            return 'WARNING'
        elif (value > self.get_limit_careful()):
            return 'CAREFUL'

        return 'OK'


    def get_alert_log(self, current=0, min=0, max=100):
        # Return the alert status relative to a current value
        # Use this function for major stat
        # If current < CAREFUL of max then alert = OK_LOG
        # If current > CAREFUL of max then alert = CAREFUL_LOG
        # If current > WARNING of max then alert = WARNING_LOG
        # If current > CRITICAL of max then alert = CRITICAL_LOG
        # stat is USER, SYSTEM, IOWAIT or STEAL
        try:
            value = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        if (value > self.get_limit_critical()):
            return 'CRITICAL_LOG'
        elif (value > self.get_limit_warning()):
            return 'WARNING_LOG'
        elif (value > self.get_limit_careful()):
            return 'CAREFUL_LOG'

        return 'OK_LOG'


    def get_limit_critical(self):
        return self.limits[self.plugin_name + '_' + 'critical']


    def get_limit_warning(self):
        return self.limits[self.plugin_name + '_' + 'warning']

    def get_limit_careful(self):
        return self.limits[self.plugin_name + '_' + 'careful']


    def msg_curse(self, args):
        """
        Return default string to display in the curse interface
        """
        return [ self.curse_add_line(str(self.stats)) ]


    def get_curse(self, args=None):
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

        if (hasattr(self, 'display_curse')):
            display_curse = self.display_curse
        if (hasattr(self, 'column_curse')):
            column_curse = self.column_curse
        if (hasattr(self, 'line_curse')):
            line_curse = self.line_curse

        return { 'display': display_curse,
                 'msgdict': self.msg_curse(args),
                 'column': column_curse,
                 'line': line_curse }


    def curse_add_line(self, msg, decoration="DEFAULT", optional=False):
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
                WARINING: Value is WARINING and non logged
                WARINING_LOG: Value is WARINING and logged
                CRITICAL: Value is CRITICAL and non logged
                CRITICAL_LOG: Value is CRITICAL and logged
            optional: True if the stat is optional (display only if space is available)
        """ 

        return { 'msg': msg, 'decoration': decoration, 'optional': optional }


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
