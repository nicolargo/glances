#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""RAID plugin."""

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


class RaidPlugin(GlancesPluginModel):
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
        ret = []

        if not self.stats or self.is_disabled():
            return ret

        if not max_width:
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        name_max_width = max_width - 12

        # Header
        msg = '{:{width}}'.format('RAID disks', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        ret.append(self.curse_add_line('{:>7}'.format('Used')))
        ret.append(self.curse_add_line('{:>7}'.format('Avail')))

        # Data
        for array in sorted(self.stats.keys()):
            array_stats = self.stats[array]
            if isinstance(array_stats, dict):
                ret.extend(self._msg_curse_array(array, array_stats, name_max_width))

        return ret

    def _msg_curse_array(self, array, array_stats, name_max_width):
        """Return curse lines for a single RAID array."""
        ret = []

        status = self.raid_alert(
            array_stats['status'],
            array_stats['used'],
            array_stats['available'],
            array_stats['type'],
        )

        array_type = array_stats['type'].upper() if array_stats['type'] is not None else 'UNKNOWN'
        full_name = f'{array_type} {array}'

        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line('{:{width}}'.format(full_name, width=name_max_width)))

        if array_stats['type'] == 'raid0' and array_stats['status'] == 'active':
            ret.extend(self._msg_curse_raid0_active(array_stats, status))
        elif array_stats['status'] == 'active':
            ret.extend(self._msg_curse_active(array_stats, status))
        elif array_stats['status'] == 'inactive':
            ret.extend(self._msg_curse_inactive(array_stats, status))

        ret.extend(self._msg_curse_degraded(array_stats, status))

        return ret

    def _msg_curse_raid0_active(self, array_stats, status):
        """Return curse lines for an active RAID-0 array."""
        return [
            self.curse_add_line('{:>7}'.format(len(array_stats['components'])), status),
            self.curse_add_line('{:>7}'.format('-'), status),
        ]

    def _msg_curse_active(self, array_stats, status):
        """Return curse lines for a non-RAID-0 active array."""
        return [
            self.curse_add_line('{:>7}'.format(array_stats['used']), status),
            self.curse_add_line('{:>7}'.format(array_stats['available']), status),
        ]

    def _msg_curse_inactive(self, array_stats, status):
        """Return curse lines for an inactive array with component listing."""
        ret = [
            self.curse_new_line(),
            self.curse_add_line('└─ Status {}'.format(array_stats['status']), status),
        ]
        components = sorted(array_stats['components'].keys())
        for i, component in enumerate(components):
            tree_char = '└─' if i == len(components) - 1 else '├─'
            ret.append(self.curse_new_line())
            ret.append(self.curse_add_line('   {} disk {}: '.format(tree_char, array_stats['components'][component])))
            ret.append(self.curse_add_line(f'{component}'))
        return ret

    def _msg_curse_degraded(self, array_stats, status):
        """Return curse lines when a non-RAID-0 array is in degraded mode."""
        ret = []
        if array_stats['type'] != 'raid0' and (
            array_stats['used'] and array_stats['available'] and array_stats['used'] < array_stats['available']
        ):
            ret.append(self.curse_new_line())
            ret.append(self.curse_add_line('└─ Degraded mode', status))
            if len(array_stats['config']) < 17:
                ret.append(self.curse_new_line())
                ret.append(self.curse_add_line('   └─ {}'.format(array_stats['config'].replace('_', 'A'))))
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
