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

"""Virtual memory plugin."""

from glances.plugins.plugin.view import GlancesPluginView


class Plugin(GlancesPluginView):
    """Glances' memory plugin view.

    view is a dict
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        # Add specifics informations
        # Alert and log
        self.views['percent']['decoration'] = self.get_alert_log(self.stats['used'], maximum=self.stats['total'])
        # Optional
        for key in ['active', 'inactive', 'buffers', 'cached']:
            if key in self.stats:
                self.views[key]['optional'] = True

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disabled
        if not self.stats or self.is_disable():
            return ret

        # First line
        # total% + active
        msg = '{}'.format('MEM')
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' {:2}'.format(self.trend_msg(self.get_trend('percent')))
        ret.append(self.curse_add_line(msg))
        # Percent memory usage
        msg = '{:>7.1%}'.format(self.stats['percent'] / 100)
        ret.append(self.curse_add_line(
            msg, self.get_views(key='percent', option='decoration')))
        # Active memory usage
        ret.extend(self.curse_add_stat('active', width=18, header='  '))

        # Second line
        # total + inactive
        ret.append(self.curse_new_line())
        # Total memory usage
        ret.extend(self.curse_add_stat('total', width=15))
        # Inactive memory usage
        ret.extend(self.curse_add_stat('inactive', width=18, header='  '))

        # Third line
        # used + buffers
        ret.append(self.curse_new_line())
        # Used memory usage
        ret.extend(self.curse_add_stat('used', width=15))
        # Buffers memory usage
        ret.extend(self.curse_add_stat('buffers', width=18, header='  '))

        # Fourth line
        # free + cached
        ret.append(self.curse_new_line())
        # Free memory usage
        ret.extend(self.curse_add_stat('free', width=15))
         # Cached memory usage
        ret.extend(self.curse_add_stat('cached', width=18, header='  '))

        return ret
