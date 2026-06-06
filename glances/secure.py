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


def secure_popen(cmd, allow_operators=True):
    """A more or less secure way to execute system commands.

    By default the following shell-like operators are interpreted:
    - '&&' to chain commands
    - '|'  to pipe a command output into the next one
    - '>'  to redirect the output to a file

    :param cmd: the command line to run (str)
    :param allow_operators: when False, the operators above are NOT
        interpreted but passed verbatim as literal arguments. The command is
        then run as a single process that can neither chain, pipe nor write to
        an arbitrary file. Used for commands coming from the configuration file
        when --disable-config-exec is set (GHSA-3vwc-qwhc-3mj7).

    :return: the result of the command(s) (str)
    """
    if not allow_operators:
        # Run the whole command as a single process: '&&', '|' and '>' are
        # passed verbatim as arguments and never interpreted.
        return __run_argv(cmd)

    ret = ''

    # Split by multiple commands (only '&&' separator is supported)
    for c in cmd.split('&&'):
        ret += __secure_popen(c)

    return ret


def __split_args(cmd):
    """Split a command string into an argument list.

    Spaces are the separators, except within single or double quotes (the
    surrounding quotes are then removed).
    """
    tmp_split = [_ for _ in list(filter(None, re.split(r'(\s+)|(".*?"+?)|(\'.*?\'+?)', cmd))) if _ != ' ']
    return [_[1:-1] if (_[0] == _[-1] == '"') or (_[0] == _[-1] == '\'') else _ for _ in tmp_split]


def __run_argv(cmd):
    """Execute cmd as a single process, without interpreting any operator."""
    p = Popen(__split_args(cmd), shell=False, stdin=None, stdout=PIPE, stderr=PIPE)
    p_ret = p.communicate()
    if nativestr(p_ret[1]) == '':
        return nativestr(p_ret[0])
    return nativestr(p_ret[1])


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
        sub_cmd_split = __split_args(sub_cmd)
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
