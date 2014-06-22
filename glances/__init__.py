# -*- coding: utf-8 -*-
#
# This file is part of Glances.
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

"""Init the Glances software."""

__appname__ = 'glances'
__version__ = '2.0.1'
__author__ = 'Nicolas Hennion <nicolas@nicolargo.com>'
__license__ = 'LGPL'

# Import system lib
import gettext
import locale
import signal
import sys

# Import psutil
try:
    from psutil import __version__ as __psutil_version
except ImportError:
    print('psutil library not found. Glances cannot start.')
    sys.exit(1)

# Check psutil version
psutil_min_version = (2, 0, 0)
psutil_version = tuple([int(num) for num in __psutil_version.split('.')])
if psutil_version < psutil_min_version:
    print('psutil version {0} detected.').format(__psutil_version)
    print('psutil 2.0 or higher is needed. Glances cannot start.')
    sys.exit(1)

# Import Glances libs
# Note: others Glances libs will be imported optionally
from glances.core.glances_globals import gettext_domain, locale_dir
from glances.core.glances_main import GlancesMain


def __signal_handler(signal, frame):
    """Callback for CTRL-C."""
    end()


def end():
    """Stop Glances."""
    if core.is_standalone():
        # Stop the standalone (CLI)
        standalone.end()
    elif core.is_client():
        # Stop the client
        client.end()
    elif core.is_server():
        # Stop the server
        server.end()

    # The end...
    sys.exit(0)


def main():
    """Main entry point for Glances.

    Select the mode (standalone, client or server)
    Run it...
    """
    # Setup translations
    locale.setlocale(locale.LC_ALL, '')
    gettext.install(gettext_domain, locale_dir)

    # Share global var
    global core, standalone, client, server

    # Create the Glances main instance
    core = GlancesMain()

    # Catch the CTRL-C signal
    signal.signal(signal.SIGINT, __signal_handler)

    # Glances can be ran in standalone, client or server mode
    if core.is_standalone():

        # Import the Glances standalone module
        from glances.core.glances_standalone import GlancesStandalone

        # Init the standalone mode
        standalone = GlancesStandalone(config=core.get_config(),
                                       args=core.get_args())

        # Start the standalone (CLI) loop
        standalone.serve_forever()

    elif core.is_client():

        # Import the Glances client module
        from glances.core.glances_client import GlancesClient

        # Init the client
        client = GlancesClient(config=core.get_config(),
                               args=core.get_args())

        # Test if client and server are in the same major version
        if not client.login():
            print(_("Error: The server version is not compatible with the client"))
            sys.exit(2)

        # Start the client loop
        client.serve_forever()

        # Shutdown the client
        client.close()

    elif core.is_server():

        # Import the Glances server module
        from glances.core.glances_server import GlancesServer

        args = core.get_args()

        server = GlancesServer(cached_time=core.cached_time,
                               config=core.get_config(),
                               args=args)
        print(_("Glances server is running on {0}:{1}").format(args.bind_address, args.port))

        # Set the server login/password (if -P/--password tag)
        if args.password != "":
            server.add_user(args.username, args.password)

        # Start the server loop
        server.serve_forever()

        # Shutdown the server?
        server.server_close()

    elif core.is_webserver():

        # Import the Glances web server module
        from glances.core.glances_webserver import GlancesWebServer

        # Init the web server mode
        webserver = GlancesWebServer(config=core.get_config(),
                                     args=core.get_args())

        # Start the web server loop
        webserver.serve_forever()
