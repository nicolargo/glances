# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Angelo Poerio <angelo.poerio@gmail.com>
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

"""IRQ plugin."""

import operator
from glances.globals import LINUX
from glances.timer import getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances IRQ plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        self.lasts = {}

        # Init the stats
        self.reset()

    def get_key(self):
        """Return the key of the list."""
        return 'irq_line'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the IRQ stats"""

        # Reset the list
        self.reset()

        if not LINUX:  # only available on GNU/Linux
            return self.stats

        if self.input_method == 'local':
            with open('/proc/interrupts') as irq_proc:
                time_since_update = getTimeSinceLastUpdate('irq')
                irq_proc.readline()  # skip header line
                for irq_line in irq_proc.readlines():
                    splitted_line = irq_line.split()
                    irq_line = splitted_line[0].replace(':', '')
                    current_irqs = sum([int(count) for count in splitted_line[
                                       1:] if count.isdigit()])  # sum interrupts on all CPUs
                    irq_rate = int(
                        current_irqs -
                        self.lasts.get(irq_line) if self.lasts.get(irq_line) else 0 //
                        time_since_update)
                    irq_current = {
                        'irq_line': irq_line,
                        'irq_rate': irq_rate,
                        'key': self.get_key(),
                        'time_since_update': time_since_update
                    }
                    self.stats.append(irq_current)
                    self.lasts[irq_line] = current_irqs

        elif self.input_method == 'snmp':
            # not available
            pass

        # Update the view
        self.update_views()

        self.stats = sorted(self.stats, key=operator.itemgetter(
            'irq_rate'), reverse=True)[:5]  # top 5 IRQ by rate/s
        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        if not LINUX:  # only available on GNU/Linux
            return ret

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_irq:
            return ret

        if max_width is not None and max_width >= 23:
            irq_max_width = max_width - 14
        else:
            irq_max_width = 9

        # Build the string message
        # Header
        msg = '{:{width}}'.format('IRQ', width=irq_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = '{:>14}'.format('Rate/s')
        ret.append(self.curse_add_line(msg))

        for i in self.stats:
            ret.append(self.curse_new_line())
            msg = '{:>3}'.format(i['irq_line'])
            ret.append(self.curse_add_line(msg))
            msg = '{:>20}'.format(str(i['irq_rate']))
            ret.append(self.curse_add_line(msg))

        return ret
