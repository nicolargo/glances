#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""RAID plugin."""

from glances.globals import iterkeys
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Import plugin specific dependency
try:
    from pymdstat import MdStat
except ImportError as e:
    import_error_tag = True
    logger.warning(f"Missing Python Lib ({e}), Raid plugin is disabled")
else:
    import_error_tag = False


class PluginModel(GlancesPluginModel):
    """Glances RAID plugin.

    stats is a dict (see pymdstat documentation)
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update RAID stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if import_error_tag:
            return self.stats

        if self.input_method == 'local':
            # Update stats using the PyMDstat lib (https://github.com/nicolargo/pymdstat)
            try:
                mds = MdStat()
                # Just for test: uncomment the following line to use a local file
                # mds = MdStat(path='/home/nicolargo/dev/pymdstat/tests/mdstat.10')
                stats = mds.get_stats()['arrays']
            except Exception as e:
                logger.debug(f"Can not grab RAID stats ({e})")
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
        if not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        if max_width:
            name_max_width = max_width - 12
        else:
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        # Header
        msg = '{:{width}}'.format('RAID disks', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = '{:>7}'.format('Used')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('Avail')
        ret.append(self.curse_add_line(msg))
        # Data
        arrays = sorted(iterkeys(self.stats))
        for array in arrays:
            array_stats = self.stats[array]

            if not isinstance(array_stats, dict):
                continue

            # Display the current status
            status = self.raid_alert(
                array_stats['status'],
                array_stats['used'],
                array_stats['available'],
                array_stats['type'],
            )

            # New line
            ret.append(self.curse_new_line())
            # Data: RAID type name | disk used | disk available
            array_type = array_stats['type'].upper() if array_stats['type'] is not None else 'UNKNOWN'
            # Build the full name = array type + array name
            full_name = f'{array_type} {array}'
            msg = '{:{width}}'.format(full_name, width=name_max_width)
            ret.append(self.curse_add_line(msg))
            if array_stats['type'] == 'raid0' and array_stats['status'] == 'active':
                msg = '{:>7}'.format(len(array_stats['components']))
                ret.append(self.curse_add_line(msg, status))
                msg = '{:>7}'.format('-')
                ret.append(self.curse_add_line(msg, status))
            elif array_stats['status'] == 'active':
                msg = '{:>7}'.format(array_stats['used'])
                ret.append(self.curse_add_line(msg, status))
                msg = '{:>7}'.format(array_stats['available'])
                ret.append(self.curse_add_line(msg, status))
            elif array_stats['status'] == 'inactive':
                ret.append(self.curse_new_line())
                msg = '└─ Status {}'.format(array_stats['status'])
                ret.append(self.curse_add_line(msg, status))
                components = sorted(iterkeys(array_stats['components']))
                for i, component in enumerate(components):
                    if i == len(components) - 1:
                        tree_char = '└─'
                    else:
                        tree_char = '├─'
                    ret.append(self.curse_new_line())
                    msg = '   {} disk {}: '.format(tree_char, array_stats['components'][component])
                    ret.append(self.curse_add_line(msg))
                    msg = f'{component}'
                    ret.append(self.curse_add_line(msg))

            if array_stats['type'] != 'raid0' and (
                array_stats['used'] and array_stats['available'] and array_stats['used'] < array_stats['available']
            ):
                # Display current array configuration
                ret.append(self.curse_new_line())
                msg = '└─ Degraded mode'
                ret.append(self.curse_add_line(msg, status))
                if len(array_stats['config']) < 17:
                    ret.append(self.curse_new_line())
                    msg = '   └─ {}'.format(array_stats['config'].replace('_', 'A'))
                    ret.append(self.curse_add_line(msg))

        return ret

    @staticmethod
    def raid_alert(status, used, available, raid_type) -> str:
        """RAID alert messages.

        [available/used] means that ideally the array may have _available_
        devices however, _used_ devices are in use.
        Obviously when used >= available then things are good.
        """
        if raid_type == 'raid0':
            return 'OK'
        if status == 'inactive':
            return 'CRITICAL'
        if used is None or available is None:
            return 'DEFAULT'
        if used < available:
            return 'WARNING'
        return 'OK'
