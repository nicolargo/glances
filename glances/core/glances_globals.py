#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

# Import system libs
import sys
import os
import gettext
import locale

# Path definitions
work_path = os.path.realpath(os.path.dirname(__file__))
appname_path = os.path.split(sys.argv[0])[0]
sys_prefix = os.path.realpath(os.path.dirname(appname_path))

# Operating system flag
# Note: Somes libs depends of OS
is_BSD = sys.platform.find('bsd') != -1
is_Linux = sys.platform.startswith('linux')
is_Mac = sys.platform.startswith('darwin')
is_Windows = sys.platform.startswith('win')

# i18n
locale.setlocale(locale.LC_ALL, '')
gettext_domain = 'glances'
# get locale directory
i18n_path = os.path.realpath(os.path.join(work_path, '..', 'i18n'))
sys_i18n_path = os.path.join(sys_prefix, 'share', 'locale')
if os.path.exists(i18n_path):
    locale_dir = i18n_path
elif os.path.exists(sys_i18n_path):
    locale_dir = sys_i18n_path
else:
    locale_dir = None
gettext.install(gettext_domain, locale_dir)
