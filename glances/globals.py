# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Common objects shared by all Glances modules."""

import errno
import os
import sys
import platform
import ujson
from operator import itemgetter

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


def json_dumps(data):
    """Return the object data in a JSON format.

    Manage the issue #815 for Windows OS with UnicodeDecodeError catching.
    """
    try:
        return ujson.dumps(data)
    except UnicodeDecodeError:
        return ujson.dumps(data, ensure_ascii=False)


def json_dumps_dictlist(data, item):
    if isinstance(data, dict):
        try:
            return json_dumps({item: data[item]})
        except:
            return None
    elif isinstance(data, list):
        try:
            # Source:
            # http://stackoverflow.com/questions/4573875/python-get-index-of-dictionary-item-in-list
            # But https://github.com/nicolargo/glances/issues/1401
            return json_dumps({item: list(map(itemgetter(item), data))})
        except:
            return None
    else:
        return None
