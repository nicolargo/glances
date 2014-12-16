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

...for all Glances plugins.
"""

# Import system libs
import json
from datetime import datetime
from operator import itemgetter

# Import Glances lib
from glances.core.glances_globals import is_py3
from glances.core.glances_logging import logger
from glances.core.glances_logs import glances_logs


class GlancesPlugin(object):

    """Main class for Glances' plugin."""

    def __init__(self, args=None, items_history_list=None):
        """Init the plugin of plugins class."""
        # Plugin name (= module name without glances_)
        self.plugin_name = self.__class__.__module__[len('glances_'):]
        # logger.debug("Init plugin %s" % self.plugin_name)

        # Init the args
        self.args = args

        # Init the default alignement (for curses)
        self.set_align('left')

        # Init the input method
        self.input_method = 'local'
        self.short_system_name = None

        # Init the stats list
        self.stats = None

        # Init the history list
        self.items_history_list = items_history_list
        self.stats_history = self.init_stats_history()

        # Init the limits dictionnary
        self.limits = dict()

    def __repr__(self):
        """Return the raw stats."""
        return self.stats

    def __str__(self):
        """Return the human-readable stats."""
        return str(self.stats)

    def add_item_history(self, key, value):
        """Add an new item (key, value) to the current history"""
        try:
            self.stats_history[key].append(value)
        except KeyError:
            self.stats_history[key] = [value]

    def init_stats_history(self):
        """Init the stats history (dict of list)"""
        ret = None
        if self.args is not None and self.args.enable_history and self.get_items_history_list() is not None:
            init_list = [i['name'] for i in self.get_items_history_list()]
            logger.debug("Stats history activated for plugin {0} (items: {0})".format(self.plugin_name, init_list))
            ret = {}
        return ret

    def reset_stats_history(self):
        """Reset the stats history (dict of list)"""
        if self.args is not None and self.args.enable_history and self.get_items_history_list() is not None:
            reset_list = [i['name'] for i in self.get_items_history_list()]
            logger.debug("Reset history for plugin {0} (items: {0})".format(self.plugin_name, reset_list))
            self.stats_history = {}
        return self.stats_history

    def update_stats_history(self, item_name=''):
        """Update stats history"""
        if self.stats != [] and self.args is not None and self.args.enable_history and self.get_items_history_list() is not None:
            self.add_item_history('date', datetime.now())
            for i in self.get_items_history_list():
                if type(self.stats) is list:
                    # Stats is a list of data
                    # Iter throught it (for exemple, iter throught network
                    # interface)
                    for l in self.stats:
                        self.add_item_history(
                            l[item_name] + '_' + i['name'], l[i['name']])
                else:
                    # Stats is not a list
                    # Add the item to the history directly
                    self.add_item_history(i['name'], self.stats[i['name']])
        return self.stats_history

    def get_stats_history(self):
        """Return the stats history"""
        return self.stats_history

    def get_items_history_list(self):
        """Return the items history list"""
        return self.items_history_list

    def set_input(self, input_method, short_system_name=None):
        """Set the input method.

        * local: system local grab (psutil or direct access)
        * snmp: Client server mode via SNMP
        * glances: Client server mode via Glances API

        For SNMP, short_system_name is detected short OS name
        """
        self.input_method = input_method
        self.short_system_name = short_system_name
        return self.input_method

    def get_input(self):
        """Get the input method."""
        return self.input_method

    def get_short_system_name(self):
        """Get the short detected OS name"""
        return self.short_system_name

    def set_stats(self, input_stats):
        """Set the stats to input_stats."""
        self.stats = input_stats
        return self.stats

    def set_stats_snmp(self, bulk=False, snmp_oid={}):
        """Update stats using SNMP.

        If bulk=True, use a bulk request instead of a get request.
        """
        from glances.core.glances_snmp import GlancesSNMPClient

        # Init the SNMP request
        clientsnmp = GlancesSNMPClient(host=self.args.client,
                                       port=self.args.snmp_port,
                                       version=self.args.snmp_version,
                                       community=self.args.snmp_community)

        # Process the SNMP request
        ret = {}
        if bulk:
            # Bulk request
            snmpresult = clientsnmp.getbulk_by_oid(0, 10, *snmp_oid.values())

            if len(snmp_oid) == 1:
                # Bulk command for only one OID
                # Note: key is the item indexed but the OID result
                for item in snmpresult:
                    if item.keys()[0].startswith(snmp_oid.values()[0]):
                        ret[snmp_oid.keys()[0] + item.keys()
                            [0].split(snmp_oid.values()[0])[1]] = item.values()[0]
            else:
                # Build the internal dict with the SNMP result
                # Note: key is the first item in the snmp_oid
                index = 1
                for item in snmpresult:
                    item_stats = {}
                    item_key = None
                    for key in list(snmp_oid.keys()):
                        oid = snmp_oid[key] + '.' + str(index)
                        if oid in item:
                            if item_key is None:
                                item_key = item[oid]
                            else:
                                item_stats[key] = item[oid]
                    if item_stats != {}:
                        ret[item_key] = item_stats
                    index += 1
        else:
            # Simple get request
            snmpresult = clientsnmp.get_by_oid(*snmp_oid.values())

            # Build the internal dict with the SNMP result
            for key in list(snmp_oid.keys()):
                ret[key] = snmpresult[snmp_oid[key]]

        return ret

    def get_raw(self):
        """Return the stats object."""
        return self.stats

    def get_stats(self):
        """Return the stats object in JSON format"""
        return json.dumps(self.stats)

    def get_stats_item(self, item):
        """
        Return the stats object for a specific item (in JSON format)
        Stats should be a list of dict (processlist, network...)
        """
        if type(self.stats) is not list:
            if type(self.stats) is dict:
                try:
                    return json.dumps({item: self.stats[item]})
                except KeyError as e:
                    logger.error("Cannot get item {0} ({1})".format(item, e))
            else:
                return None
        else:
            try:
                # Source:
                # http://stackoverflow.com/questions/4573875/python-get-index-of-dictionary-item-in-list
                return json.dumps({item: map(itemgetter(item), self.stats)})
            except (KeyError, ValueError) as e:
                logger.error("Cannot get item {0} ({1})".format(item, e))
                return None

    def get_stats_value(self, item, value):
        """
        Return the stats object for a specific item=value (in JSON format)
        Stats should be a list of dict (processlist, network...)
        """
        if type(self.stats) is not list:
            return None
        else:
            if value.isdigit():
                value = int(value)
            try:
                return json.dumps({value: [i for i in self.stats if i[item] == value]})
            except (KeyError, ValueError) as e:
                logger.error("Cannot get item({0})=value({1}) ({2})".format(item, value, e))
                return None

    def load_limits(self, config):
        """Load the limits from the configuration file."""
        if (hasattr(config, 'has_section') and
                config.has_section(self.plugin_name)):
            for s, v in config.items(self.plugin_name):
                # Read limits
                try:
                    self.limits[
                        self.plugin_name + '_' + s] = config.get_option(self.plugin_name, s)
                except ValueError:
                    self.limits[
                        self.plugin_name + '_' + s] = config.get_raw_option(self.plugin_name, s).split(",")

    def set_limits(self, input_limits):
        """Set the limits to input_limits."""
        self.limits = input_limits
        return self.limits

    def get_limits(self):
        """Return the limits object."""
        return self.limits

    def get_alert(self, current=0, min=0, max=100, header="", log=False):
        """Return the alert status relative to a current value.

        Use this function for minor stats.

        If current < CAREFUL of max then alert = OK
        If current > CAREFUL of max then alert = CAREFUL
        If current > WARNING of max then alert = WARNING
        If current > CRITICAL of max then alert = CRITICAL

        If defined 'header' is added between the plugin name and the status.
        Only useful for stats with several alert status.

        If log=True than return the logged status.
        """
        # Compute the %
        try:
            value = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'
        except TypeError:
            return 'DEFAULT'

        # Manage limits
        ret = 'OK'
        try:
            if value > self.__get_limit_critical(header=header):
                ret = 'CRITICAL'
            elif value > self.__get_limit_warning(header=header):
                ret = 'WARNING'
            elif value > self.__get_limit_careful(header=header):
                ret = 'CAREFUL'
            elif current < min:
                ret = 'CAREFUL'
        except KeyError:
            return 'DEFAULT'

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
            # Add the log to the list
            glances_logs.add(ret, stat_name.upper(), value, [])

        # Default is ok
        return ret + log_str

    def get_alert_log(self, current=0, min=0, max=100, header=""):
        """Get the alert log."""
        return self.get_alert(current, min, max, header, log=True)

    def __get_limit_critical(self, header=""):
        if header == "":
            return self.limits[self.plugin_name + '_' + 'critical']
        else:
            return self.limits[self.plugin_name + '_' + header + '_' + 'critical']

    def __get_limit_warning(self, header=""):
        if header == "":
            return self.limits[self.plugin_name + '_' + 'warning']
        else:
            return self.limits[self.plugin_name + '_' + header + '_' + 'warning']

    def __get_limit_careful(self, header=""):
        if header == "":
            return self.limits[self.plugin_name + '_' + 'careful']
        else:
            return self.limits[self.plugin_name + '_' + header + '_' + 'careful']

    def get_conf_value(self, value, header="", plugin_name=None):
        """Return the configuration (header_)value for the current plugin (or the one given by the plugin_name var)"""
        if plugin_name is None:
            plugin_name = self.plugin_name
        if header == "":
            try:
                return self.limits[plugin_name + '_' + value]
            except KeyError:
                return []
        else:
            try:
                return self.limits[plugin_name + '_' + header + '_' + value]
            except KeyError:
                return []

    def is_hide(self, value, header=""):
        """Return True if the value is in the hide configuration list."""
        return value in self.get_conf_value('hide', header=header)

    def has_alias(self, header):
        """Return the alias name for the relative header or None if nonexist"""
        try:
            return self.limits[self.plugin_name + '_' + header + '_' + 'alias'][0]
        except (KeyError, IndexError):
            return None

    def msg_curse(self, args=None, max_width=None):
        """Return default string to display in the curse interface."""
        return [self.curse_add_line(str(self.stats))]

    def get_stats_display(self, args=None, max_width=None):
        """Return a dict with all the information needed to display the stat.

        key     | description
        ----------------------------
        display | Display the stat (True or False)
        msgdict | Message to display (list of dict [{ 'msg': msg, 'decoration': decoration } ... ])
        align   | Message position
        """
        display_curse = False

        if hasattr(self, 'display_curse'):
            display_curse = self.display_curse
        if hasattr(self, 'align'):
            align_curse = self.align

        if max_width is not None:
            ret = {'display': display_curse,
                   'msgdict': self.msg_curse(args, max_width=max_width),
                   'align': align_curse}
        else:
            ret = {'display': display_curse,
                   'msgdict': self.msg_curse(args),
                   'align': align_curse}

        return ret

    def curse_add_line(self, msg, decoration="DEFAULT",
                       optional=False, additional=False,
                       splittable=False):
        """Return a dict with

        Where:
            msg: string
            decoration:
                DEFAULT: no decoration
                UNDERLINE: underline
                BOLD: bold
                TITLE: for stat title
                PROCESS: for process name
                STATUS: for process status
                NICE: for process niceness
                OK: Value is OK and non logged
                OK_LOG: Value is OK and logged
                CAREFUL: Value is CAREFUL and non logged
                CAREFUL_LOG: Value is CAREFUL and logged
                WARNING: Value is WARINING and non logged
                WARNING_LOG: Value is WARINING and logged
                CRITICAL: Value is CRITICAL and non logged
                CRITICAL_LOG: Value is CRITICAL and logged
            optional: True if the stat is optional (display only if space is available)
            additional: True if the stat is additional (display only if space is available after optional)
            spittable: Line can be splitted to fit on the screen (default is not)
        """
        return {'msg': msg, 'decoration': decoration, 'optional': optional, 'additional': additional, 'splittable': splittable}

    def curse_new_line(self):
        """Go to a new line."""
        return self.curse_add_line('\n')

    def set_align(self, align='left'):
        """Set the Curse align"""
        if align in ('left', 'right', 'bottom'):
            self.align = align
        else:
            self.align = 'left'

    def get_align(self):
        """Get the Curse align"""
        return self.align

    def auto_unit(self, number, low_precision=False):
        """Make a nice human-readable string out of number.

        Number of decimal places increases as quantity approaches 1.

        examples:
        CASE: 613421788        RESULT:       585M low_precision:       585M
        CASE: 5307033647       RESULT:      4.94G low_precision:       4.9G
        CASE: 44968414685      RESULT:      41.9G low_precision:      41.9G
        CASE: 838471403472     RESULT:       781G low_precision:       781G
        CASE: 9683209690677    RESULT:      8.81T low_precision:       8.8T
        CASE: 1073741824       RESULT:      1024M low_precision:      1024M
        CASE: 1181116006       RESULT:      1.10G low_precision:       1.1G

        'low_precision=True' returns less decimal places potentially
        sacrificing precision for more readability.
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

        for symbol in reversed(symbols):
            value = float(number) / prefix[symbol]
            if value > 1:
                decimal_precision = 0
                if value < 10:
                    decimal_precision = 2
                elif value < 100:
                    decimal_precision = 1
                if low_precision:
                    if symbol in 'MK':
                        decimal_precision = 0
                    else:
                        decimal_precision = min(1, decimal_precision)
                elif symbol in 'K':
                    decimal_precision = 0
                return '{0:.{decimal}f}{symbol}'.format(
                    value, decimal=decimal_precision, symbol=symbol)
        return '{0!s}'.format(number)

    def _log_result_decorator(fct):
        """Log (DEBUG) the result of the function fct"""
        def wrapper(*args, **kw):
            ret = fct(*args, **kw)
            if is_py3:
                logger.debug("%s %s %s return %s" % (args[0].__class__.__name__, args[
                             0].__class__.__module__[len('glances_'):], fct.__name__, ret))
            else:
                logger.debug("%s %s %s return %s" % (args[0].__class__.__name__, args[
                             0].__class__.__module__[len('glances_'):], fct.func_name, ret))
            return ret
        return wrapper

    # Mandatory to call the decorator in childs' classes
    _log_result_decorator = staticmethod(_log_result_decorator)
