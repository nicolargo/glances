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

from glances import psutil_version_info
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """Get the psutil version for client/server purposes.

    stats is a tuple
    """

    def __init__(self, args=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)

        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = None

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the stats."""
        # Reset stats
        self.reset()

        # Return PsUtil version as a tuple
        if self.input_method == 'local':
            # PsUtil version only available in local
            try:
                self.stats = psutil_version_info
            except NameError:
                pass
        else:
            pass

        return self.stats
