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
"""
Init the Glances software
"""

# Import system lib
import sys

# Import Glances libs
# Note: others Glances libs will be imported optionnaly
from glances.core.glances_main import GlancesMain


def main():
    # Create the Glances main instance
    core = GlancesMain()

    # Glances can be ran in standalone, client or server mode
    if (core.is_standalone()):

        # Import the Glances standalone module
        from glances.core.glances_standalone import GlancesStandalone

        # Init the standalone mode
        standalone = GlancesStandalone(config=core.get_config(),
                                       args=core.get_args(),
                                       refresh_time=core.refresh_time,
                                       use_bold=core.use_bold)

        # Start the standalone (CLI) loop
        standalone.serve_forever()

    elif (core.is_client()):

        # Import the Glances client module
        from glances.core.glances_client import GlancesClient

        # Init the client
        client = GlancesClient(args=core.get_args(),
                               server_address=core.server_ip, server_port=int(core.server_port),
                               username=core.username, password=core.password, config=core.get_config())

        # Test if client and server are in the same major version
        if (not client.login()):
            print(_("Error: The server version is not compatible with the client"))
            sys.exit(2)

        # Start the client loop
        client.serve_forever()

        # Shutdown the client
        # !!! How to close the server with CTRL-C
        # !!! Call core.end() with parameters ?
        client.close()

    elif (core.is_server()):

        # Import the Glances server module
        from glances.core.glances_server import GlancesServer

        # Init the server
        server = GlancesServer(bind_address=core.bind_ip,
                               bind_port=int(core.server_port),
                               cached_time=core.cached_time,
                               config=core.get_config())
        # print(_("DEBUG: Glances server is running on %s:%s with config file %s") % (core.bind_ip, core.server_port, core.config.get_config_path()))
        print("{} {}:{}".format(_("Glances server is running on"), core.bind_ip, core.server_port))

        # Set the server login/password (if -P/--password tag)
        if (core.password != ""):
            server.add_user(core.username, core.password)

        # Start the server loop
        server.serve_forever()

        # Shutdown the server
        # !!! How to close the server with CTRL-C
        # !!! Call core.end() with parameters ?
        server.server_close()
