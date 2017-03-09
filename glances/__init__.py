# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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
#

"""Init the Glances software."""

# Import system libs
import locale
import platform
import signal
import sys

# Global name
__version__ = '2.8.3'
__author__ = 'Nicolas Hennion <nicolas@nicolargo.com>'
__license__ = 'LGPLv3'

# Import psutil
try:
    from psutil import __version__ as psutil_version
except ImportError:
    print('PSutil library not found. Glances cannot start.')
    sys.exit(1)

# Import Glances libs
# Note: others Glances libs will be imported optionally
from glances.logger import logger
from glances.main import GlancesMain
from glances.globals import WINDOWS

# Check locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    print("Warning: Unable to set locale. Expect encoding problems.")

# Check Python version
if sys.version_info < (2, 7) or (3, 0) <= sys.version_info < (3, 3):
    print('Glances requires at least Python 2.7 or 3.3 to run.')
    sys.exit(1)

# Check PSutil version
psutil_min_version = (2, 0, 0)
psutil_version_info = tuple([int(num) for num in psutil_version.split('.')])
if psutil_version_info < psutil_min_version:
    print('PSutil 2.0 or higher is needed. Glances cannot start.')
    sys.exit(1)


def __signal_handler(signal, frame):
    """Callback for CTRL-C."""
    end()


def end():
    """Stop Glances."""
    if core.is_standalone():
        # Stop the standalone (CLI)
        standalone.end()
        logger.info("Stop Glances (with CTRL-C)")
    elif core.is_client():
        # Stop the client
        client.end()
        logger.info("Stop Glances client (with CTRL-C)")
    elif core.is_server():
        # Stop the server
        server.end()
        logger.info("Stop Glances server (with CTRL-C)")
    elif core.is_webserver() or core.is_standalone():
        # Stop the Web server
        webserver.end()
        logger.info("Stop Glances web server(with CTRL-C)")

    # The end...
    sys.exit(0)


def start_standalone(config, args):
    """Start the standalone mode"""
    logger.info("Start standalone mode")

    # Share global var
    global standalone

    # Import the Glances standalone module
    from glances.standalone import GlancesStandalone

    # Init the standalone mode
    standalone = GlancesStandalone(config=config, args=args)

    # Start the standalone (CLI) loop
    standalone.serve_forever()


def start_clientbrowser(config, args):
    """Start the browser client mode"""
    logger.info("Start client mode (browser)")

    # Share global var
    global client

    # Import the Glances client browser module
    from glances.client_browser import GlancesClientBrowser

    # Init the client
    client = GlancesClientBrowser(config=config, args=args)

    # Start the client loop
    client.serve_forever()

    # Shutdown the client
    client.end()


def start_client(config, args):
    """Start the client mode"""
    logger.info("Start client mode")

    # Share global var
    global client

    # Import the Glances client browser module
    from glances.client import GlancesClient

    # Init the client
    client = GlancesClient(config=config, args=args)

    # Test if client and server are in the same major version
    if not client.login():
        logger.critical("The server version is not compatible with the client")
        sys.exit(2)

    # Start the client loop
    client.serve_forever()

    # Shutdown the client
    client.end()


def start_server(config, args):
    """Start the server mode"""
    logger.info("Start server mode")

    # Share global var
    global server

    # Import the Glances server module
    from glances.server import GlancesServer

    server = GlancesServer(cached_time=args.cached_time,
                           config=config,
                           args=args)
    print('Glances server is running on {}:{}'.format(args.bind_address, args.port))

    # Set the server login/password (if -P/--password tag)
    if args.password != "":
        server.add_user(args.username, args.password)

    # Start the server loop
    server.serve_forever()

    # Shutdown the server?
    server.server_close()


def start_webserver(config, args):
    """Start the Web server mode"""
    logger.info("Start web server mode")

    # Share global var
    global webserver

    # Import the Glances web server module
    from glances.webserver import GlancesWebServer

    # Init the web server mode
    webserver = GlancesWebServer(config=config, args=args)

    # Start the web server loop
    webserver.serve_forever()


def main():
    """Main entry point for Glances.

    Select the mode (standalone, client or server)
    Run it...
    """
    # Log Glances and PSutil version
    logger.info('Start Glances {}'.format(__version__))
    logger.info('{} {} and PSutil {} detected'.format(
        platform.python_implementation(),
        platform.python_version(),
        psutil_version))

    # Share global var
    global core

    # Create the Glances main instance
    core = GlancesMain()
    config = core.get_config()
    args = core.get_args()

    # Catch the CTRL-C signal
    signal.signal(signal.SIGINT, __signal_handler)

    # Glances can be ran in standalone, client or server mode
    if core.is_standalone():
        start_standalone(config=config, args=args)
    elif core.is_client() and not WINDOWS:
        if core.is_client_browser():
            start_clientbrowser(config=config, args=args)
        else:
            start_client(config=config, args=args)
    elif core.is_server():
        start_server(config=config, args=args)
    elif core.is_webserver():
        # Web server mode replace the standalone mode on Windows OS
        # In this case, try to start the web browser mode automaticaly
        if WINDOWS:
            args.open_web_browser = True
        start_webserver(config=config, args=args)
