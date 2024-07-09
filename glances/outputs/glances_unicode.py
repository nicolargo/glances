#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage unicode message for Glances output."""

_unicode_message = {
    'ARROW_LEFT': ['\u2190', '<'],
    'ARROW_RIGHT': ['\u2192', '>'],
    'ARROW_UP': ['\u2191', '^'],
    'ARROW_DOWN': ['\u2193', 'v'],
    'CHECK': ['\u2713', ''],
    'PROCESS_SELECTOR': ['>', '>'],
    'MEDIUM_LINE': ['\u2500', '─'],
    'LOW_LINE': ['\u2581', '_'],
}


def unicode_message(key, args=None):
    """Return the unicode message for the given key."""
    if args and hasattr(args, 'disable_unicode') and args.disable_unicode:
        return _unicode_message[key][1]
    return _unicode_message[key][0]
