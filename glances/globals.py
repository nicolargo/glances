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
import multiprocessing
import os
import platform
import queue
import re
import socket
import subprocess
import sys
import weakref
from collections import OrderedDict
from configparser import ConfigParser, NoOptionError, NoSectionError
from datetime import datetime
from operator import itemgetter, methodcaller
from statistics import mean
from typing import Any, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import psutil

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

# Multiprocessing start method (on POSIX system)
if LINUX or BSD or SUNOS or MACOS:
    ctx_mp_fork = multiprocessing.get_context('fork')
else:
    ctx_mp_fork = multiprocessing.get_context()

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
    """
    now = now or datetime.now()
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

    # Thresholds for day_diff == 0: (max_seconds, divisor, singular, plural)
    second_thresholds = [
        (10, 1, "just now", None),
        (60, 1, None, " secs"),
        (120, 1, "a min", None),
        (3600, 60, None, " mins"),
        (7200, 1, "an hour", None),
        (86400, 3600, None, " hours"),
    ]

    # Thresholds for day_diff > 0: (max_days, divisor, singular, plural)
    day_thresholds = [
        (2, 1, "yesterday", None),
        (7, 1, "a day", " days"),
        (31, 7, "a week", " weeks"),
        (365, 30, "a month", " months"),
        (float('inf'), 365, "an year", " years"),
    ]

    if day_diff == 0:
        for max_val, divisor, singular, plural in second_thresholds:
            if second_diff < max_val:
                if singular and not plural:
                    return singular
                value = second_diff // divisor
                return str(value) + plural

    for max_val, divisor, singular, plural in day_thresholds:
        if day_diff < max_val:
            value = day_diff // divisor
            if singular and (value <= 1 or not plural):
                return singular
            return str(value) + plural

    return ''


def urlopen_auth(url, username, password, timeout=3):
    """Open a url with basic auth"""
    return urlopen(
        Request(
            url,
            headers={'Authorization': 'Basic ' + base64.b64encode(f'{username}:{password}'.encode()).decode()},
        ),
        timeout=timeout,
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


def json_loads(data: str | bytes | bytearray) -> dict | list:
    """Load a JSON buffer into memory as a Python object"""
    return json.loads(data)


def list_to_dict(data):
    """Convert a list of dict (with key in 'key') to a dict with key as key and value as value."""
    if not isinstance(data, list):
        return None
    return {item[item['key']]: item for item in data if 'key' in item}


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


def dictlist_json_dumps(data, item):
    dl = dictlist(data, item)
    if dl is None:
        return None
    return json_dumps(dl)


def dictlist_first_key_value(data: list[dict], key, value) -> dict | None:
    """In a list of dict, return first item where key=value or none if not found."""
    try:
        ret = next(item for item in data if key in item and item[key] == value)
    except StopIteration:
        ret = None
    return ret


def auto_unit(number, low_precision=False, min_symbol='K', none_symbol='-'):
    """Make a nice human-readable string out of number.

    Number of decimal places increases as quantity approaches 1.
    CASE: 613421788        RESULT:       585M low_precision:       585M
    CASE: 5307033647       RESULT:      4.94G low_precision:       4.9G
    CASE: 44968414685      RESULT:      41.9G low_precision:      41.9G
    CASE: 838471403472     RESULT:       781G low_precision:       781G
    CASE: 9683209690677    RESULT:      8.81T low_precision:       8.8T
    CASE: 1073741824       RESULT:      1024M low_precision:      1024M
    CASE: 1181116006       RESULT:      1.10G low_precision:       1.1G

    :low_precision: returns less decimal places potentially (default is False)
                    sacrificing precision for more readability.
    :min_symbol: Do not approach if number < min_symbol (default is K)
    :decimal_count: if set, force the number of decimal number (default is None)
    """
    if number is None:
        return none_symbol
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    if min_symbol in symbols:
        symbols = symbols[symbols.index(min_symbol) :]
    prefix = {
        'Y': 1208925819614629174706176,
        'Z': 1180591620717411303424,
        'E': 1152921504606846976,
        'P': 1125899906842624,
        'T': 1099511627776,
        'G': 1073741824,
        'M': 1048576,
        'K': 1024,
    }

    if number == 0:
        # Avoid 0.0
        return '0'

    # If a value is a float, decimal_precision is 2 else 0
    decimal_precision = 2 if isinstance(number, float) else 0
    for symbol in reversed(symbols):
        value = float(number) / prefix[symbol]
        if value > 1:
            decimal_precision = 0
            if value < 10:
                decimal_precision = 2
            elif value < 100:
                decimal_precision = 1
            if low_precision:
                if symbol in 'MK':
                    decimal_precision = 0
                else:
                    decimal_precision = min(1, decimal_precision)
            elif symbol in 'K':
                decimal_precision = 0
            return '{:.{decimal}f}{symbol}'.format(value, decimal=decimal_precision, symbol=symbol)

    return f'{number:.{decimal_precision}f}'


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


def _get_ttl_hash(ttl):
    """A simple (dummy) function to return a hash based on the current second.
    TODO: Implement a real TTL mechanism.
    """
    if ttl is None:
        return 0
    now = datetime.now()
    return now.second


def weak_lru_cache(maxsize=1, typed=False, ttl=None):
    """LRU Cache decorator that keeps a weak reference to self

    Warning: When used in a class, the class should implement __eq__(self, other) and __hash__(self) methods

    Source: https://stackoverflow.com/a/55990799"""

    def wrapper(func):
        @functools.lru_cache(maxsize, typed)
        def _func(_self, *args, ttl_hash=None, **kwargs):
            del ttl_hash  # Unused parameter, but kept for compatibility
            return func(_self(), *args, **kwargs)

        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            return _func(weakref.ref(self), *args, ttl_hash=_get_ttl_hash(ttl), **kwargs)

        return inner

    return wrapper


