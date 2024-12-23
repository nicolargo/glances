#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
I am your father...

...of all Glances model plugins.
"""

import copy
import re

from glances.actions import GlancesActions
from glances.events_list import glances_events
from glances.globals import dictlist, iterkeys, itervalues, json_dumps, json_dumps_dictlist, listkeys, mean, nativestr
from glances.history import GlancesHistory
from glances.logger import logger
from glances.outputs.glances_unicode import unicode_message
from glances.thresholds import glances_thresholds
from glances.timer import Counter, Timer, getTimeSinceLastUpdate

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


class GlancesPluginModel:
    """Main class for Glances plugin model."""

    def __init__(self, args=None, config=None, items_history_list=None, stats_init_value={}, fields_description=None):
        """Init the plugin of plugins model class.

        All Glances' plugins model should inherit from this class. Most of the
        methods are already implemented in the father classes.

        Your plugin should return a dict or a list of dicts (stored in the
        self.stats). As an example, you can have a look on the mem plugin
        (for dict) or network (for list of dicts).

        From version 4 of the API, the plugin should return a dict.

        A plugin should implement:
        - the reset method: to set your self.stats variable to {} or []
        - the update method: where your self.stats variable is set
        and optionally:
        - the get_key method: set the key of the dict (only for list of dict)
        - all others methods you want to overwrite

        :args: args parameters
        :config: configuration parameters
        :items_history_list: list of items to store in the history
        :stats_init_value: Default value for a stats item
        """
        # Build the plugin name
        # Internal or external module (former prefixed by 'glances.plugins')
        _mod = self.__class__.__module__.replace('glances.plugins.', '')
        self.plugin_name = _mod.split('.')[0]

        if self.plugin_name.startswith('glances_'):
            self.plugin_name = self.plugin_name.split('glances_')[1]
        logger.debug(f"Init {self.plugin_name} plugin")

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
        self._limits = {}
        if config is not None:
            logger.debug(f'Load section {self.plugin_name} in Glances configuration file')
            self.load_limits(config=config)

        # Init the alias (dictionary)
        self.alias = self.read_alias()

        # Init the actions
        self.actions = GlancesActions(args=args)

        # Init the views
        self.views = {}

        # Hide stats if all the hide_zero_fields has never been != 0
        # Default is False, always display stats
        self.hide_zero = False
        # The threshold needed to display a value if hide_zero is true.
        # Only hide a value if it is less than hide_threshold_bytes.
        self.hide_threshold_bytes = 0
        self.hide_zero_fields = []

        # Set the initial refresh time to display stats the first time
        self.refresh_timer = Timer(0)

        # Init stats description
        self.fields_description = fields_description

        # Init the stats
        self.stats_init_value = stats_init_value
        self.time_since_last_update = None
        self.stats = None
        self.stats_previous = None
        self.reset()

    def __repr__(self):
        """Return the raw stats."""
        return str(self.stats)

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
        logger.debug(f"Stop the {self.plugin_name} plugin")

    def get_key(self):
        """Return the key of the list."""
        return

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
            logger.debug(f"Stats history activated for plugin {self.plugin_name} (items: {init_list})")
        return GlancesHistory()

    def reset_stats_history(self):
        """Reset the stats history (dict of GlancesAttribute)."""
        if self.history_enable():
            reset_list = [a['name'] for a in self.get_items_history_list()]
            logger.debug(f"Reset history for plugin {self.plugin_name} (items: {reset_list})")
            self.stats_history.reset()

    def update_stats_history(self):
        """Update stats history."""
        # Build the history
        if not (self.get_export() and self.history_enable()):
            return
        # Itern through items history
        item_name = '' if self.get_key() is None else self.get_key()
        for i in self.get_items_history_list():
            if isinstance(self.get_export(), list):
                # Stats is a list of data
                # Iter through stats (for example, iter through network interface)
                for l_export in self.get_export():
                    if i['name'] in l_export:
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
        if item in s:
            return s[item]
        return None

    def get_export_history(self, item=None):
        """Return the stats history object to export."""
        return self.get_raw_history(item=item)

    def get_stats_history(self, item=None, nb=0):
        """Return the stats history (JSON format)."""
        s = self.stats_history.get_json(nb=nb)

        if item is None:
            return json_dumps(s)

        return json_dumps_dictlist(s, item)

    def get_trend(self, item, nb=30):
        """Get the trend regarding to the last nb values.

        The trend is the diffirence between the mean of the last 0 to nb / 2
        and nb / 2 to nb values.
        """
        raw_history = self.get_raw_history(item=item, nb=nb)
        if raw_history is None or len(raw_history) < nb:
            return None
        last_nb = [v[1] for v in raw_history]
        return mean(last_nb[nb // 2 :]) - mean(last_nb[: nb // 2])

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
        if key is None:
            return self.stats
        try:
            return sorted(
                self.stats,
                key=lambda stat: tuple(
                    int(part) if part.isdigit() else part.lower()
                    for part in re.split(r"(\d+|\D+)", self.has_alias(stat[key]) or stat[key])
                ),
            )
        except TypeError:
            # Correct "Starting an alias with a number causes a crash #1885"
            return sorted(
                self.stats,
                key=lambda stat: tuple(
                    part.lower() for part in re.split(r"(\d+|\D+)", self.has_alias(stat[key]) or stat[key])
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
            snmp_result = snmp_client.getbulk_by_oid(0, 10, *list(itervalues(snmp_oid)))
            logger.info(snmp_result)
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
            snmp_result = snmp_client.get_by_oid(*list(itervalues(snmp_oid)))

            # Build the internal dict with the SNMP result
            for key in iterkeys(snmp_oid):
                ret[key] = snmp_result[snmp_oid[key]]

        return ret

    def get_raw(self):
        """Return the stats object."""
        return self.stats

    def get_export(self):
        """Return the stats object to export.
        By default, return the raw stats.
        Note: this method could be overwritten by the plugin if a specific format is needed (ex: processlist)
        """
        return self.get_raw()

    def get_stats(self):
        """Return the stats object in JSON format."""
        return json_dumps(self.get_raw())

    def get_json(self):
        """Return the stats object in JSON format."""
        return self.get_stats()

    def get_raw_stats_item(self, item):
        """Return the stats object for a specific item in RAW format.

        Stats should be a list of dict (processlist, network...)
        """
        return dictlist(self.get_raw(), item)

    def get_raw_stats_key(self, item, key):
        """Return the stats object for a specific item in RAW format.

        Stats should be a list of dict (processlist, network...)
        """
        return {item: [i for i in self.get_raw() if 'key' in i and i[i['key']] == key][0].get(item)}

    def get_stats_item(self, item):
        """Return the stats object for a specific item in JSON format.

        Stats should be a list of dict (processlist, network...)
        """
        return json_dumps_dictlist(self.get_raw(), item)

    def get_raw_stats_value(self, item, value):
        """Return the stats object for a specific item=value.

        Return None if the item=value does not exist
        Return None if the item is not a list of dict
        """
        if not isinstance(self.get_raw(), list):
            return None

        if (not isinstance(value, int) and not isinstance(value, float)) and value.isdigit():
            value = int(value)
        try:
            return {value: [i for i in self.get_raw() if i[item] == value]}
        except (KeyError, ValueError) as e:
            logger.error(f"Cannot get item({item})=value({value}) ({e})")
            return None

    def get_stats_value(self, item, value):
        """Return the stats object for a specific item=value in JSON format.

        Stats should be a list of dict (processlist, network...)
        """
        rsv = self.get_raw_stats_value(item, value)
        if rsv is None:
            return None
        return json_dumps(rsv)

    def get_item_info(self, item, key, default=None):
        """Return the item info grabbed into self.fields_description."""
        if self.fields_description is None or item not in self.fields_description:
            return default
        return self.fields_description[item].get(key, default)

    def update_views(self):
        """Update the stats views.

        The V of MVC
        A dict of dict with the needed information to display the stats.
        Example for the stat xxx:
        'xxx': {'decoration': 'DEFAULT',  >>> The decoration of the stats
                'optional': False,        >>> Is the stat optional
                'additional': False,      >>> Is the stat provide additional information
                'splittable': False,      >>> Is the stat can be cut (like process lon name)
                'hidden': False}          >>> Is the stats should be hidden in the UI
        """
        ret = {}

        if isinstance(self.get_raw(), list) and self.get_raw() is not None and self.get_key() is not None:
            # Stats are stored in a list of dict (ex: DISKIO, NETWORK, FS...)
            for i in self.get_raw():
                key = i[self.get_key()]
                ret[key] = {}
                for field in listkeys(i):
                    value = {
                        'decoration': 'DEFAULT',
                        'optional': False,
                        'additional': False,
                        'splittable': False,
                    }
                    # Manage the hidden feature
                    # Allow to automatically hide fields when values is never different than 0
                    # Refactoring done for #2929
                    if not self.hide_zero:
                        value['hidden'] = False
                    elif key in self.views and field in self.views[key] and 'hidden' in self.views[key][field]:
                        value['hidden'] = self.views[key][field]['hidden']
                        if field in self.hide_zero_fields and i[field] > self.hide_threshold_bytes:
                            value['hidden'] = False
                    else:
                        value['hidden'] = field in self.hide_zero_fields
                    ret[key][field] = value
        elif isinstance(self.get_raw(), dict) and self.get_raw() is not None:
            # Stats are stored in a dict (ex: CPU, LOAD...)
            for field in listkeys(self.get_raw()):
                value = {
                    'decoration': 'DEFAULT',
                    'optional': False,
                    'additional': False,
                    'splittable': False,
                    'hidden': False,
                }
                # Manage the hidden feature
                # Allow to automatically hide fields when values is never different than 0
                # Refactoring done for #2929
                if not self.hide_zero:
                    value['hidden'] = False
                elif field in self.views and 'hidden' in self.views[field]:
                    value['hidden'] = self.views[field]['hidden']
                    if field in self.hide_zero_fields and self.get_raw()[field] >= self.hide_threshold_bytes:
                        value['hidden'] = False
                else:
                    value['hidden'] = field in self.hide_zero_fields
                ret[field] = value

        self.views = ret

        return self.views

    def set_views(self, input_views):
        """Set the views to input_views."""
        self.views = input_views

    def reset_views(self):
        """Reset the views to input_views."""
        self.views = {}

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

        if key is None or key not in item_views:
            return item_views
        if option is None:
            return item_views[key]
        if option in item_views[key]:
            return item_views[key][option]
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
        # TODO: not optimized because this section is loaded for each plugin...
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
                logger.debug(f"Load limit: {limit} = {self._limits[limit]}")

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
            ret = self.args.time if hasattr(self.args, 'time') else 2
        return ret

    def get_refresh_time(self):
        """Return the plugin refresh time"""
        return self.get_refresh()

    def set_limits(self, item, value):
        """Set the limits object."""
        self._limits[f'{self.plugin_name}_{item}'] = value

    def get_limits(self, item=None):
        """Return the limits object."""
        if item is None:
            return self._limits
        return self._limits.get(f'{self.plugin_name}_{item}', None)

    def get_stats_action(self):
        """Return stats for the action.

        By default return all the stats.
        Can be overwrite by plugins implementation.
        For example, Docker will return self.stats['containers']
        """
        return self.stats

    def get_stat_name(self, header=""):
        """Return the stat name with an optional header"""
        ret = self.plugin_name
        if header != '':
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
        stat_name = self.get_stat_name(header=header).lower()

        # Manage limits
        # If is_max is set then default style is set to MAX else default is set to OK
        ret = 'MAX' if is_max else 'OK'

        # Iter through limits
        critical = self.get_limit('critical', stat_name=stat_name)
        warning = self.get_limit('warning', stat_name=stat_name)
        careful = self.get_limit('careful', stat_name=stat_name)
        if critical and value >= critical:
            ret = 'CRITICAL'
        elif warning and value >= warning:
            ret = 'WARNING'
        elif careful and value >= careful:
            ret = 'CAREFUL'
        elif not careful and not warning and not critical:
            ret = 'DEFAULT'
        else:
            ret = 'OK'

        if current < minimum:
            ret = 'CAREFUL'

        # Manage log
        log_str = ""
        if self.get_limit_log(stat_name=stat_name, default_action=log):
            # Add _LOG to the return string
            # So stats will be highlighted with a specific color
            log_str = "_LOG"
            # Add the log to the events list
            glances_events.add(ret, stat_name.upper(), value)

        # Manage threshold
        self.manage_threshold(stat_name, ret)

        # Manage action
        self.manage_action(stat_name, ret.lower(), header, action_key)

        # Default is 'OK'
        return ret + log_str

    def filter_stats(self, stats):
        """Filter the stats to keep only the fields we want (the one defined in fields_description)."""
        if hasattr(stats, '_asdict'):
            return {k: v for k, v in stats._asdict().items() if k in self.fields_description}
        if isinstance(stats, dict):
            return {k: v for k, v in stats.items() if k in self.fields_description}
        if isinstance(stats, list):
            return [self.filter_stats(s) for s in stats]
        return stats

    def manage_threshold(self, stat_name, trigger):
        """Manage the threshold for the current stat."""
        glances_thresholds.add(stat_name, trigger)

    def manage_action(self, stat_name, trigger, header, action_key):
        """Manage the action for the current stat."""
        # Here is a command line for the current trigger ?
        command, repeat = self.get_limit_action(trigger, stat_name=stat_name)
        if not command and not repeat:
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
        return self.get_stat_name(stat_name).lower() + '_' + criticality in self._limits

    def get_limit(self, criticality=None, stat_name=""):
        """Return the limit value for the given criticality.
        If criticality is None, return the dict of all the limits."""
        if criticality is None:
            return self._limits

        # Get the limit for stat + header
        # Example: network_wlan0_rx_careful
        stat_name = stat_name.lower()
        if stat_name + '_' + criticality in self._limits:
            return self._limits[stat_name + '_' + criticality]
        if self.plugin_name + '_' + criticality in self._limits:
            return self._limits[self.plugin_name + '_' + criticality]

        return None

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

        # No key found, return None
        return None, None

    def get_limit_log(self, stat_name, default_action=False):
        """Return the log tag for the alert."""
        # Get the log tag for stat + header
        # Example: network_wlan0_rx_log
        if stat_name + '_log' in self._limits:
            return self._limits[stat_name + '_log'][0].lower() == 'true'
        if self.plugin_name + '_log' in self._limits:
            return self._limits[self.plugin_name + '_log'][0].lower() == 'true'
        return default_action

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
        It is a comma-separated list of regexp.
        Example for diskio:
        show=sda.*
        """
        # TODO: possible optimisation: create a re.compile list
        return any(
            j for j in [re.fullmatch(i.lower(), value.lower()) for i in self.get_conf_value('show', header=header)]
        )

    def is_hide(self, value, header=""):
        """Return True if the value is in the hide configuration list.

        The hide configuration list is defined in the glances.conf file.
        It is a comma-separated list of regexp.
        Example for diskio:
        hide=sda2,sda5,loop.*
        """
        # TODO: possible optimisation: create a re.compile list
        return any(
            j for j in [re.fullmatch(i.lower(), value.lower()) for i in self.get_conf_value('hide', header=header)]
        )

    def is_display(self, value, header=""):
        """Return True if the value should be displayed in the UI"""
        if self.get_conf_value('show', header=header) != []:
            return self.is_show(value, header=header)
        return not self.is_hide(value, header=header)

    def read_alias(self):
        if self.plugin_name + '_' + 'alias' in self._limits:
            return {i.split(':')[0].lower(): i.split(':')[1] for i in self._limits[self.plugin_name + '_' + 'alias']}
        return {}

    def has_alias(self, header):
        """Return the alias name for the relative header it it exists otherwise None."""
        return self.alias.get(header, None)

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

        # Is it a rate ? Yes, get the pre-computed rate value
        if (
            key in self.fields_description
            and 'rate' in self.fields_description[key]
            and self.fields_description[key]['rate'] is True
        ):
            value = self.stats.get(key + '_rate_per_sec', None)
        else:
            value = self.stats.get(key, None)

        if width is None:
            msg_item = header + f'{key_name}' + separator
            msg_template_float = '{:.1f}{}'
            msg_template = '{}{}'
        else:
            # Define the size of the message
            # item will be on the left
            # value will be on the right
            msg_item = header + '{:{width}}'.format(key_name, width=width - 7) + separator
            msg_template_float = '{:5.1f}{}'
            msg_template = '{:>5}{}'

        if value is None:
            msg_value = msg_template.format('-', '')
        elif unit_type == 'float':
            msg_value = msg_template_float.format(value, unit_short)
        elif 'min_symbol' in self.fields_description[key]:
            msg_value = msg_template.format(
                self.auto_unit(int(value), min_symbol=self.fields_description[key]['min_symbol']), unit_short
            )
        else:
            msg_value = msg_template.format(int(value), unit_short)

        # Add the trailer
        msg_value = msg_value + trailer

        decoration = self.get_views(key=key, option='decoration') if value is not None else 'DEFAULT'
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

    def auto_unit(self, number, low_precision=False, min_symbol='K', none_symbol='-'):
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
        :decimal_count: if set, force the number of decimal number (default is None)
        """
        if number is None:
            return none_symbol
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

        if number == 0:
            # Avoid 0.0
            return '0'

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
        return f'{number!s}'

    def trend_msg(self, trend, significant=1):
        """Return the trend message.

        Do not take into account if trend < significant
        """
        ret = '-'
        if trend is None:
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
            class_name = args[0].__class__.__name__
            class_module = args[0].__class__.__module__
            logger.debug(f"{class_name} {class_module} {fct.__name__} return {ret} in {duration} seconds")
            return ret

        return wrapper

    def _manage_rate(fct):
        """Manage rate decorator for update method."""

        def compute_rate(self, stat, stat_previous):
            if stat_previous is None:
                return stat

            # 1) set _gauge for all the rate fields
            # 2) compute the _rate_per_sec
            # 3) set the original field to the delta between the current and the previous value
            for field in self.fields_description:
                # For all the field with the rate=True flag
                if 'rate' in self.fields_description[field] and self.fields_description[field]['rate'] is True:
                    # Create a new metadata with the gauge
                    stat['time_since_update'] = self.time_since_last_update
                    stat[field + '_gauge'] = stat[field]
                    if field + '_gauge' in stat_previous and stat[field] and stat_previous[field + '_gauge']:
                        # The stat becomes the delta between the current and the previous value
                        stat[field] = stat[field] - stat_previous[field + '_gauge']
                        # Compute the rate
                        if self.time_since_last_update > 0:
                            stat[field + '_rate_per_sec'] = stat[field] // self.time_since_last_update
                        else:
                            stat[field] = 0
                    else:
                        # Avoid strange rate at the first run
                        stat[field] = 0
            return stat

        def compute_rate_on_list(self, stats, stats_previous):
            if stats_previous is None:
                return stats

            for stat in stats:
                olds = [i for i in stats_previous if i[self.get_key()] == stat[self.get_key()]]
                if len(olds) == 1:
                    compute_rate(self, stat, olds[0])
            return stats

        def wrapper(self, *args, **kw):
            # Call the father method
            stats = fct(self, *args, **kw)

            # Get the time since the last update
            self.time_since_last_update = getTimeSinceLastUpdate(self.plugin_name)

            # Compute the rate
            if isinstance(stats, dict):
                # Stats is a dict
                compute_rate(self, stats, self.stats_previous)
            elif isinstance(stats, list):
                # Stats is a list
                compute_rate_on_list(self, stats, self.stats_previous)

            # Memorized the current stats for next run
            self.stats_previous = copy.deepcopy(stats)

            return stats

        return wrapper

    # Mandatory to call the decorator in child classes
    _check_decorator = staticmethod(_check_decorator)
    _log_result_decorator = staticmethod(_log_result_decorator)
    _manage_rate = staticmethod(_manage_rate)
