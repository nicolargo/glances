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

"""
I am your father...

...for all Glances plugins.
"""

# Import system libs
import json
from datetime import datetime
from operator import itemgetter

# Import Glances lib
from glances.core.glances_actions import GlancesActions
from glances.core.glances_globals import is_py3
from glances.core.glances_logging import logger
from glances.core.glances_logs import glances_logs


class GlancesPlugin(object):

    """Main class for Glances plugin."""

    def __init__(self, args=None, items_history_list=None):
        """Init the plugin of plugins class."""
        # Plugin name (= module name without glances_)
        self.plugin_name = self.__class__.__module__[len('glances_'):]
        # logger.debug("Init plugin %s" % self.plugin_name)

        # Init the args
        self.args = args

        # Init the default alignement (for curses)
        self._align = 'left'

        # Init the input method
        self._input_method = 'local'
        self._short_system_name = None

        # Init the stats list
        self.stats = None

        # Init the history list
        self.items_history_list = items_history_list
        self.stats_history = self.init_stats_history()

        # Init the limits dictionnary
        self._limits = dict()

        # Init the actions
        self.actions = GlancesActions()

        # Init the views
        self.views = dict()

    def exit(self):
        """Method to be called when Glances exit"""
        logger.debug("Stop the {0} plugin".format(self.plugin_name))

    def __repr__(self):
        """Return the raw stats."""
        return self.stats

    def __str__(self):
        """Return the human-readable stats."""
        return str(self.stats)

    def get_key(self):
        """Return the key of the list."""
        return None

    def add_item_history(self, key, value):
        """Add an new item (key, value) to the current history."""
        try:
            self.stats_history[key].append(value)
        except KeyError:
            self.stats_history[key] = [value]

    def init_stats_history(self):
        """Init the stats history (dict of list)."""
        ret = None
        if self.args is not None and self.args.enable_history and self.get_items_history_list() is not None:
            init_list = [i['name'] for i in self.get_items_history_list()]
            logger.debug("Stats history activated for plugin {0} (items: {0})".format(
                self.plugin_name, init_list))
            ret = {}
        return ret

    def reset_stats_history(self):
        """Reset the stats history (dict of list)."""
        if self.args is not None and self.args.enable_history and self.get_items_history_list() is not None:
            reset_list = [i['name'] for i in self.get_items_history_list()]
            logger.debug("Reset history for plugin {0} (items: {0})".format(
                self.plugin_name, reset_list))
            self.stats_history = {}

    def update_stats_history(self, item_name=''):
        """Update stats history."""
        if (self.stats and self.args is not None and
                self.args.enable_history and
                self.get_items_history_list() is not None):
            self.add_item_history('date', datetime.now())
            for i in self.get_items_history_list():
                if isinstance(self.stats, list):
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

    def get_stats_history(self):
        """Return the stats history."""
        return self.stats_history

    def get_items_history_list(self):
        """Return the items history list."""
        return self.items_history_list

    @property
    def input_method(self):
        """Get the input method."""
        return self._input_method

    @input_method.setter
    def input_method(self, input_method):
        """Set the input method.

        * local: system local grab (psutil or direct access)
        * snmp: Client server mode via SNMP
        * glances: Client server mode via Glances API
        """
        self._input_method = input_method

    @property
    def short_system_name(self):
        """Get the short detected OS name (SNMP)."""
        return self._short_system_name

    @short_system_name.setter
    def short_system_name(self, short_name):
        """Set the short detected OS name (SNMP)."""
        self._short_system_name = short_name

    def set_stats(self, input_stats):
        """Set the stats to input_stats."""
        self.stats = input_stats

    def get_stats_snmp(self, bulk=False, snmp_oid=None):
        """Update stats using SNMP.

        If bulk=True, use a bulk request instead of a get request.
        """
        snmp_oid = snmp_oid or {}

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
                    if item_stats:
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

    def get_export(self):
        """Return the stats object to export."""
        return self.get_raw()

    def get_stats(self):
        """Return the stats object in JSON format."""
        return json.dumps(self.stats)

    def get_stats_item(self, item):
        """Return the stats object for a specific item in JSON format.

        Stats should be a list of dict (processlist, network...)
        """
        if isinstance(self.stats, dict):
            try:
                return json.dumps({item: self.stats[item]})
            except KeyError as e:
                logger.error("Cannot get item {0} ({1})".format(item, e))
                return None
        elif isinstance(self.stats, list):
            try:
                # Source:
                # http://stackoverflow.com/questions/4573875/python-get-index-of-dictionary-item-in-list
                return json.dumps({item: map(itemgetter(item), self.stats)})
            except (KeyError, ValueError) as e:
                logger.error("Cannot get item {0} ({1})".format(item, e))
                return None
        else:
            return None

    def get_stats_value(self, item, value):
        """Return the stats object for a specific item=value in JSON format.

        Stats should be a list of dict (processlist, network...)
        """
        if not isinstance(self.stats, list):
            return None
        else:
            if value.isdigit():
                value = int(value)
            try:
                return json.dumps({value: [i for i in self.stats if i[item] == value]})
            except (KeyError, ValueError) as e:
                logger.error(
                    "Cannot get item({0})=value({1}) ({2})".format(item, value, e))
                return None

    def update_views(self):
        """Default builder fo the stats views.

        The V of MVC
        A dict of dict with the needed information to display the stats.
        Example for the stat xxx:
        'xxx': {'decoration': 'DEFAULT',
                'optional': False,
                'additional': False,
                'splittable': False}
        """
        ret = {}

        if (isinstance(self.get_raw(), list) and
                self.get_raw() is not None and
                self.get_key() is not None):
            # Stats are stored in a list of dict (ex: NETWORK, FS...)
            for i in self.get_raw():
                ret[i[self.get_key()]] = {}
                for key in i.keys():
                    value = {'decoration': 'DEFAULT',
                             'optional': False,
                             'additional': False,
                             'splittable': False}
                    ret[i[self.get_key()]][key] = value
        elif isinstance(self.get_raw(), dict) and self.get_raw() is not None:
            # Stats are stored in a dict (ex: CPU, LOAD...)
            for key in self.get_raw().keys():
                value = {'decoration': 'DEFAULT',
                         'optional': False,
                         'additional': False,
                         'splittable': False}
                ret[key] = value

        self.views = ret

        return self.views

    def set_views(self, input_views):
        """Set the views to input_views."""
        self.views = input_views

    def get_views(self, item=None, key=None, option=None):
        """Return the views object.

        If key is None, return all the view for the current plugin
        else if option is None return the view for the specific key (all option)
        else return the view fo the specific key/option

        Specify item if the stats are stored in a dict of dict (ex: NETWORK, FS...)
        """
        if item is None:
            item_views = self.views
        else:
            item_views = self.views[item]

        if key is None:
            return item_views
        else:
            if option is None:
                return item_views[key]
            else:
                return item_views[key][option]

    def load_limits(self, config):
        """Load limits from the configuration file, if it exists."""
        if (hasattr(config, 'has_section') and
                config.has_section(self.plugin_name)):
            for level, _ in config.items(self.plugin_name):
                # Read limits
                limit = '_'.join([self.plugin_name, level])
                try:
                    self._limits[limit] = config.get_float_value(self.plugin_name, level)
                except ValueError:
                    self._limits[limit] = config.get_value(self.plugin_name, level).split(",")
                logger.debug("Load limit: {0} = {1}".format(limit, self._limits[limit]))

    @property
    def limits(self):
        """Return the limits object."""
        return self._limits

    @limits.setter
    def limits(self, input_limits):
        """Set the limits to input_limits."""
        self._limits = input_limits

    def get_alert(self, current=0, minimum=0, maximum=100, header="", log=False):
        """Return the alert status relative to a current value.

        Use this function for minor stats.

        If current < CAREFUL of max then alert = OK
        If current > CAREFUL of max then alert = CAREFUL
        If current > WARNING of max then alert = WARNING
        If current > CRITICAL of max then alert = CRITICAL

        If defined 'header' is added between the plugin name and the status.
        Only useful for stats with several alert status.

        If log=True than add log if necessary
        elif log=False than do not log
        elig log=None than apply the config given in the conf file
        """
        # Compute the %
        try:
            value = (current * 100) / maximum
        except ZeroDivisionError:
            return 'DEFAULT'
        except TypeError:
            return 'DEFAULT'

        # Build the stat_name = plugin_name + header
        if header == "":
            stat_name = self.plugin_name
        else:
            stat_name = self.plugin_name + '_' + header

        # Manage limits
        ret = 'OK'
        try:
            if value > self.__get_limit('critical', stat_name=stat_name):
                ret = 'CRITICAL'
            elif value > self.__get_limit('warning', stat_name=stat_name):
                ret = 'WARNING'
            elif value > self.__get_limit('careful', stat_name=stat_name):
                ret = 'CAREFUL'
            elif current < minimum:
                ret = 'CAREFUL'
        except KeyError:
            return 'DEFAULT'

        # Manage log
        log_str = ""
        if self.__get_limit_log(stat_name=stat_name, default_action=log):
            # Add _LOG to the return string
            # So stats will be highlited with a specific color
            log_str = "_LOG"
            # Add the log to the list
            glances_logs.add(ret, stat_name.upper(), value, [])

        # Manage action
        # Here is a command line for the current trigger ?
        try:
            command = self.__get_limit_action(ret.lower(), stat_name=stat_name)
        except KeyError:
            # Reset the trigger
            self.actions.set(stat_name, ret.lower())
        else:
            # A command line is available for the current alert, run it
            # Build the {{mustache}} dictionnary
            if isinstance(self.stats, list):
                # If the stats are stored in a list of dict (fs plugin for exemple)
                # Return the dict for the current header
                mustache_dict = {}
                for item in self.stats:
                    if item[self.get_key()] == header:
                        mustache_dict = item
                        break
            else:
                # Use the stats dict
                mustache_dict = self.stats
            # Run the action
            self.actions.run(
                stat_name, ret.lower(), command, mustache_dict=mustache_dict)

        # Default is ok
        return ret + log_str

    def get_alert_log(self, current=0, minimum=0, maximum=100, header=""):
        """Get the alert log."""
        return self.get_alert(current, minimum, maximum, header, log=True)

    def __get_limit(self, criticity, stat_name=""):
        """Return the limit value for the alert."""
        # Get the limit for stat + header
        # Exemple: network_wlan0_rx_careful
        try:
            limit = self._limits[stat_name + '_' + criticity]
        except KeyError:
            # Try fallback to plugin default limit
            # Exemple: network_careful
            limit = self._limits[self.plugin_name + '_' + criticity]

        # Return the limit
        return limit

    def __get_limit_action(self, criticity, stat_name=""):
        """Return the action for the alert."""
        # Get the action for stat + header
        # Exemple: network_wlan0_rx_careful_action
        try:
            ret = self._limits[stat_name + '_' + criticity + '_action']
        except KeyError:
            # Try fallback to plugin default limit
            # Exemple: network_careful_action
            ret = self._limits[self.plugin_name + '_' + criticity + '_action']

        # Return the action list
        return ret

    def __get_limit_log(self, stat_name, default_action=False):
        """Return the log tag for the alert."""
        # Get the log tag for stat + header
        # Exemple: network_wlan0_rx_log
        try:
            log_tag = self._limits[stat_name + '_log']
        except KeyError:
            # Try fallback to plugin default log
            # Exemple: network_log
            try:
                log_tag = self._limits[self.plugin_name + '_log']
            except KeyError:
                # By defaukt, log are disabled
                return default_action

        # Return the action list
        return log_tag[0].lower() == 'true'

    def get_conf_value(self, value, header="", plugin_name=None):
        """Return the configuration (header_) value for the current plugin.

        ...or the one given by the plugin_name var.
        """
        if plugin_name is None:
            # If not default use the current plugin name
            plugin_name = self.plugin_name

        if header != "":
            # Add the header
            plugin_name = plugin_name + '_' + header

        try:
            return self._limits[plugin_name + '_' + value]
        except KeyError:
            return []

    def is_hide(self, value, header=""):
        """Return True if the value is in the hide configuration list."""
        return value in self.get_conf_value('hide', header=header)

    def has_alias(self, header):
        """Return the alias name for the relative header or None if nonexist."""
        try:
            return self._limits[self.plugin_name + '_' + header + '_' + 'alias'][0]
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
            align_curse = self._align

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
        """Return a dict with.

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
                CPU_TIME: for process cpu time
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

    @property
    def align(self):
        """Get the curse align."""
        return self._align

    @align.setter
    def align(self, value):
        """Set the curse align.

        value: left, right, bottom.
        """
        self._align = value

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
        """Log (DEBUG) the result of the function fct."""
        def wrapper(*args, **kw):
            ret = fct(*args, **kw)
            if is_py3:
                logger.debug("%s %s %s return %s" % (
                    args[0].__class__.__name__,
                    args[0].__class__.__module__[len('glances_'):],
                    fct.__name__, ret))
            else:
                logger.debug("%s %s %s return %s" % (
                    args[0].__class__.__name__,
                    args[0].__class__.__module__[len('glances_'):],
                    fct.func_name, ret))
            return ret
        return wrapper

    # Mandatory to call the decorator in childs' classes
    _log_result_decorator = staticmethod(_log_result_decorator)
