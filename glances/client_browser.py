#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances client browser (list of Glances server)."""

import webbrowser

from glances.client import GlancesClient
from glances.logger import LOG_FILENAME, logger
from glances.outputs.glances_curses_browser import GlancesCursesBrowser
from glances.servers_list import GlancesServersList


class GlancesClientBrowser:
    """This class creates and manages the TCP client browser (servers list)."""

    def __init__(self, config=None, args=None):
        # Store the arg/config
        self.args = args
        self.config = config

        # Init the server list
        self.servers_list = GlancesServersList(config=config, args=args)

        # Init screen
        self.screen = GlancesCursesBrowser(args=self.args)

    def __display_server(self, server):
        """Connect and display the given server"""
        # Display the Glances client for the selected server
        logger.debug(f"Selected server {server}")

        if server['protocol'].lower() == 'rest':
            # Display a popup
            self.screen.display_popup(
                'Open the WebUI {}:{} in a Web Browser'.format(server['name'], server['port']), duration=1
            )
            # Try to open a Webbrowser
            webbrowser.open(self.servers_list.get_uri(server), new=2, autoraise=1)
            self.screen.active_server = None
            return

        # Connection can take time
        # Display a popup
        self.screen.display_popup('Connect to {}:{}'.format(server['name'], server['port']), duration=1)

        # A password is needed to access to the server's stats
        if server['password'] is None:
            # First of all, check if a password is available in the [passwords] section
            clear_password = self.servers_list.password.get_password(server['name'])
            if (
                clear_password is None
                or self.servers_list.get_servers_list()[self.screen.active_server]['status'] == 'PROTECTED'
            ):
                # Else, the password should be enter by the user
                # Display a popup to enter password
                clear_password = self.screen.display_popup(
                    'Password needed for {}: '.format(server['name']), popup_type='input', is_password=True
                )
            # Store the password for the selected server
            if clear_password is not None:
                self.set_in_selected('password', self.servers_list.password.get_hash(clear_password))

        # Display the Glance client on the selected server
        logger.info("Connect Glances client to the {} server".format(server['key']))

        # Init the client
        args_server = self.args

        # Overwrite connection setting
        args_server.client = server['ip']
        args_server.port = server['port']
        args_server.username = server['username']
        args_server.password = server['password']
        client = GlancesClient(config=self.config, args=args_server, return_to_browser=True)

        # Test if client and server are in the same major version
        if not client.login():
            self.screen.display_popup(
                "Sorry, cannot connect to '{}'\n" "See '{}' for more details".format(server['name'], LOG_FILENAME)
            )

            # Set the ONLINE status for the selected server
            self.set_in_selected('status', 'OFFLINE')
        else:
            # Start the client loop
            # Return connection type: 'glances' or 'snmp'
            connection_type = client.serve_forever()

            try:
                logger.debug("Disconnect Glances client from the {} server".format(server['key']))
            except IndexError:
                # Server did not exist anymore
                pass
            else:
                # Set the ONLINE status for the selected server
                if connection_type == 'snmp':
                    self.set_in_selected('status', 'SNMP')
                else:
                    self.set_in_selected('status', 'ONLINE')

        # Return to the browser (no server selected)
        self.screen.active_server = None

    def __serve_forever(self):
        """Main client loop."""
        # No need to update the server list
        while not self.screen.is_end:
            # Update the stats in the servers list
            self.servers_list.update_servers_stats()

            if self.screen.active_server is None:
                # Display Glances browser (servers list)
                self.screen.update(self.servers_list.get_servers_list())
            else:
                # Display selected Glances server
                self.__display_server(self.servers_list.get_servers_list()[self.screen.active_server])

    def serve_forever(self):
        """Wrapper to the serve_forever function.

        This function will restore the terminal to a sane state
        before re-raising the exception and generating a traceback.
        """
        try:
            return self.__serve_forever()
        finally:
            self.end()

    def set_in_selected(self, key, value):
        """Set the (key, value) for the selected server in the list."""
        self.servers_list.set_in_selected(self.screen.active_server, key, value)

    def end(self):
        """End of the client browser session."""
        self.screen.end()
