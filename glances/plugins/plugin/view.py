# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
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

...for all Glances view plugins.
"""

import json

from glances.globals import listkeys
from glances.plugins.plugin.model import fields_unit_short, fields_unit_type


class GlancesPluginView(object):
    """Main class for Glances plugin view."""

    def __init__(self, args=None):
        """Init the plugin of plugins class.

        All Glances' plugins should inherit from this class. Most of the
        methods are already implemented in the father classes.

        Your plugin should return a dict or a list of dicts (stored in the
        self.stats). As an example, you can have a look on the mem plugin
        (for dict) or network (for list of dicts).

        A plugin should implement:
        - the __init__ constructor: define the self.display_curse
        and optionnaly:
        - the update_view method: only if you need to trick your output
        - the msg_curse: define the curse (UI) message (if display_curse is True)
        - all others methods you want to overwrite

        :args: args parameters
        """
        # Init the args
        self.args = args

        # Init the default alignement (for curses)
        self._align = 'left'

        # Init the views
        self.views = dict()

        # Hide stats if all the hide_zero_fields has never been != 0
        # Default is False, always display stats
        self.hide_zero = False
        self.hide_zero_fields = []

    def __repr__(self):
        """Return the raw views."""
        return self.views

    def __str__(self):
        """Return the human-readable views."""
        # TODO: a better method to display views
        return str(self.views)

    def _json_dumps(self, d):
        """Return the object 'd' in a JSON format.

        Manage the issue #815 for Windows OS
        """
        try:
            return json.dumps(d)
        except UnicodeDecodeError:
            return json.dumps(d, ensure_ascii=False)

    def get_raw(self):
        """Return the stats object."""
        return self.views

    def get_export(self):
        """Return the stats object to export."""
        return self.get_raw()

    def update_views_hidden(self):
        """If the self.hide_zero is set then update the hidden field of the view
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
            #                       vvvv
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
                if option in item_views[key]:
                    return item_views[key][option]
                else:
                    return 'DEFAULT'

    def get_json_views(self, item=None, key=None, option=None):
        """Return the views (in JSON)."""
        return self._json_dumps(self.get_views(item, key, option))

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
                WARNING: Value is WARINING and non logged
                WARNING_LOG: Value is WARINING and logged
                CRITICAL: Value is CRITICAL and non logged
                CRITICAL_LOG: Value is CRITICAL and logged
            optional: True if the stat is optional (display only if space is available)
            additional: True if the stat is additional (display only if space is available after optional)
            spittable: Line can be splitted to fit on the screen (default is not)
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

    def curse_add_stat(self, key, width=None, header='', separator='', trailer=''):
        """Return a list of dict messages with the 'key: value' result

          <=== width ===>
        __key     : 80.5%__
        | |       | |    |_ trailer
        | |       | |_ self.stats[key]
        | |       |_ separator
        | |_ key
        |_ trailer

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
        if 'short_name' in self.fields_description[key]:
            key_name = self.fields_description[key]['short_name']
        else:
            key_name = key

        # Check if unit is defined and get the short unit char in the unit_sort dict
        if 'unit' in self.fields_description[key] and self.fields_description[key]['unit'] in fields_unit_short:
            # Get the shortname
            unit_short = fields_unit_short[self.fields_description[key]['unit']]
        else:
            unit_short = ''

        # Check if unit is defined and get the unit type unit_type dict
        if 'unit' in self.fields_description[key] and self.fields_description[key]['unit'] in fields_unit_type:
            # Get the shortname
            unit_type = fields_unit_type[self.fields_description[key]['unit']]
        else:
            unit_type = 'float'

        # Is it a rate ? Yes, compute it thanks to the time_since_update key
        if 'rate' in self.fields_description[key] and self.fields_description[key]['rate'] is True:
            value = self.stats[key] // self.stats['time_since_update']
        else:
            value = self.stats[key]

        if width is None:
            msg_item = header + '{}'.format(key_name) + separator
            if unit_type == 'float':
                msg_value = '{:.1f}{}'.format(value, unit_short) + trailer
            elif 'min_symbol' in self.fields_description[key]:
                msg_value = (
                    '{}{}'.format(
                        self.auto_unit(int(value), min_symbol=self.fields_description[key]['min_symbol']), unit_short
                    )
                    + trailer
                )
            else:
                msg_value = '{}{}'.format(int(value), unit_short) + trailer
        else:
            # Define the size of the message
            # item will be on the left
            # value will be on the right
            msg_item = header + '{:{width}}'.format(key_name, width=width - 7) + separator
            if unit_type == 'float':
                msg_value = '{:5.1f}{}'.format(value, unit_short) + trailer
            elif 'min_symbol' in self.fields_description[key]:
                msg_value = (
                    '{:>5}{}'.format(
                        self.auto_unit(int(value), min_symbol=self.fields_description[key]['min_symbol']), unit_short
                    )
                    + trailer
                )
            else:
                msg_value = '{:>5}{}'.format(int(value), unit_short) + trailer
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
        :min_symbol: Do not approache if number < min_symbol (default is K)
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
        if trend is None:
            ret = ' '
        elif trend > significant:
            ret = '/'
        elif trend < -significant:
            ret = '\\'
        return ret
