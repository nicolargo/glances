# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage unicode message for Glances output."""

_unicode_message = {
    'ARROW_LEFT': [u'\u2190', u'<'],
    'ARROW_RIGHT': [u'\u2192', u'>'],
    'ARROW_UP': [u'\u2191', u'^'],
    'ARROW_DOWN': [u'\u2193', u'v'],
    'CHECK': [u'\u2713', u''],
    'PROCESS_SELECTOR': [u'>', u'>'],
    'MEDIUM_LINE': [u'\u23AF', u'-'],
    'LOW_LINE': [u'\u2581', u'_'],
}


def unicode_message(key, args=None):
    """Return the unicode message for the given key."""
    if args and hasattr(args, 'disable_unicode') and args.disable_unicode:
        return _unicode_message[key][1]
    else:
        return _unicode_message[key][0]