def namedtuple_to_dict(data):
    """Convert a namedtuple to a dict, using the _asdict() method embedded in PsUtil stats."""
    return {k: (v._asdict() if hasattr(v, '_asdict') else v) for k, v in list(data.items())}


def list_of_namedtuple_to_list_of_dict(data):
    """Convert a list of namedtuples to a dict, using the _asdict() method embedded in PsUtil stats."""
    return [namedtuple_to_dict(d) for d in data]


def replace_special_chars(input_string, by=' '):
    """Replace some special char by another in the input_string
    Return: the string with the chars replaced"""
    return input_string.replace('\r\n', by).replace('\n', by).replace('\t', by)


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """Return a text in a natural/human readable format."""
    return [atoi(c) for c in re.split(r'(\d+)', text)]


def exit_after(seconds, default=None):
    """Exit the function if it takes more than 'seconds' seconds to complete.
    In this case, return the value of 'default' (default: None)."""

    def handler(q, func, args, kwargs):
        q.put(func(*args, **kwargs))

    def decorator(func):
        if not LINUX:
            return func

        def wraps(*args, **kwargs):
            try:
                q = ctx_mp_fork.Queue()
            except PermissionError:
                # Manage an exception in Snap packages on Linux
                # The strict mode prevent the use of multiprocessing.Queue()
                # There is a "dirty" hack:
                # https://forum.snapcraft.io/t/python-multiprocessing-permission-denied-in-strictly-confined-snap/15518/2
                # But i prefer to just disable the timeout feature in this case
                func(*args, **kwargs)
            else:
                p = ctx_mp_fork.Process(target=handler, args=(q, func, args, kwargs))
                p.start()
                p.join(timeout=seconds)
                if not p.is_alive():
                    return q.get()
                p.terminate()
                p.join(timeout=0.1)
                if p.is_alive():
                    # Kill in case processes doesn't terminate
                    # Happens with cases like broken NFS connections
                    p.kill()
            return default

        return wraps

    return decorator


