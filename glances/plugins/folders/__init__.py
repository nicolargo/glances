#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Folder plugin."""

from glances.folder_list import FolderList as glancesFolderList
from glances.globals import nativestr
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'path': {'description': 'Absolute path.'},
    'size': {
        'description': 'Folder size in bytes.',
        'unit': 'byte',
    },
    'refresh': {
        'description': 'Refresh interval in seconds.',
        'unit': 'second',
    },
    'errno': {
        'description': 'Return code when retrieving folder size (0 is no error).',
        'unit': 'number',
    },
    'careful': {
        'description': 'Careful threshold in MB.',
        'unit': 'megabyte',
    },
    'warning': {
        'description': 'Warning threshold in MB.',
        'unit': 'megabyte',
    },
    'critical': {
        'description': 'Critical threshold in MB.',
        'unit': 'megabyte',
    },
}


class PluginModel(GlancesPluginModel):
    """Glances folder plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[], fields_description=fields_description)

        self.args = args
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.glances_folders = glancesFolderList(config)

    def get_key(self):
        """Return the key of the list."""
        return 'path'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the folders list."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Folder list only available in a full Glances environment
            # Check if the glances_folder instance is init
            if self.glances_folders is None:
                return self.stats

            # Update the folders list (result of command)
            self.glances_folders.update(key=self.get_key())

            # Put it on the stats var
            stats = self.glances_folders.get()
        else:
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def get_alert(self, stat, header=""):
        """Manage limits of the folder list."""
        if stat['errno'] != 0:
            ret = 'ERROR'
        else:
            ret = 'OK'

            if stat['critical'] is not None and stat['size'] > int(stat['critical']) * 1000000:
                ret = 'CRITICAL'
            elif stat['warning'] is not None and stat['size'] > int(stat['warning']) * 1000000:
                ret = 'WARNING'
            elif stat['careful'] is not None and stat['size'] > int(stat['careful']) * 1000000:
                ret = 'CAREFUL'

        # Get stat name
        stat_name = self.get_stat_name(header=header)

        # Manage threshold
        self.manage_threshold(stat_name, ret)

        # Manage action
        self.manage_action(stat_name, ret.lower(), header, stat[self.get_key()])

        return ret

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        if max_width:
            name_max_width = max_width - 7
        else:
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        # Header
        msg = '{:{width}}'.format('FOLDERS', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))

        # Data
        for i in self.stats:
            ret.append(self.curse_new_line())
            if len(i['path']) > name_max_width:
                # Cut path if it is too long
                path = '_' + i['path'][-name_max_width + 1 :]
            else:
                path = i['path']
            msg = '{:{width}}'.format(nativestr(path), width=name_max_width)
            ret.append(self.curse_add_line(msg))
            if i['errno'] != 0:
                msg = '?{:>8}'.format(self.auto_unit(i['size']))
            else:
                msg = '{:>9}'.format(self.auto_unit(i['size']))
            ret.append(self.curse_add_line(msg, self.get_alert(i, header='folder_' + i['indice'])))

        return ret
