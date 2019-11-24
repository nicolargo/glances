# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""RAID plugin."""

from glances.compat import iterkeys
from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin

# Import plugin specific dependency
try:
    from pymdstat import MdStat
except ImportError as e:
    import_error_tag = True
    logger.warning("Missing Python Lib ({}), Raid plugin is disabled".format(e))
else:
    import_error_tag = False


class Plugin(GlancesPlugin):
    """Glances RAID plugin.

    stats is a dict (see pymdstat documentation)
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update RAID stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if import_error_tag:
            return self.stats

        if self.input_method == 'local':
            # Update stats using the PyMDstat lib (https://github.com/nicolargo/pymdstat)
            try:
                # Just for test
                # mds = MdStat(path='/home/nicolargo/dev/pymdstat/tests/mdstat.10')
                mds = MdStat()
                stats = mds.get_stats()['arrays']
            except Exception as e:
                logger.debug("Can not grab RAID stats (%s)" % e)
                return self.stats

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # No standard way for the moment...
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if not self.stats or self.is_disable():
            return ret

        # Max size for the interface name
        name_max_width = max_width - 12

        # Header
        msg = '{:{width}}'.format('RAID disks',
                                  width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = '{:>7}'.format('Used')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('Avail')
        ret.append(self.curse_add_line(msg))
        # Data
        arrays = sorted(iterkeys(self.stats))
        for array in arrays:
            # New line
            ret.append(self.curse_new_line())
            # Display the current status
            status = self.raid_alert(self.stats[array]['status'],
                                     self.stats[array]['used'],
                                     self.stats[array]['available'],
                                     self.stats[array]['type'])
            # Data: RAID type name | disk used | disk available
            array_type = self.stats[array]['type'].upper() if self.stats[array]['type'] is not None else 'UNKNOWN'
            # Build the full name = array type + array name
            full_name = '{} {}'.format(array_type, array)
            msg = '{:{width}}'.format(full_name,
                                      width=name_max_width)
            ret.append(self.curse_add_line(msg))
            if self.stats[array]['type'] == 'raid0' and self.stats[array]['status'] == 'active':
                msg = '{:>7}'.format(len(self.stats[array]['components']))
                ret.append(self.curse_add_line(msg, status))
                msg = '{:>7}'.format('-')
                ret.append(self.curse_add_line(msg, status))
            elif self.stats[array]['status'] == 'active':
                msg = '{:>7}'.format(self.stats[array]['used'])
                ret.append(self.curse_add_line(msg, status))
                msg = '{:>7}'.format(self.stats[array]['available'])
                ret.append(self.curse_add_line(msg, status))
            elif self.stats[array]['status'] == 'inactive':
                ret.append(self.curse_new_line())
                msg = '└─ Status {}'.format(self.stats[array]['status'])
                ret.append(self.curse_add_line(msg, status))
                components = sorted(iterkeys(self.stats[array]['components']))
                for i, component in enumerate(components):
                    if i == len(components) - 1:
                        tree_char = '└─'
                    else:
                        tree_char = '├─'
                    ret.append(self.curse_new_line())
                    msg = '   {} disk {}: '.format(tree_char, self.stats[array]['components'][component])
                    ret.append(self.curse_add_line(msg))
                    msg = '{}'.format(component)
                    ret.append(self.curse_add_line(msg))
            if self.stats[array]['type'] != 'raid0' and (self.stats[array]['used'] < self.stats[array]['available']):
                # Display current array configuration
                ret.append(self.curse_new_line())
                msg = '└─ Degraded mode'
                ret.append(self.curse_add_line(msg, status))
                if len(self.stats[array]['config']) < 17:
                    ret.append(self.curse_new_line())
                    msg = '   └─ {}'.format(self.stats[array]['config'].replace('_', 'A'))
                    ret.append(self.curse_add_line(msg))

        return ret

    def raid_alert(self, status, used, available, type):
        """RAID alert messages.

        [available/used] means that ideally the array may have _available_
        devices however, _used_ devices are in use.
        Obviously when used >= available then things are good.
        """
        if type == 'raid0':
            return 'OK'
        if status == 'inactive':
            return 'CRITICAL'
        if used is None or available is None:
            return 'DEFAULT'
        elif used < available:
            return 'WARNING'
        return 'OK'
