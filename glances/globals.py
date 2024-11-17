# ruff: noqa: F401
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Common objects shared by all Glances modules."""

################
# GLOBAL IMPORTS
################

import base64
import errno
import functools
import importlib
import os
import platform
import queue
import re
import subprocess
import sys
import weakref
from collections import OrderedDict
from configparser import ConfigParser, NoOptionError, NoSectionError
from datetime import datetime
from operator import itemgetter, methodcaller
from statistics import mean
from typing import Any, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Prefer faster libs for JSON (de)serialization
# Preference Order: orjson > ujson > json (builtin)
try:
    import orjson as json

    json.dumps = functools.partial(json.dumps, option=json.OPT_NON_STR_KEYS)
except ImportError:
    # Need to log info but importing logger will cause cyclic imports
    pass

if 'json' not in globals():
    try:
        # Note: ujson is not officially supported
        # Available as a fallback to allow orjson's unsupported platforms to use a faster serialization lib
        import ujson as json
    except ImportError:
        import json

    # To allow ujson & json dumps to serialize datetime
    def _json_default(v: Any) -> Any:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    json.dumps = functools.partial(json.dumps, default=_json_default)

##############
# GLOBALS VARS
##############

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

# Types
text_type = str
binary_type = bytes
bool_type = bool
long = int

# Alias errors
PermissionError = OSError

# Alias methods
viewkeys = methodcaller('keys')
viewvalues = methodcaller('values')
viewitems = methodcaller('items')


###################
# GLOBALS FUNCTIONS
###################


def printandflush(string):
    """Print and flush (used by stdout* outputs modules)"""
    print(string, flush=True)


def to_ascii(s):
    """Convert the bytes string to a ASCII string
    Useful to remove accent (diacritics)"""
    if isinstance(s, binary_type):
        return s.decode()
    return s.encode('ascii', 'ignore').decode()


def listitems(d):
    return list(d.items())


def listkeys(d):
    return list(d.keys())


def listvalues(d):
    return list(d.values())


def iteritems(d):
    return iter(d.items())


def iterkeys(d):
    return iter(d.keys())


def itervalues(d):
    return iter(d.values())


def u(s, errors='replace'):
    if isinstance(s, text_type):
        return s
    return s.decode('utf-8', errors=errors)


def b(s, errors='replace'):
    if isinstance(s, binary_type):
        return s
    return s.encode('utf-8', errors=errors)


def nativestr(s, errors='replace'):
    if isinstance(s, text_type):
        return s
    if isinstance(s, (int, float)):
        return s.__str__()
    return s.decode('utf-8', errors=errors)


def system_exec(command):
    """Execute a system command and return the result as a str"""
    try:
        res = subprocess.run(command.split(' '), stdout=subprocess.PIPE).stdout.decode('utf-8')
    except Exception as e:
        res = f'ERROR: {e}'
    return res.rstrip()


def subsample(data, sampling):
    """Compute a simple mean subsampling.

    Data should be a list of numerical itervalues

    Return a subsampled list of sampling length
    """
    if len(data) <= sampling:
        return data
    sampling_length = int(round(len(data) / float(sampling)))
    return [mean(data[s * sampling_length : (s + 1) * sampling_length]) for s in range(0, sampling)]


def time_series_subsample(data, sampling):
    """Compute a simple mean subsampling.

    Data should be a list of set (time, value)

    Return a subsampled list of sampling length
    """
    if len(data) <= sampling:
        return data
    t = [t[0] for t in data]
    v = [t[1] for t in data]
    sampling_length = int(round(len(data) / float(sampling)))
    t_subsampled = [t[s * sampling_length : (s + 1) * sampling_length][0] for s in range(0, sampling)]
    v_subsampled = [mean(v[s * sampling_length : (s + 1) * sampling_length]) for s in range(0, sampling)]
    return list(zip(t_subsampled, v_subsampled))


def to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit."""
    return celsius * 1.8 + 32


def is_admin():
    """
    https://stackoverflow.com/a/19719292
    @return: True if the current user is an 'Admin' whatever that
    means (root on Unix), otherwise False.
    Warning: The inner function fails unless you have Windows XP SP2 or
    higher. The failure causes a traceback to be printed and this
    function to return False.
    """

    if os.name == 'nt':
        import ctypes
        import traceback

        # WARNING: requires Windows XP SP2 or higher!
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            print(f"Admin check failed with error: {e}")
            traceback.print_exc()
            return False
    else:
        # Check for root on Posix
        return os.getuid() == 0


def key_exist_value_not_none(k, d):
    # Return True if:
    # - key k exists
    # - d[k] is not None
    return k in d and d[k] is not None


def key_exist_value_not_none_not_v(k, d, value='', length=None):
    # Return True if:
    # - key k exists
    # - d[k] is not None
    # - d[k] != value
    # - if length is not None and len(d[k]) >= length
    return k in d and d[k] is not None and d[k] != value and (length is None or len(d[k]) >= length)


def disable(class_name, var):
    """Set disable_<var> to True in the class class_name."""
    setattr(class_name, 'enable_' + var, False)
    setattr(class_name, 'disable_' + var, True)


def enable(class_name, var):
    """Set disable_<var> to False in the class class_name."""
    setattr(class_name, 'enable_' + var, True)
    setattr(class_name, 'disable_' + var, False)


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


def get_time_diffs(ref, now):
    if isinstance(ref, int):
        diff = now - datetime.fromtimestamp(ref)
    elif isinstance(ref, datetime):
        diff = now - ref
    elif not ref:
        diff = 0

    return diff


def get_first_true_val(conds):
    return next(key for key, val in conds.items() if val)


def maybe_add_plural(count):
    return "s" if count > 1 else ""


