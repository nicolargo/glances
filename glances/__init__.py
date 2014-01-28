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

# Import Glances libs
# Note: others Glances libs will be imported optionnaly
from .core.glances_main import GlancesMain

def main(argv=None):
    # Create the Glances main instance
    core = GlancesMain()

    # Glances can be ran in standalone, client or server mode
    if (core.is_standalone()):
        # !!!
        print "Standalone mode"
    elif (core.is_client()):
        # !!!
        print "Client mode"
    elif (core.is_server()):
        # Import the Glances server module
        from .core.glances_server import GlancesServer

        # Init the server
        server = GlancesServer(bind_address=core.bind_ip, 
                               bind_port=int(core.server_port), 
                               cached_time=core.cached_time)
        print(_("Glances server is running on") + " %s:%s" % (core.bind_ip, core.server_port))

        # Set the server login/password (if -P/--password tag)
        if (core.password != ""):
            server.add_user(core.username, core.password)

        # Start the server loop
        server.serve_forever()

        # Shutdown the server
        # !!! How to close the server with CTRL-C
        # !!! Call core.end() with parameters ?
        server.server_close()





