#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the servers list used in TUI and WEBUI Central Browser mode"""

from glances.servers_list_dynamic import GlancesAutoDiscoverServer
from glances.servers_list_static import GlancesStaticServer


class GlancesServersList:
    def __init__(self, config=None, args=None):
        # Store the arg/config
        self.args = args
        self.config = config

        # Init the servers list defined in the Glances configuration file
        self.static_server = None
        self.load()

        # Init the dynamic servers list by starting a Zeroconf listener
        self.autodiscover_server = None
        if not self.args.disable_autodiscover:
            self.autodiscover_server = GlancesAutoDiscoverServer()

    def load(self):
        """Load server and password list from the configuration file."""
        # Init the static server list
        self.static_server = GlancesStaticServer(config=self.config)

    def get_servers_list(self):
        """Return the current server list (list of dict).

        Merge of static + autodiscover servers list.
        """
        ret = []

        if self.args.browser:
            ret = self.static_server.get_servers_list()
            if self.autodiscover_server is not None:
                ret = self.static_server.get_servers_list() + self.autodiscover_server.get_servers_list()

        return ret

    def get_columns(self):
        return self.static_server.get_columns()

    def set_in_selected(self, selected, key, value):
        """Set the (key, value) for the selected server in the list."""
        # Static list then dynamic one
        if selected >= len(self.static_server.get_servers_list()):
            self.autodiscover_server.set_server(selected - len(self.static_server.get_servers_list()), key, value)
        else:
            self.static_server.set_server(selected, key, value)
