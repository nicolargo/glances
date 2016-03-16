# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""Folder plugin."""

from glances.folder_list import FolderList as glancesFolderList
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances folder plugin."""

    def __init__(self, args=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.glances_folders = None
        self.reset()

    def get_key(self):
        """Return the key of the list."""
        return 'path'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    def load_limits(self, config):
        """Load the foldered list from the config file, if it exists."""
        self.glances_folders = glancesFolderList(config)

    def update(self):
        """Update the foldered list."""
        # Reset the list
        self.reset()

        if self.input_method == 'local':
            # Folder list only available in a full Glances environment
            # Check if the glances_folder instance is init
            if self.glances_folders is None:
                return self.stats

            # Update the foldered list (result of command)
            self.glances_folders.update()

            # Put it on the stats var
            self.stats = self.glances_folders.get()
        else:
            pass

        return self.stats

    def get_alert(self, stat):
        """Manage limits of the folder list"""

        if stat['size'] is None:
            return 'DEFAULT'
        else:
            ret = 'OK'

        if stat['critical'] is not None and stat['size'] > int(stat['critical']) * 1000000:
            ret = 'CRITICAL'
        elif stat['warning'] is not None and stat['size'] > int(stat['warning']) * 1000000:
            ret = 'WARNING'
        elif stat['careful'] is not None and stat['size'] > int(stat['careful']) * 1000000:
            ret = 'CAREFUL'

        return ret

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_folder:
            return ret

        # Build the string message
        # Header
        msg = '{0}'.format('FOLDERS')
        ret.append(self.curse_add_line(msg, "TITLE"))

        # Data
        for i in self.stats:
            ret.append(self.curse_new_line())
            if len(i['path']) > 15:
                # Cut path if it is too long
                path = '_' + i['path'][-15 + 1:]
            else:
                path = i['path']
            msg = '{0:<16} '.format(path)
            ret.append(self.curse_add_line(msg))
            try:
                msg = '{0:>6}'.format(self.auto_unit(i['size']))
            except TypeError:
                msg = '{0:>6}'.format('?')
            ret.append(self.curse_add_line(msg, self.get_alert(i)))

        return ret
