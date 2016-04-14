# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""Monitor plugin."""

from glances.compat import iteritems
from glances.amps_list import AmpsList as glancesAmpsList
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances AMPs plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)
        self.args = args
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the list of AMP (classe define in the glances/amps_list.py script)
        self.glances_amps = glancesAmpsList(self.args, self.config)

        # Init stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the AMP list."""
        # Reset stats
        self.reset()

        if self.input_method == 'local':
            # TODO
            for k, v in iteritems(self.glances_amps.update()):
                self.stats.append({k: v.result()})
        else:
            pass

        return self.stats

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        # Only process if stats exist and display plugin enable...
        ret = []

        if not self.stats or args.disable_process:
            return ret

        # Build the string message
        for m in self.stats:
            for k, v in iteritems(m):
                msg = '{0:<16} '.format(k)
                ret.append(self.curse_add_line(msg))
                msg = '{0}'.format(v.replace('\n', ''))
                ret.append(self.curse_add_line(msg, splittable=True))
            ret.append(self.curse_new_line())

        # Delete the last empty line
        try:
            ret.pop()
        except IndexError:
            pass

        return ret
