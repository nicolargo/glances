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


def secure_popen(cmd, allow_operators=True, render=None):
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
    :param render: an optional callable applied to each argument *after* the
        command line has been tokenized. Callers that build a command from a
        trusted template plus untrusted data (the on-alert actions and their
        {{mustache}} fields) must pass the expansion here instead of expanding
        the template first: once the argument boundaries are fixed, a rendered
        value can no longer open or close a quote, introduce whitespace or
        forge an operator, so it always lands in exactly one argument
        (GHSA-56xw-p9qm-r437).

    :return: the result of the command(s) (str)
    """
    if not allow_operators:
        # Run the whole command as a single process: '&&', '|' and '>' are
        # passed verbatim as arguments and never interpreted.
        return __run_argv(cmd, render)

    ret = ''

    # Split by multiple commands (only '&&' separator is supported)
    for c in cmd.split('&&'):
        ret += __secure_popen(c, render)

    return ret


def __split_args(cmd, render=None):
    """Split a command string into an argument list.

    Spaces are the separators, except within single or double quotes (the
    surrounding quotes are then removed).

    When render is given it is applied to every argument once the boundaries
    are already fixed. Rendering after the split, and never before, is what
    keeps a templated value confined to a single argument.
    """
    tmp_split = [_ for _ in list(filter(None, re.split(r'(\s+)|(".*?"+?)|(\'.*?\'+?)', cmd))) if _ != ' ']
    args = [_[1:-1] if (_[0] == _[-1] == '"') or (_[0] == _[-1] == '\'') else _ for _ in tmp_split]
    return args if render is None else [render(_) for _ in args]


def __run_argv(cmd, render=None):
    """Execute cmd as a single process, without interpreting any operator."""
    p = Popen(__split_args(cmd, render), shell=False, stdin=None, stdout=PIPE, stderr=PIPE)
    p_ret = p.communicate()
    if nativestr(p_ret[1]) == '':
        return nativestr(p_ret[0])
    return nativestr(p_ret[1])


def __secure_popen(cmd, render=None):
    """A more or less secure way to execute system command

    Manage redirection (>) and pipes (|)
    """
    # Split by redirection '>'
    cmd_split_redirect = cmd.split('>')
    if len(cmd_split_redirect) > 2:
        return f'Glances error: Only one file redirection allowed ({cmd})'
    if len(cmd_split_redirect) == 2:
        stdout_redirect = cmd_split_redirect[1].strip()
        if render is not None:
            # The redirection target may itself be templated
            stdout_redirect = render(stdout_redirect)
        cmd = cmd_split_redirect[0]
    else:
        stdout_redirect = None

    # Split by pipe '|', then tokenize (and render) every stage before spawning
    # anything: a template error must not leave a half-started pipeline behind.
    # Split by space character, but do no split spaces within quotes (remove surrounding quotes, though)
    sub_cmd_split_list = [__split_args(sub_cmd, render) for sub_cmd in cmd.split('|')]

    sub_cmd_stdin = None
    p_list = []
    for sub_cmd_split in sub_cmd_split_list:
        p = Popen(sub_cmd_split, shell=False, stdin=sub_cmd_stdin, stdout=PIPE, stderr=PIPE)
        if p_list:
            # Allow the previous process to receive a SIGPIPE if p exits.
            p_list[-1].stdout.close()
        p_list.append(p)
        sub_cmd_stdin = p.stdout

    p_ret = p_list[-1].communicate()
    # Reap the upstream processes of the pipeline (they exited on their own)
    for p in p_list[:-1]:
        p.wait()

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
