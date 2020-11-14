# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2020 Nicolargo <nicolas@nicolargo.com>
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
# Version should start and end with a numerical char
# See https://packaging.python.org/specifications/core-metadata/#version
__version__ = '3.1.6_b1'
__author__ = 'Nicolas Hennion <nicolas@nicolargo.com>'
__license__ = 'LGPLv3'

# Import psutil
try:
    from psutil import __version__ as psutil_version
except ImportError:
    print('psutil library not found. Glances cannot start.')
    sys.exit(1)

# Import Glances libs
# Note: others Glances libs will be imported optionally
from glances.logger import logger
from glances.main import GlancesMain
from glances.globals import WINDOWS
from glances.timer import Counter
# Check locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    print("Warning: Unable to set locale. Expect encoding problems.")

# Check Python version
if sys.version_info < (2, 7) or (3, 0) <= sys.version_info < (3, 4):
    print('Glances requires at least Python 2.7 or 3.4 to run.')
    sys.exit(1)

# Check psutil version
psutil_min_version = (5, 3, 0)
psutil_version_info = tuple([int(num) for num in psutil_version.split('.')])
if psutil_version_info < psutil_min_version:
    print('psutil 5.3.0 or higher is needed. Glances cannot start.')
    sys.exit(1)


def __signal_handler(signal, frame):
    """Callback for CTRL-C."""
    end()


def end():
    """Stop Glances."""
    try:
        mode.end()
    except NameError:
        # NameError: name 'mode' is not defined in case of interrupt shortly...
        # ...after starting the server mode (issue #1175)
        pass

    logger.info("Glances stopped (keypressed: CTRL-C)")

    # The end...
    sys.exit(0)


def start(config, args):
    """Start Glances."""

    # Load mode
    global mode

    start_duration = Counter()

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
    logger.debug("Glances started in {} seconds".format(start_duration.get()))
    mode.serve_forever()

    # Shutdown
    mode.end()


def main():
    """Main entry point for Glances.

    Select the mode (standalone, client or server)
    Run it...
    """
    # Catch the CTRL-C signal
    signal.signal(signal.SIGINT, __signal_handler)

    # Log Glances and psutil version
    logger.info('Start Glances {}'.format(__version__))
    logger.info('{} {} and psutil {} detected'.format(
        platform.python_implementation(),
        platform.python_version(),
        psutil_version))

    # Share global var
    global core

    # Create the Glances main instance
    core = GlancesMain()
    config = core.get_config()
    args = core.get_args()

    # Glances can be ran in standalone, client or server mode
    start(config=config, args=args)
