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
__version__ = '2.10'
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
    mode.end()
    logger.info("Glances stopped with CTRL-C")

    # The end...
    sys.exit(0)


def start(config, args):
    """Start Glances"""

    # Load mode
    global mode

    if core.is_standalone():
        from glances.standalone import GlancesStandalone as GlancesMode
    elif core.is_client():
        if core.is_client_browser():
            from glances.client_browser import GlancesClientBrowser as GlancesMode
        else:
            from glances.client import GlancesClient as GlancesMode
    elif core.is_server():
        from glances.server import GlancesServer as GlancesMode
    elif core.is_webserver():
        from glances.webserver import GlancesWebServer as GlancesMode

    # Init the mode
    logger.info("Start {} mode".format(GlancesMode.__name__))
    mode = GlancesMode(config=config, args=args)

    # Start the main loop
    mode.serve_forever()

    # Shutdown
    mode.end()


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
    start(config=config, args=args)
