# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""Common objects shared by all Glances modules."""

import errno
import os
import sys
import platform

# OS constants (some libraries/features are OS-dependent)
BSD = sys.platform.find('bsd') != -1
LINUX = sys.platform.startswith('linux')
MACOS = sys.platform.startswith('darwin')
SUNOS = sys.platform.startswith('sunos')
WINDOWS = sys.platform.startswith('win')
WSL = "linux" in platform.system().lower() and "microsoft" in platform.uname()[3].lower()

# Set the AMPs, plugins and export modules path
work_path = os.path.realpath(os.path.dirname(__file__))
amps_path = os.path.realpath(os.path.join(work_path, 'amps'))
plugins_path = os.path.realpath(os.path.join(work_path, 'plugins'))
exports_path = os.path.realpath(os.path.join(work_path, 'exports'))
sys_path = sys.path[:]
sys.path.insert(1, exports_path)
sys.path.insert(1, plugins_path)
sys.path.insert(1, amps_path)


def safe_makedirs(path):
    """A safe function for creating a directory tree."""
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            if not os.path.isdir(path):
                raise
        else:
            raise
