#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Secures functions for Glances"""

import re
from subprocess import PIPE, Popen

from glances.globals import nativestr


def secure_popen(cmd):
    """A more or less secure way to execute system commands

    Multiple command should be separated with a &&

    :return: the result of the commands
    """
    ret = ''

    # Split by multiple commands (only '&&' separator is supported)
    for c in cmd.split('&&'):
        ret += __secure_popen(c)

    return ret


def __secure_popen(cmd):
    """A more or less secure way to execute system command

    Manage redirection (>) and pipes (|)
    """
    # Split by redirection '>'
    cmd_split_redirect = cmd.split('>')
    if len(cmd_split_redirect) > 2:
        return f'Glances error: Only one file redirection allowed ({cmd})'
    if len(cmd_split_redirect) == 2:
        stdout_redirect = cmd_split_redirect[1].strip()
        cmd = cmd_split_redirect[0]
    else:
        stdout_redirect = None

    sub_cmd_stdin = None
    p_last = None
    # Split by pipe '|'
    for sub_cmd in cmd.split('|'):
        # Split by space character, but do no split spaces within quotes (remove surrounding quotes, though)
        tmp_split = [_ for _ in list(filter(None, re.split(r'(\s+)|(".*?"+?)|(\'.*?\'+?)', sub_cmd))) if _ != ' ']
        sub_cmd_split = [_[1:-1] if (_[0] == _[-1] == '"') or (_[0] == _[-1] == '\'') else _ for _ in tmp_split]
        p = Popen(sub_cmd_split, shell=False, stdin=sub_cmd_stdin, stdout=PIPE, stderr=PIPE)
        if p_last is not None:
            # Allow p_last to receive a SIGPIPE if p exits.
            p_last.stdout.close()
            p_last.kill()
            p_last.wait()
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
