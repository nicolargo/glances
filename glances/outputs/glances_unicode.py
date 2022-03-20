# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2022 Nicolargo <nicolas@nicolargo.com>
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
