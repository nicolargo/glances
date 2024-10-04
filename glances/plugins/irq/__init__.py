#
# This file is part of Glances.
#
# Copyright (C) 2018 Angelo Poerio <angelo.poerio@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""IRQ plugin."""

import operator
import os

from glances.globals import LINUX
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel
from glances.timer import getTimeSinceLastUpdate

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'irq_line': {
        'description': 'IRQ line name',
    },
    'irq_rate': {
        'description': 'IRQ rate per second',
        'unit': 'numberpersecond',
    },
}


class PluginModel(GlancesPluginModel):
    """Glances IRQ plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[], fields_description=fields_description)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.irq = GlancesIRQ()

    def get_key(self):
        """Return the key of the list."""
        return self.irq.get_key()

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the IRQ stats."""
        # Init new stats
        stats = self.get_init_value()

        # IRQ plugin only available on GNU/Linux
        if not LINUX:
            return self.stats

        if self.input_method == 'local':
            # Grab the stats
            stats = self.irq.get()

        elif self.input_method == 'snmp':
            # not available
            pass

        # Get the TOP 5 (by rate/s)
        stats = sorted(stats, key=operator.itemgetter('irq_rate'), reverse=True)[:5]

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only available on GNU/Linux
        # Only process if stats exist and display plugin enable...
        if not LINUX or not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        if max_width:
            name_max_width = max_width - 7
        else:
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        # Build the string message
        # Header
        msg = '{:{width}}'.format('IRQ', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = '{:>9}'.format('Rate/s')
        ret.append(self.curse_add_line(msg))

        for i in self.stats:
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(i['irq_line'][:name_max_width], width=name_max_width)
            ret.append(self.curse_add_line(msg))
            msg = '{:>9}'.format(str(i['irq_rate']))
            ret.append(self.curse_add_line(msg))

        return ret


class GlancesIRQ:
    """This class manages the IRQ file."""

    IRQ_FILE = '/proc/interrupts'

    def __init__(self):
        """Init the class.

        The stat are stored in a internal list of dict
        """
        self.lasts = {}
        self.reset()

    def reset(self):
        """Reset the stats."""
        self.stats = []
        self.cpu_number = 0

    def get(self):
        """Return the current IRQ stats."""
        return self.__update()

    def get_key(self):
        """Return the key of the dict."""
        return 'irq_line'

    def __header(self, line):
        """Build the header (contain the number of CPU).

        CPU0       CPU1       CPU2       CPU3
        0:         21          0          0          0   IO-APIC   2-edge      timer
        """
        self.cpu_number = len(line.split())
        return self.cpu_number

    def __humanname(self, line):
        """Return the IRQ name, alias or number (choose the best for human).

        IRQ line samples:
        1:      44487        341         44         72   IO-APIC   1-edge      i8042
        LOC:   33549868   22394684   32474570   21855077   Local timer interrupts
        """
        splitted_line = line.split()
        irq_line = splitted_line[0].replace(':', '')
        if irq_line.isdigit():
            # If the first column is a digit, use the alias (last column)
            irq_line += f'_{splitted_line[-1]}'
        return irq_line

    def __sum(self, line):
        """Return the IRQ sum number.

        IRQ line samples:
        1:     44487        341         44         72   IO-APIC   1-edge      i8042
        LOC:   33549868   22394684   32474570   21855077   Local timer interrupts
        FIQ:   usb_fiq
        """
        splitted_line = line.split()
        try:
            ret = sum(map(int, splitted_line[1 : (self.cpu_number + 1)]))
        except ValueError:
            # Correct issue #1007 on some conf (Raspberry Pi with Raspbian)
            ret = 0
        return ret

    def __update(self):
        """Load the IRQ file and update the internal dict."""
        self.reset()

        if not os.path.exists(self.IRQ_FILE):
            # Correct issue #947: IRQ file do not exist on OpenVZ container
            return self.stats

        try:
            with open(self.IRQ_FILE) as irq_proc:
                time_since_update = getTimeSinceLastUpdate('irq')
                # Read the header
                self.__header(irq_proc.readline())
                # Read the rest of the lines (one line per IRQ)
                for line in irq_proc.readlines():
                    irq_line = self.__humanname(line)
                    current_irqs = self.__sum(line)
                    irq_rate = int(
                        current_irqs - self.lasts.get(irq_line) if self.lasts.get(irq_line) else 0 // time_since_update
                    )
                    irq_current = {
                        'irq_line': irq_line,
                        'irq_rate': irq_rate,
                        'key': self.get_key(),
                        'time_since_update': time_since_update,
                    }
                    self.stats.append(irq_current)
                    self.lasts[irq_line] = current_irqs
        except OSError:
            pass

        return self.stats
