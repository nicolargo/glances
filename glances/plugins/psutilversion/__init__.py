#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""psutil plugin.
Just a simple plugin to get the Psutil version."""

from glances import psutil_version_info
from glances.plugins.plugin.model import GlancesPluginModel


class PluginModel(GlancesPluginModel):
    """Get the Psutil version.

    stats is a string
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config)

        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = None

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the stats."""
        # Reset stats
        self.reset()

        # Return psutil version as a tuple
        if self.input_method == 'local':
            # psutil version only available in local
            try:
                self.stats = '.'.join([str(i) for i in psutil_version_info])
            except NameError:
                pass
        else:
            pass

        return self.stats
