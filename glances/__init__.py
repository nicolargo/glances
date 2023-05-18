# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#
#

"""Init the Glances software."""

# Import system libs
import tracemalloc
import locale
import platform
import signal
import sys

# Global name
# Version should start and end with a numerical char
# See https://packaging.python.org/specifications/core-metadata/#version
__version__ = '4.0.0_beta01'
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
from glances.timer import Counter

# Check locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    print("Warning: Unable to set locale. Expect encoding problems.")

# Check Python version
if sys.version_info < (3, 4):
    print('Glances requires at least Python 3.4 to run.')
    sys.exit(1)

# Check psutil version
psutil_min_version = (5, 3, 0)
psutil_version_info = tuple([int(num) for num in psutil_version.split('.')])
if psutil_version_info < psutil_min_version:
    print('psutil 5.3.0 or higher is needed. Glances cannot start.')
    sys.exit(1)

# Trac malloc is only available on Python 3.4 or higher


def __signal_handler(signal, frame):
    logger.debug("Signal {} catched".format(signal))
    end()


def end():
    """Stop Glances."""
    try:
        mode.end()
    except (NameError, KeyError):
        # NameError: name 'mode' is not defined in case of interrupt shortly...
        # ...after starting the server mode (issue #1175)
        pass

    logger.info("Glances stopped gracefully")

    # The end...
    sys.exit(0)


def start(config, args):
    """Start Glances."""

    # Load mode
    global mode

    if args.trace_malloc or args.memory_leak:
        tracemalloc.start()

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
    if args.stop_after:
        logger.info('Glances will be stopped in ~{} seconds'.format(args.stop_after * args.time * args.memory_leak * 2))

    if args.memory_leak:
        print(
            'Memory leak detection, please wait ~{} seconds...'.format(
                args.stop_after * args.time * args.memory_leak * 2
            )
        )
        # First run without dump to fill the memory
        mode.serve_n(args.stop_after)
        # Then start the memory-leak loop
        snapshot_begin = tracemalloc.take_snapshot()

    if args.stdout_issue or args.stdout_apidoc:
        # Serve once for issue/test mode
        mode.serve_issue()
    else:
        # Serve forever
        mode.serve_forever()

    if args.memory_leak:
        snapshot_end = tracemalloc.take_snapshot()
        snapshot_diff = snapshot_end.compare_to(snapshot_begin, 'filename')
        memory_leak = sum([s.size_diff for s in snapshot_diff])
        print("Memory consumption: {0:.1f}KB (see log for details)".format(memory_leak / 1000))
        logger.info("Memory consumption (top 5):")
        for stat in snapshot_diff[:5]:
            logger.info(stat)
    elif args.trace_malloc:
        # See more options here: https://docs.python.org/3/library/tracemalloc.html
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("filename")
        print("[ Trace malloc - Top 10 ]")
        for stat in top_stats[:10]:
            print(stat)

    # Shutdown
    mode.end()


def main():
    """Main entry point for Glances.

    Select the mode (standalone, client or server)
    Run it...
    """
    # SIGHUP not available on Windows (see issue #2408)
    if sys.platform.startswith('win'):
        signal_list = (signal.SIGTERM, signal.SIGINT)
    else:
        signal_list = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
    # Catch the kill signal
    for sig in signal_list:
        signal.signal(sig, __signal_handler)

    # Log Glances and psutil version
    logger.info('Start Glances {}'.format(__version__))
    logger.info(
        '{} {} ({}) and psutil {} detected'.format(
            platform.python_implementation(), platform.python_version(), sys.executable, psutil_version
        )
    )

    # Share global var
    global core

    # Create the Glances main instance
    # Glances options from the command line are read first (in __init__)
    # then the options from the config file (in parse_args)
    core = GlancesMain()

    # Glances can be ran in standalone, client or server mode
    start(config=core.get_config(), args=core.get_args())
