#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#
#

"""Init the Glances software."""

# Import system libs
import locale
import sys

# Global name
# Version should start and end with a numerical char
# See https://packaging.python.org/specifications/core-metadata/#version
# Examples: 1.0.0, 1.0.0rc1, 1.1.0_dev1
__version__ = "5.0.0b1"
__apiversion__ = "5"
__author__ = 'Nicolas Hennion <nicolas@nicolargo.com>'
__license__ = 'LGPLv3'

# Import psutil
try:
    from psutil import __version__ as psutil_version
except ImportError:
    print('psutil library not found. Glances cannot start.')
    sys.exit(1)

# Check locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    print("Warning: Unable to set locale. Expect encoding problems.")

# Check psutil version
psutil_min_version = (5, 3, 0)
psutil_version_info = tuple([int(num) for num in psutil_version.split('.')])
if psutil_version_info < psutil_min_version:
    print('psutil 5.3.0 or higher is needed. Glances cannot start.')
    sys.exit(1)


def main():
    """Main entry point for Glances (the `glances` command and `python -m glances`)."""
    from glances.main import main as run

    sys.exit(run())


# End of glances/__init__.py