def split_esc(input_string, sep=None, maxsplit=-1, esc='\\'):
    """
    Return a list of the substrings in the input_string, using sep as the separator char
    and esc as the escape character.

    sep
        The separator used to split the input_string.

        When set to None (the default value), will split on any whitespace
        character (including \n \r \t \f and spaces) unless the character is escaped
        and will discard empty strings from the result.
    maxsplit
        Maximum number of splits.
        -1 (the default value) means no limit.
    esc
        The character used to escape the separator.

        When set to None, this behaves equivalently to `str.split`.
        Defaults to '\\\\' i.e. backslash.

    Splitting starts at the front of the input_string and works to the end.

    Note: escape characters in the substrings returned are removed. However, if
    maxsplit is reached, escape characters in the remaining, unprocessed substring
    are not removed, which allows split_esc to be called on it again.
    """
    # Input validation
    if not isinstance(input_string, str):
        raise TypeError(f'must be str, not {input_string.__class__.__name__}')
    str.split('', sep=sep, maxsplit=maxsplit)  # Use str.split to validate sep and maxsplit
    if esc is None:
        return input_string.split(
            sep=sep, maxsplit=maxsplit
        )  # Short circuit to default implementation if the escape character is None
    if not isinstance(esc, str):
        raise TypeError(f'must be str or None, not {esc.__class__.__name__}')
    if len(esc) == 0:
        raise ValueError('empty escape character')
    if len(esc) > 1:
        raise ValueError('escape must be a single character')

    # Set up a simple state machine keeping track of whether we have seen an escape character
    ret, esc_seen, i = [''], False, 0
    while i < len(input_string) and len(ret) - 1 != maxsplit:
        if not esc_seen:
            if input_string[i] == esc:
                # Consume the escape character and transition state
                esc_seen = True
                i += 1
            elif sep is None and input_string[i].isspace():
                # Consume as much whitespace as possible
                n = 1
                while i + n + 1 < len(input_string) and input_string[i + n : i + n + 1].isspace():
                    n += 1
                ret.append('')
                i += n
            elif sep is not None and input_string[i : i + len(sep)] == sep:
                # Consume the separator
                ret.append('')
                i += len(sep)
            else:
                # Otherwise just add the current char
                ret[-1] += input_string[i]
                i += 1
        else:
            # Add the current char and transition state back
            ret[-1] += input_string[i]
            esc_seen = False
            i += 1

    # Append any remaining string if we broke early because of maxsplit
    if i < len(input_string):
        ret[-1] += input_string[i:]

    # If splitting on whitespace, discard empty strings from result
    if sep is None:
        ret = [sub for sub in ret if len(sub) > 0]

    return ret


def get_ip_address(ipv6=False):
    """Get current IP address and netmask as a tuple."""
    family = socket.AF_INET6 if ipv6 else socket.AF_INET

    # Get IP address
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()

    ip_address = None
    ip_netmask = None
    for interface, stat in stats.items():
        if stat.isup and interface != 'lo':
            if interface in addrs:
                for addr in addrs[interface]:
                    if addr.family == family:
                        ip_address = addr.address
                        ip_netmask = addr.netmask
                        break

    return ip_address, ip_netmask


def get_default_gateway(ipv6=False):
    """Get the default gateway IP address."""

    def convert_ipv4(gateway_hex):
        """Convert IPv4 hex (little-endian) to dotted notation."""
        return '.'.join(str(int(gateway_hex[i : i + 2], 16)) for i in range(6, -1, -2))

    def convert_ipv6(gateway_hex):
        """Convert IPv6 hex to colon notation."""
        return ':'.join(gateway_hex[i : i + 4] for i in range(0, 32, 4))

    if ipv6:
        route_file = '/proc/net/ipv6_route'
        default_dest = '00000000000000000000000000000000'
        dest_field = 0
        gateway_field = 4
        converter = convert_ipv6
    else:
        route_file = '/proc/net/route'
        default_dest = '00000000'
        dest_field = 1
        gateway_field = 2
        converter = convert_ipv4

    try:
        with open(route_file) as f:
            for line in f:
                fields = line.strip().split()
                if fields[dest_field] == default_dest:
                    return converter(fields[gateway_field])
    except (FileNotFoundError, IndexError, ValueError):
        return None
    return None
