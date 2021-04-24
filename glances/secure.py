# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
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

"""Secures functions for Glances"""

from glances.compat import nativestr
from subprocess import Popen, PIPE


def secure_popen(cmd):
    """A more or less secure way to execute system command

    Return: the result of the command OR an error message
    """
    ret = None

    # Split by redirection '>'
    cmd_split_redirect = cmd.split('>')
    if len(cmd_split_redirect) > 2:
        return 'Glances error: Only one file redirection allowed ({})'.format(cmd)
    elif len(cmd_split_redirect) == 2:
        stdout_redirect = cmd_split_redirect[1].strip()
        cmd = cmd_split_redirect[0]
    else:
        stdout_redirect = None

    sub_cmd_stdin = None
    p_last = None
    # Split by pipe '|'
    for sub_cmd in cmd.split('|'):
        # Split by space ' '
        sub_cmd_split = [i for i in sub_cmd.split(' ') if i]
        p = Popen(sub_cmd_split,
                  shell=False,
                  stdin=sub_cmd_stdin,
                  stdout=PIPE,
                  stderr=PIPE)
        if p_last is not None:
            # Allow p_last to receive a SIGPIPE if p exits.
            p_last.stdout.close()
        p_last = p
        sub_cmd_stdin = p.stdout

    p_ret = p_last.communicate()

    if nativestr(p_ret[1]) == '':
        # No error
        ret = nativestr(p_ret[0])
        if stdout_redirect is not None:
            # Write result to redirection file
            with open(stdout_redirect, "w") as stdout_redirect_file:
                stdout_redirect_file.write(ret)
    else:
        # Error
        ret = nativestr(p_ret[1])

    return ret
