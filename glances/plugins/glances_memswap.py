#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

# Import system libs
# Check for PSUtil already done in the glances_core script
import psutil

# from ..plugins.glances_plugin import GlancesPlugin
from glances_plugin import GlancesPlugin

class Plugin(GlancesPlugin):
    """
    Glances's swap memory Plugin

    stats is a dict
    """

    def __init__(self):
        GlancesPlugin.__init__(self)


    def update(self):
        """
        Update MEM (SWAP) stats
        """

        # SWAP
        # psutil >= 0.6
        if hasattr(psutil, 'swap_memory'):
            # Try... is an hack for issue #152
            try:
                virtmem = psutil.swap_memory()
            except Exception:
                self.stats = {}
            else:
                self.stats = {'total': virtmem.total,
                              'used': virtmem.used,
                              'free': virtmem.free,
                              'percent': virtmem.percent}

        # psutil < 0.6
        elif hasattr(psutil, 'virtmem_usage'):
            virtmem = psutil.virtmem_usage()
            self.stats = {'total': virtmem.total,
                          'used': virtmem.used,
                          'free': virtmem.free,
                          'percent': virtmem.percent}
        else:
            self.stats = {}
