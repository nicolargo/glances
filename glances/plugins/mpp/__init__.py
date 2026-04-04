#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""MPP (Media Process Platform) plugin for Glances.

Currently supported:
- Rockchip MPP (RKVENC, RKVDEC, RKJPEGD)
"""

from glances.logger import logger
from glances.plugins.mpp.cards.rockchip_mpp import RockchipMPP
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
fields_description = {
    'engine_id': {
        'description': 'Engine identification',
    },
    'name': {
        'description': 'Engine name',
    },
    'type': {
        'description': 'Engine type (encoder/decoder/jpeg)',
    },
    'load': {
        'description': 'Engine load',
        'unit': 'percent',
    },
    'utilization': {
        'description': 'Engine utilization',
        'unit': 'percent',
    },
    'sessions': {
        'description': 'Number of active sessions',
    },
}

# Define the history items list
items_history_list = [
    {'name': 'load', 'description': 'MPP engine load', 'y_unit': '%'},
]


class MppPlugin(GlancesPluginModel):
    """Glances MPP plugin.

    stats is a list of dictionaries with one entry per MPP engine.
    """

    def __init__(
        self,
        args=None,
        config=None,
        rockchip_mpp_root_folder: str = '/',
    ):
        """Init the plugin."""
        super().__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            stats_init_value=[],
            fields_description=fields_description,
        )

        self.rockchip = RockchipMPP(mpp_root_folder=rockchip_mpp_root_folder)

        # We want to display the stat in the curse interface
        self.display_curse = True

    def exit(self):
        """Overwrite the exit method."""
        self.rockchip.exit()
        super().exit()

    def get_key(self):
        """Return the key of the list."""
        return 'engine_id'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the MPP stats."""
        stats = self.get_init_value()

        if self.rockchip.is_available():
            try:
                engine_stats = self.rockchip.get_stats()
                stats.extend(engine_stats)
            except Exception as e:
                logger.debug(f"Error getting Rockchip MPP stats, disabling: {e}")
                self.rockchip.disable()

        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        super().update_views()

        for i in self.stats:
            self.views[i[self.get_key()]] = {'load': {}}
            if 'load' in i and i['load'] is not None:
                alert = self.get_alert(i['load'], header='load')
                self.views[i[self.get_key()]]['load']['decoration'] = alert

        return True

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        ret = []

        if not self.stats or self.is_disabled():
            return ret

        # Header
        ret.append(self.curse_add_line('MPP', 'TITLE'))

        # One line per engine
        for engine in self.stats:
            ret.append(self.curse_new_line())

            # Engine name and type (e.g. "RKVENC  enc")
            name = engine.get('name', 'unknown')
            etype = engine.get('type', '')
            label = f'{name:<8}{etype:>5}'
            ret.append(self.curse_add_line(label))

            # Load percentage
            load = engine.get('load')
            if load is not None:
                msg = f'{load:>6.1f}%'
                ret.append(
                    self.curse_add_line(
                        msg,
                        self.get_views(
                            key='load',
                            item=engine[self.get_key()],
                            option='decoration',
                        ),
                    )
                )
            else:
                ret.append(self.curse_add_line('{:>7}'.format('N/A')))

            # Session count
            sessions = engine.get('sessions', 0)
            if sessions:
                msg = f'  {sessions} sess'
                ret.append(self.curse_add_line(msg))

        return ret
