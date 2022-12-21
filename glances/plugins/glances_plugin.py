# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
I am your father...

...for all Glances plugins.
"""

import re
import copy

from glances.globals import json_dumps, json_dumps_dictlist
from glances.compat import iterkeys, itervalues, listkeys, map, mean, nativestr, PY3
from glances.actions import GlancesActions
from glances.history import GlancesHistory
from glances.logger import logger
from glances.events import glances_events
from glances.thresholds import glances_thresholds
from glances.timer import Counter, Timer
from glances.outputs.glances_unicode import unicode_message


fields_unit_short = {'percent': '%'}

fields_unit_type = {
    'percent': 'float',
    'percents': 'float',
    'number': 'int',
    'numbers': 'int',
    'int': 'int',
    'ints': 'int',
    'float': 'float',
    'floats': 'float',
    'second': 'int',
    'seconds': 'int',
    'byte': 'int',
    'bytes': 'int',
}


class GlancesPlugin(object):
    """Main class for Glances plugin."""

    def __init__(self, args=None, config=None, items_history_list=None, stats_init_value={}, fields_description=None):
        """Init the plugin of plugins class.

        All Glances' plugins should inherit from this class. Most of the
        methods are already implemented in the father classes.

        Your plugin should return a dict or a list of dicts (stored in the
        self.stats). As an example, you can have a look on the mem plugin
        (for dict) or network (for list of dicts).

        A plugin should implement:
        - the __init__ constructor: define the self.display_curse
        - the reset method: to set your self.stats variable to {} or []
        - the update method: where your self.stats variable is set
        and optionally:
        - the get_key method: set the key of the dict (only for list of dict)
        - the update_view method: only if you need to trick your output
        - the msg_curse: define the curse (UI) message (if display_curse is True)

        :args: args parameters
        :items_history_list: list of items to store in the history
        :stats_init_value: Default value for a stats item
        """
        # Plugin name (= module name without glances_)
        pos = self.__class__.__module__.find('glances_') + len('glances') + 1
        self.plugin_name = self.__class__.__module__[pos:]
        # logger.debug("Init plugin %s" % self.plugin_name)

        # Init the args
        self.args = args

        # Init the default alignment (for curses)
        self._align = 'left'

        # Init the input method
        self._input_method = 'local'
        self._short_system_name = None

        # Init the history list
        self.items_history_list = items_history_list
        self.stats_history = self.init_stats_history()

        # Init the limits (configuration keys) dictionary
        self._limits = dict()
        if config is not None:
            logger.debug('Load section {} in {}'.format(self.plugin_name, config.config_file_paths()))
            self.load_limits(config=config)

        # Init the actions
        self.actions = GlancesActions(args=args)

        # Init the views
        self.views = dict()

        # Hide stats if all the hide_zero_fields has never been != 0
        # Default is False, always display stats
        self.hide_zero = False
        self.hide_zero_fields = []

        # Set the initial refresh time to display stats the first time
        self.refresh_timer = Timer(0)

        # Init stats description
        self.fields_description = fields_description

        # Init the stats
        self.stats_init_value = stats_init_value
        self.stats = None
        self.reset()

    def __repr__(self):
        """Return the raw stats."""
        return self.stats

    def __str__(self):
        """Return the human-readable stats."""
        return str(self.stats)

    def get_init_value(self):
        """Return a copy of the init value."""
        return copy.copy(self.stats_init_value)

    def reset(self):
        """Reset the stats.

        This method should be overwritten by child classes.
        """
        self.stats = self.get_init_value()

    def exit(self):
        """Just log an event when Glances exit."""
        logger.debug("Stop the {} plugin".format(self.plugin_name))

    def get_key(self):
        """Return the key of the list."""
        return None

    def is_enabled(self, plugin_name=None):
        """Return true if plugin is enabled."""
        if not plugin_name:
            plugin_name = self.plugin_name
        try:
            d = getattr(self.args, 'disable_' + plugin_name)
        except AttributeError:
            d = getattr(self.args, 'enable_' + plugin_name, True)
        return d is False

    def is_disabled(self, plugin_name=None):
        """Return true if plugin is disabled."""
        return not self.is_enabled(plugin_name=plugin_name)

    def history_enable(self):
        return self.args is not None and not self.args.disable_history and self.get_items_history_list() is not None

    def init_stats_history(self):
        """Init the stats history (dict of GlancesAttribute)."""
        if self.history_enable():
            init_list = [a['name'] for a in self.get_items_history_list()]
            logger.debug("Stats history activated for plugin {} (items: {})".format(self.plugin_name, init_list))
        return GlancesHistory()

    def reset_stats_history(self):
        """Reset the stats history (dict of GlancesAttribute)."""
        if self.history_enable():
            reset_list = [a['name'] for a in self.get_items_history_list()]
            logger.debug("Reset history for plugin {} (items: {})".format(self.plugin_name, reset_list))
            self.stats_history.reset()

    def update_stats_history(self):
        """Update stats history."""
        # Build the history
        if self.get_export() and self.history_enable():
            # If the plugin data is a dict, the dict's key should be used
            if self.get_key() is None:
                item_name = ''
            else:
                item_name = self.get_key()
            for i in self.get_items_history_list():
                if isinstance(self.get_export(), list):
                    # Stats is a list of data
                    # Iter through it (for example, iter through network interface)
                    for l_export in self.get_export():
                        self.stats_history.add(
                            nativestr(l_export[item_name]) + '_' + nativestr(i['name']),
                            l_export[i['name']],
                            description=i['description'],
                            history_max_size=self._limits['history_size'],
                        )
                else:
                    # Stats is not a list
                    # Add the item to the history directly
                    self.stats_history.add(
                        nativestr(i['name']),
                        self.get_export()[i['name']],
                        description=i['description'],
                        history_max_size=self._limits['history_size'],
                    )

    def get_items_history_list(self):
        """Return the items history list."""
        return self.items_history_list

    def get_raw_history(self, item=None, nb=0):
        """Return the history (RAW format).

        - the stats history (dict of list) if item is None
        - the stats history for the given item (list) instead
        - None if item did not exist in the history
        """
        s = self.stats_history.get(nb=nb)
        if item is None:
            return s
        else:
            if item in s:
                return s[item]
            else:
                return None

    def get_json_history(self, item=None, nb=0):
        """Return the history (JSON format).

        - the stats history (dict of list) if item is None
        - the stats history for the given item (list) instead
        - None if item did not exist in the history
        Limit to lasts nb items (all if nb=0)
        """
        s = self.stats_history.get_json(nb=nb)
        if item is None:
            return s
        else:
            if item in s:
                return s[item]
            else:
                return None

    def get_export_history(self, item=None):
        """Return the stats history object to export."""
        return self.get_raw_history(item=item)

    def get_stats_history(self, item=None, nb=0):
        """Return the stats history (JSON format)."""
        s = self.get_json_history(nb=nb)

        if item is None:
            return json_dumps(s)

        return json_dumps_dictlist(s, item)

    def get_trend(self, item, nb=6):
        """Get the trend regarding to the last nb values.

        The trend is the diff between the mean of the last nb values
        and the current one.
        """
        raw_history = self.get_raw_history(item=item, nb=nb)
        if raw_history is None or len(raw_history) < nb:
            return None
        last_nb = [v[1] for v in raw_history]
        return last_nb[-1] - mean(last_nb[:-1])

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

    def sorted_stats(self):
        """Get the stats sorted by an alias (if present) or key."""
        key = self.get_key()
        try:
            return sorted(
                self.stats,
                key=lambda stat: tuple(
                    map(
                        lambda part: int(part) if part.isdigit() else part.lower(),
                        re.split(r"(\d+|\D+)", self.has_alias(stat[key]) or stat[key]),
                    )
                ),
            )
        except TypeError:
            # Correct "Starting an alias with a number causes a crash #1885"
            return sorted(
                self.stats,
                key=lambda stat: tuple(
                    map(lambda part: part.lower(), re.split(r"(\d+|\D+)", self.has_alias(stat[key]) or stat[key]))
                ),
            )

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

        from glances.snmp import GlancesSNMPClient

        # Init the SNMP request
        snmp_client = GlancesSNMPClient(
            host=self.args.client,
            port=self.args.snmp_port,
            version=self.args.snmp_version,
            community=self.args.snmp_community,
        )

        # Process the SNMP request
        ret = {}
        if bulk:
            # Bulk request
            snmp_result = snmp_client.getbulk_by_oid(0, 10, itervalues(*snmp_oid))

            if len(snmp_oid) == 1:
                # Bulk command for only one OID
                # Note: key is the item indexed but the OID result
                for item in snmp_result:
                    if iterkeys(item)[0].startswith(itervalues(snmp_oid)[0]):
                        ret[iterkeys(snmp_oid)[0] + iterkeys(item)[0].split(itervalues(snmp_oid)[0])[1]] = itervalues(
                            item
                        )[0]
            else:
                # Build the internal dict with the SNMP result
                # Note: key is the first item in the snmp_oid
                index = 1
                for item in snmp_result:
                    item_stats = {}
                    item_key = None
                    for key in iterkeys(snmp_oid):
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
            snmp_result = snmp_client.get_by_oid(itervalues(*snmp_oid))

            # Build the internal dict with the SNMP result
            for key in iterkeys(snmp_oid):
                ret[key] = snmp_result[snmp_oid[key]]

        return ret

    def get_raw(self):
        """Return the stats object."""
        return self.stats

    def get_export(self):
        """Return the stats object to export."""
        return self.get_raw()

    def get_stats(self):
        """Return the stats object in JSON format."""
        return json_dumps(self.stats)

    def get_json(self):
        """Return the stats object in JSON format."""
        return self.get_stats()

    def get_stats_item(self, item):
        """Return the stats object for a specific item in JSON format.

        Stats should be a list of dict (processlist, network...)
        """
        return json_dumps_dictlist(self.stats, item)

    def get_stats_value(self, item, value):
        """Return the stats object for a specific item=value in JSON format.

        Stats should be a list of dict (processlist, network...)
        """
        if not isinstance(self.stats, list):
            return None
        else:
            if not isinstance(value, int) and value.isdigit():
                value = int(value)
            try:
                return json_dumps({value: [i for i in self.stats if i[item] == value]})
            except (KeyError, ValueError) as e:
                logger.error("Cannot get item({})=value({}) ({})".format(item, value, e))
                return None

    def update_views_hidden(self):
        """Update the hidden views

        If the self.hide_zero is set then update the hidden field of the view
        It will check if all fields values are already be different from 0
        In this case, the hidden field is set to True

        Note: This function should be called by plugin (in the update_views method)

        Example (for network plugin):
        __Init__
            self.hide_zero_fields = ['rx', 'tx']
        Update views
            ...
            self.update_views_hidden()
        """
        if not self.hide_zero:
            return False
        if isinstance(self.get_raw(), list) and self.get_raw() is not None and self.get_key() is not None:
            # Stats are stored in a list of dict (ex: NETWORK, FS...)
            for i in self.get_raw():
                if any([i[f] for f in self.hide_zero_fields]):
                    for f in self.hide_zero_fields:
                        self.views[i[self.get_key()]][f]['_zero'] = self.views[i[self.get_key()]][f]['hidden']
                for f in self.hide_zero_fields:
                    self.views[i[self.get_key()]][f]['hidden'] = self.views[i[self.get_key()]][f]['_zero'] and i[f] == 0
        elif isinstance(self.get_raw(), dict) and self.get_raw() is not None:
            #
            # Warning: This code has never been tested because
            # no plugin with dict instance use the hidden function...
            #
            # Stats are stored in a dict (ex: CPU, LOAD...)
            for key in listkeys(self.get_raw()):
                if any([self.get_raw()[f] for f in self.hide_zero_fields]):
                    for f in self.hide_zero_fields:
                        self.views[f]['_zero'] = self.views[f]['hidden']
                for f in self.hide_zero_fields:
                    self.views[f]['hidden'] = self.views['_zero'] and self.views[f] == 0
        return True

    def update_views(self):
        """Update the stats views.

        The V of MVC
        A dict of dict with the needed information to display the stats.
        Example for the stat xxx:
        'xxx': {'decoration': 'DEFAULT',  >>> The decoration of the stats
                'optional': False,        >>> Is the stat optional
                'additional': False,      >>> Is the stat provide additional information
                'splittable': False,      >>> Is the stat can be cut (like process lon name)
                'hidden': False,          >>> Is the stats should be hidden in the UI
                '_zero': True}            >>> For internal purpose only
        """
        ret = {}

        if isinstance(self.get_raw(), list) and self.get_raw() is not None and self.get_key() is not None:
            # Stats are stored in a list of dict (ex: NETWORK, FS...)
            for i in self.get_raw():
                # i[self.get_key()] is the interface name (example for NETWORK)
                ret[i[self.get_key()]] = {}
                for key in listkeys(i):
                    value = {
                        'decoration': 'DEFAULT',
                        'optional': False,
                        'additional': False,
                        'splittable': False,
                        'hidden': False,
                        '_zero': self.views[i[self.get_key()]][key]['_zero']
                        if i[self.get_key()] in self.views
                        and key in self.views[i[self.get_key()]]
                        and 'zero' in self.views[i[self.get_key()]][key]
                        else True,
                    }
                    ret[i[self.get_key()]][key] = value
        elif isinstance(self.get_raw(), dict) and self.get_raw() is not None:
            # Stats are stored in a dict (ex: CPU, LOAD...)
            for key in listkeys(self.get_raw()):
                value = {
                    'decoration': 'DEFAULT',
                    'optional': False,
                    'additional': False,
                    'splittable': False,
                    'hidden': False,
                    '_zero': self.views[key]['_zero'] if key in self.views and '_zero' in self.views[key] else True,
                }
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
        else return the view of the specific key/option

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
                if option in item_views[key]:
                    return item_views[key][option]
                else:
                    return 'DEFAULT'

    def get_json_views(self, item=None, key=None, option=None):
        """Return the views (in JSON)."""
        return json_dumps(self.get_views(item, key, option))

    def load_limits(self, config):
        """Load limits from the configuration file, if it exists."""
        # By default set the history length to 3 points per second during one day
        self._limits['history_size'] = 28800

        if not hasattr(config, 'has_section'):
            return False

        # Read the global section
        # @TODO: not optimized because this section is loaded for each plugin...
        if config.has_section('global'):
            self._limits['history_size'] = config.get_float_value('global', 'history_size', default=28800)
            logger.debug("Load configuration key: {} = {}".format('history_size', self._limits['history_size']))

        # Read the plugin specific section
        if config.has_section(self.plugin_name):
            for level, _ in config.items(self.plugin_name):
                # Read limits
                limit = '_'.join([self.plugin_name, level])
                try:
                    self._limits[limit] = config.get_float_value(self.plugin_name, level)
                except ValueError:
                    self._limits[limit] = config.get_value(self.plugin_name, level).split(",")
                logger.debug("Load limit: {} = {}".format(limit, self._limits[limit]))

        return True

    @property
    def limits(self):
        """Return the limits object."""
        return self._limits

    @limits.setter
    def limits(self, input_limits):
        """Set the limits to input_limits."""
        self._limits = input_limits

    def set_refresh(self, value):
        """Set the plugin refresh rate"""
        self.set_limits('refresh', value)

    def get_refresh(self):
        """Return the plugin refresh time"""
        ret = self.get_limits(item='refresh')
        if ret is None:
            ret = self.args.time
        return ret

    def get_refresh_time(self):
        """Return the plugin refresh time"""
        return self.get_refresh()

    def set_limits(self, item, value):
        """Set the limits object."""
        self._limits['{}_{}'.format(self.plugin_name, item)] = value

    def get_limits(self, item=None):
        """Return the limits object."""
        if item is None:
            return self._limits
        else:
            return self._limits.get('{}_{}'.format(self.plugin_name, item), None)

    def get_stats_action(self):
        """Return stats for the action.

        By default return all the stats.
        Can be overwrite by plugins implementation.
        For example, Docker will return self.stats['containers']
        """
        return self.stats

    def get_stat_name(self, header=""):
        """ "Return the stat name with an optional header"""
        ret = self.plugin_name
        if header != "":
            ret += '_' + header
        return ret

    def get_alert(
        self,
        current=0,
        minimum=0,
        maximum=100,
        highlight_zero=True,
        is_max=False,
        header="",
        action_key=None,
        log=False,
    ):
        """Return the alert status relative to a current value.

        Use this function for minor stats.

        If current < CAREFUL of max then alert = OK
        If current > CAREFUL of max then alert = CAREFUL
        If current > WARNING of max then alert = WARNING
        If current > CRITICAL of max then alert = CRITICAL

        If highlight=True than 0.0 is highlighted

        If defined 'header' is added between the plugin name and the status.
        Only useful for stats with several alert status.

        If defined, 'action_key' define the key for the actions.
        By default, the action_key is equal to the header.

        If log=True than add log if necessary
        elif log=False than do not log
        elif log=None than apply the config given in the conf file
        """
        # Manage 0 (0.0) value if highlight_zero is not True
        if not highlight_zero and current == 0:
            return 'DEFAULT'

        # Compute the %
        try:
            value = (current * 100) / maximum
        except ZeroDivisionError:
            return 'DEFAULT'
        except TypeError:
            return 'DEFAULT'

        # Build the stat_name
        stat_name = self.get_stat_name(header=header)

        # Manage limits
        # If is_max is set then display the value in MAX
        ret = 'MAX' if is_max else 'OK'
        try:
            if value >= self.get_limit('critical', stat_name=stat_name):
                ret = 'CRITICAL'
            elif value >= self.get_limit('warning', stat_name=stat_name):
                ret = 'WARNING'
            elif value >= self.get_limit('careful', stat_name=stat_name):
                ret = 'CAREFUL'
            elif current < minimum:
                ret = 'CAREFUL'
        except KeyError:
            return 'DEFAULT'

        # Manage log
        log_str = ""
        if self.get_limit_log(stat_name=stat_name, default_action=log):
            # Add _LOG to the return string
            # So stats will be highlighted with a specific color
            log_str = "_LOG"
            # Add the log to the list
            glances_events.add(ret, stat_name.upper(), value)

        # Manage threshold
        self.manage_threshold(stat_name, ret)

        # Manage action
        self.manage_action(stat_name, ret.lower(), header, action_key)

        # Default is 'OK'
        return ret + log_str

    def manage_threshold(self, stat_name, trigger):
        """Manage the threshold for the current stat."""
        glances_thresholds.add(stat_name, trigger)

    def manage_action(self, stat_name, trigger, header, action_key):
        """Manage the action for the current stat."""
        # Here is a command line for the current trigger ?
        try:
            command, repeat = self.get_limit_action(trigger, stat_name=stat_name)
        except KeyError:
            # Reset the trigger
            self.actions.set(stat_name, trigger)
        else:
            # Define the action key for the stats dict
            # If not define, then it sets to header
            if action_key is None:
                action_key = header

            # A command line is available for the current alert
            # 1) Build the {{mustache}} dictionary
            if isinstance(self.get_stats_action(), list):
                # If the stats are stored in a list of dict (fs plugin for example)
                # Return the dict for the current header
                mustache_dict = {}
                for item in self.get_stats_action():
                    if item[self.get_key()] == action_key:
                        mustache_dict = item
                        break
            else:
                # Use the stats dict
                mustache_dict = self.get_stats_action()
            # 2) Run the action
            self.actions.run(stat_name, trigger, command, repeat, mustache_dict=mustache_dict)

    def get_alert_log(self, current=0, minimum=0, maximum=100, header="", action_key=None):
        """Get the alert log."""
        return self.get_alert(
            current=current, minimum=minimum, maximum=maximum, header=header, action_key=action_key, log=True
        )

    def is_limit(self, criticality, stat_name=""):
        """Return true if the criticality limit exist for the given stat_name"""
        if stat_name == "":
            return self.plugin_name + '_' + criticality in self._limits
        else:
            return stat_name + '_' + criticality in self._limits

    def get_limit(self, criticality, stat_name=""):
        """Return the limit value for the alert."""
        # Get the limit for stat + header
        # Example: network_wlan0_rx_careful
        try:
            limit = self._limits[stat_name + '_' + criticality]
        except KeyError:
            # Try fallback to plugin default limit
            # Example: network_careful
            limit = self._limits[self.plugin_name + '_' + criticality]

        # logger.debug("{} {} value is {}".format(stat_name, criticality, limit))

        # Return the limiter
        return limit

    def get_limit_action(self, criticality, stat_name=""):
        """Return the tuple (action, repeat) for the alert.

        - action is a command line
        - repeat is a bool
        """
        # Get the action for stat + header
        # Example: network_wlan0_rx_careful_action
        # Action key available ?
        ret = [
            (stat_name + '_' + criticality + '_action', False),
            (stat_name + '_' + criticality + '_action_repeat', True),
            (self.plugin_name + '_' + criticality + '_action', False),
            (self.plugin_name + '_' + criticality + '_action_repeat', True),
        ]
        for r in ret:
            if r[0] in self._limits:
                return self._limits[r[0]], r[1]

        # No key found, the raise an error
        raise KeyError

    def get_limit_log(self, stat_name, default_action=False):
        """Return the log tag for the alert."""
        # Get the log tag for stat + header
        # Example: network_wlan0_rx_log
        try:
            log_tag = self._limits[stat_name + '_log']
        except KeyError:
            # Try fallback to plugin default log
            # Example: network_log
            try:
                log_tag = self._limits[self.plugin_name + '_log']
            except KeyError:
                # By default, log are disabled
                return default_action

        # Return the action list
        return log_tag[0].lower() == 'true'

    def get_conf_value(self, value, header="", plugin_name=None, default=[]):
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
            return default

    def is_show(self, value, header=""):
        """Return True if the value is in the show configuration list.

        If the show value is empty, return True (show by default)

        The show configuration list is defined in the glances.conf file.
        It is a comma separated list of regexp.
        Example for diskio:
        show=sda.*
        """
        # @TODO: possible optimisation: create a re.compile list
        return any(
            j for j in [re.fullmatch(i.lower(), value.lower()) for i in self.get_conf_value('show', header=header)]
        )

    def is_hide(self, value, header=""):
        """Return True if the value is in the hide configuration list.

        The hide configuration list is defined in the glances.conf file.
        It is a comma separated list of regexp.
        Example for diskio:
        hide=sda2,sda5,loop.*
        """
        # @TODO: possible optimisation: create a re.compile list
        return any(
            j for j in [re.fullmatch(i.lower(), value.lower()) for i in self.get_conf_value('hide', header=header)]
        )

    def is_display(self, value, header=""):
        """Return True if the value should be displayed in the UI"""
        if self.get_conf_value('show', header=header) != []:
            return self.is_show(value, header=header)
        else:
            return not self.is_hide(value, header=header)

    def has_alias(self, header):
        """Return the alias name for the relative header it it exists otherwise None."""
        try:
            # Force to lower case (issue #1126)
            return self._limits[self.plugin_name + '_' + header.lower() + '_' + 'alias'][0]
        except (KeyError, IndexError):
            # logger.debug("No alias found for {}".format(header))
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
            ret = {'display': display_curse, 'msgdict': self.msg_curse(args, max_width=max_width), 'align': align_curse}
        else:
            ret = {'display': display_curse, 'msgdict': self.msg_curse(args), 'align': align_curse}

        return ret

    def curse_add_line(self, msg, decoration="DEFAULT", optional=False, additional=False, splittable=False):
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
                WARNING: Value is WARNING and non logged
                WARNING_LOG: Value is WARNING and logged
                CRITICAL: Value is CRITICAL and non logged
                CRITICAL_LOG: Value is CRITICAL and logged
            optional: True if the stat is optional (display only if space is available)
            additional: True if the stat is additional (display only if space is available after optional)
            spittable: Line can be split to fit on the screen (default is not)
        """
        return {
            'msg': msg,
            'decoration': decoration,
            'optional': optional,
            'additional': additional,
            'splittable': splittable,
        }

    def curse_new_line(self):
        """Go to a new line."""
        return self.curse_add_line('\n')

    def curse_add_stat(self, key, width=None, header='', display_key=True, separator='', trailer=''):
        """Return a list of dict messages with the 'key: value' result

          <=== width ===>
        __key     : 80.5%__
        | |       | |    |_ trailer
        | |       | |_ self.stats[key]
        | |       |_ separator
        | |_ 'short_name' description or key or nothing if display_key is True
        |_ header

        Instead of:
            msg = '  {:8}'.format('idle:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='idle', option='optional')))
            msg = '{:5.1f}%'.format(self.stats['idle'])
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='idle', option='optional')))

        Use:
            ret.extend(self.curse_add_stat('idle', width=15, header='  '))

        """
        if key not in self.stats:
            return []

        # Check if a shortname is defined
        if not display_key:
            key_name = ''
        elif key in self.fields_description and 'short_name' in self.fields_description[key]:
            key_name = self.fields_description[key]['short_name']
        else:
            key_name = key

        # Check if unit is defined and get the short unit char in the unit_sort dict
        if (
            key in self.fields_description
            and 'unit' in self.fields_description[key]
            and self.fields_description[key]['unit'] in fields_unit_short
        ):
            # Get the shortname
            unit_short = fields_unit_short[self.fields_description[key]['unit']]
        else:
            unit_short = ''

        # Check if unit is defined and get the unit type unit_type dict
        if (
            key in self.fields_description
            and 'unit' in self.fields_description[key]
            and self.fields_description[key]['unit'] in fields_unit_type
        ):
            # Get the shortname
            unit_type = fields_unit_type[self.fields_description[key]['unit']]
        else:
            unit_type = 'float'

        # Is it a rate ? Yes, compute it thanks to the time_since_update key
        if (
            key in self.fields_description
            and 'rate' in self.fields_description[key]
            and self.fields_description[key]['rate'] is True
        ):
            value = self.stats[key] // self.stats['time_since_update']
        else:
            value = self.stats[key]

        if width is None:
            msg_item = header + '{}'.format(key_name) + separator
            msg_template_float = '{:.1f}{}'
            msg_template = '{}{}'
        else:
            # Define the size of the message
            # item will be on the left
            # value will be on the right
            msg_item = header + '{:{width}}'.format(key_name, width=width - 7) + separator
            msg_template_float = '{:5.1f}{}'
            msg_template = '{:>5}{}'

        if unit_type == 'float':
            msg_value = msg_template_float.format(value, unit_short) + trailer
        elif 'min_symbol' in self.fields_description[key]:
            msg_value = (
                msg_template.format(
                    self.auto_unit(int(value), min_symbol=self.fields_description[key]['min_symbol']), unit_short
                )
                + trailer
            )
        else:
            msg_value = msg_template.format(int(value), unit_short) + trailer

        decoration = self.get_views(key=key, option='decoration')
        optional = self.get_views(key=key, option='optional')

        return [
            self.curse_add_line(msg_item, optional=optional),
            self.curse_add_line(msg_value, decoration=decoration, optional=optional),
        ]

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

    def auto_unit(self, number, low_precision=False, min_symbol='K'):
        """Make a nice human-readable string out of number.

        Number of decimal places increases as quantity approaches 1.
        CASE: 613421788        RESULT:       585M low_precision:       585M
        CASE: 5307033647       RESULT:      4.94G low_precision:       4.9G
        CASE: 44968414685      RESULT:      41.9G low_precision:      41.9G
        CASE: 838471403472     RESULT:       781G low_precision:       781G
        CASE: 9683209690677    RESULT:      8.81T low_precision:       8.8T
        CASE: 1073741824       RESULT:      1024M low_precision:      1024M
        CASE: 1181116006       RESULT:      1.10G low_precision:       1.1G

        :low_precision: returns less decimal places potentially (default is False)
                        sacrificing precision for more readability.
        :min_symbol: Do not approach if number < min_symbol (default is K)
        """
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        if min_symbol in symbols:
            symbols = symbols[symbols.index(min_symbol) :]
        prefix = {
            'Y': 1208925819614629174706176,
            'Z': 1180591620717411303424,
            'E': 1152921504606846976,
            'P': 1125899906842624,
            'T': 1099511627776,
            'G': 1073741824,
            'M': 1048576,
            'K': 1024,
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
                return '{:.{decimal}f}{symbol}'.format(value, decimal=decimal_precision, symbol=symbol)
        return '{!s}'.format(number)

    def trend_msg(self, trend, significant=1):
        """Return the trend message.

        Do not take into account if trend < significant
        """
        ret = '-'
        if trend is None or not PY3:
            ret = ' '
        elif trend > significant:
            ret = unicode_message('ARROW_UP', self.args)
        elif trend < -significant:
            ret = unicode_message('ARROW_DOWN', self.args)
        return ret

    def _check_decorator(fct):
        """Check decorator for update method.

        It checks:
        - if the plugin is enabled.
        - if the refresh_timer is finished
        """

        def wrapper(self, *args, **kw):
            if self.is_enabled() and (self.refresh_timer.finished() or self.stats == self.get_init_value):
                # Run the method
                ret = fct(self, *args, **kw)
                # Reset the timer
                self.refresh_timer.set(self.get_refresh())
                self.refresh_timer.reset()
            else:
                # No need to call the method
                # Return the last result available
                ret = self.stats
            return ret

        return wrapper

    def _log_result_decorator(fct):
        """Log (DEBUG) the result of the function fct."""

        def wrapper(*args, **kw):
            counter = Counter()
            ret = fct(*args, **kw)
            duration = counter.get()
            logger.debug(
                "%s %s %s return %s in %s seconds"
                % (
                    args[0].__class__.__name__,
                    args[0].__class__.__module__[len('glances_') :],
                    fct.__name__,
                    ret,
                    duration,
                )
            )
            return ret

        return wrapper

    # Mandatory to call the decorator in child classes
    _check_decorator = staticmethod(_check_decorator)
    _log_result_decorator = staticmethod(_log_result_decorator)
