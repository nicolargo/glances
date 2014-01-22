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
    Glances's memory Plugin

    stats is a dict
    """

    def __init__(self):
        GlancesPlugin.__init__(self)


    def update(self):
        """
        Update MEM (RAM) stats
        """

        # RAM
        # psutil >= 0.6
        if hasattr(psutil, 'virtual_memory'):
            phymem = psutil.virtual_memory()

            # buffers and cached (Linux, BSD)
            buffers = getattr(phymem, 'buffers', 0)
            cached = getattr(phymem, 'cached', 0)

            # active and inactive not available on Windows
            active = getattr(phymem, 'active', 0)
            inactive = getattr(phymem, 'inactive', 0)

            # phymem free and usage
            total = phymem.total
            free = phymem.available  # phymem.free + buffers + cached
            used = total - free

            self.stats = {'total': total,
                          'percent': phymem.percent,
                          'used': used,
                          'free': free,
                          'active': active,
                          'inactive': inactive,
                          'buffers': buffers,
                          'cached': cached}

        # psutil < 0.6
        elif hasattr(psutil, 'phymem_usage'):
            phymem = psutil.phymem_usage()

            # buffers and cached (Linux, BSD)
            buffers = getattr(psutil, 'phymem_buffers', 0)()
            cached = getattr(psutil, 'cached_phymem', 0)()

            # phymem free and usage
            total = phymem.total
            free = phymem.free + buffers + cached
            used = total - free

            # active and inactive not available for psutil < 0.6
            self.stats = {'total': total,
                          'percent': phymem.percent,
                          'used': used,
                          'free': free,
                          'buffers': buffers,
                          'cached': cached}
        else:
            self.stats = {}