def build_str_when_more_than_seven_days(day_diff, unit):
    scale = {'week': 7, 'month': 30, 'year': 365}[unit]

    count = day_diff // scale

    return str(count) + " " + unit + maybe_add_plural(count)


def pretty_date(ref, now=None):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    Source: https://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python

    Refactoring done in commit https://github.com/nicolargo/glances/commit/f6279baacd4cf0b27ca10df6dc01f091ea86a40a
    break the function. Get back to the old fashion way.
    """
    if not now:
        now = datetime.now()
    if isinstance(ref, int):
        diff = now - datetime.fromtimestamp(ref)
    elif isinstance(ref, datetime):
        diff = now - ref
    elif not ref:
        diff = 0
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " secs"
        if second_diff < 120:
            return "a min"
        if second_diff < 3600:
            return str(second_diff // 60) + " mins"
        if second_diff < 7200:
            return "an hour"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + " days" if day_diff > 1 else "a day"
    if day_diff < 31:
        week = day_diff // 7
        return str(week) + " weeks" if week > 1 else "a week"
    if day_diff < 365:
        month = day_diff // 30
        return str(month) + " months" if month > 1 else "a month"
    year = day_diff // 365
    return str(year) + " years" if year > 1 else "an year"


def urlopen_auth(url, username, password):
    """Open a url with basic auth"""
    return urlopen(
        Request(
            url,
            headers={'Authorization': 'Basic ' + base64.b64encode(f'{username}:{password}'.encode()).decode()},
        )
    )


def json_dumps(data) -> bytes:
    """Return the object data in a JSON format.

    Manage the issue #815 for Windows OS with UnicodeDecodeError catching.
    """
    try:
        res = json.dumps(data)
    except UnicodeDecodeError:
        res = json.dumps(data, ensure_ascii=False)
    # ujson & json libs return strings, but our contract expects bytes
    return b(res)


def json_loads(data: Union[str, bytes, bytearray]) -> Union[dict, list]:
    """Load a JSON buffer into memory as a Python object"""
    return json.loads(data)


def dictlist(data, item):
    if isinstance(data, dict):
        try:
            return {item: data[item]}
        except (TypeError, IndexError, KeyError):
            return None
    elif isinstance(data, list):
        try:
            # Source:
            # http://stackoverflow.com/questions/4573875/python-get-index-of-dictionary-item-in-list
            # But https://github.com/nicolargo/glances/issues/1401
            return {item: list(map(itemgetter(item), data))}
        except (TypeError, IndexError, KeyError):
            return None
    else:
        return None


def json_dumps_dictlist(data, item):
    dl = dictlist(data, item)
    if dl is None:
        return None
    return json_dumps(dl)


def string_value_to_float(s):
    """Convert a string with a value and an unit to a float.
    Example:
    '12.5 MB' -> 12500000.0
    '32.5 GB' -> 32500000000.0
    Args:
        s (string): Input string with value and unit
    Output:
        float: The value in float
    """
    convert_dict = {
        None: 1,
        'B': 1,
        'KB': 1000,
        'MB': 1000000,
        'GB': 1000000000,
        'TB': 1000000000000,
        'PB': 1000000000000000,
    }
    unpack_string = [
        i[0] if i[1] == '' else i[1].upper() for i in re.findall(r'([\d.]+)|([^\d.]+)', s.replace(' ', ''))
    ]
    if len(unpack_string) == 2:
        value, unit = unpack_string
    elif len(unpack_string) == 1:
        value = unpack_string[0]
        unit = None
    else:
        return None
    try:
        value = float(unpack_string[0])
    except ValueError:
        return None
    return value * convert_dict[unit]


def file_exists(filename):
    """Return True if the file exists and is readable."""
    return os.path.isfile(filename) and os.access(filename, os.R_OK)


def folder_size(path, errno=0):
    """Return a tuple with the size of the directory given by path and the errno.
    If an error occurs (for example one file or subfolder is not accessible),
    errno is set to the error number.

    path: <string>
    errno: <int> Should always be 0 when calling the function"""
    ret_size = 0
    ret_err = errno
    try:
        for f in os.scandir(path):
            if f.is_dir(follow_symlinks=False) and (f.name != '.' or f.name != '..'):
                ret = folder_size(os.path.join(path, f.name), ret_err)
                ret_size += ret[0]
                ret_err = ret[1]
            else:
                try:
                    ret_size += f.stat().st_size
                except OSError as e:
                    ret_err = e.errno
    except (OSError, PermissionError) as e:
        return 0, e.errno
    else:
        return ret_size, ret_err


def weak_lru_cache(maxsize=128, typed=False):
    """LRU Cache decorator that keeps a weak reference to self
    Source: https://stackoverflow.com/a/55990799"""

    def wrapper(func):
        @functools.lru_cache(maxsize, typed)
        def _func(_self, *args, **kwargs):
            return func(_self(), *args, **kwargs)

        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            return _func(weakref.ref(self), *args, **kwargs)

        return inner

    return wrapper


def namedtuple_to_dict(data):
    """Convert a namedtuple to a dict, using the _asdict() method embedded in PsUtil stats."""
    return {k: (v._asdict() if hasattr(v, '_asdict') else v) for k, v in data.items()}


def list_of_namedtuple_to_list_of_dict(data):
    """Convert a list of namedtuples to a dict, using the _asdict() method embedded in PsUtil stats."""
    return [namedtuple_to_dict(d) for d in data]


def replace_special_chars(input_string, by=' '):
    """Replace some special char by another in the input_string
    Return: the string with the chars replaced"""
    return input_string.replace('\r\n', by).replace('\n', by).replace('\t', by)
