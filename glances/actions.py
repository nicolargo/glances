#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage on alert actions."""

from glances.logger import logger
from glances.secure import secure_popen
from glances.timer import Timer

try:
    import chevron
except ImportError:
    logger.debug("Chevron library not found (action scripts won't work)")
    chevron_tag = False
else:
    chevron_tag = True

# Characters that secure_popen interprets as shell operators.
# Mustache-rendered values must not contain these to prevent command injection.
_SHELL_OPERATORS = ('&&', '|', '>>', '>')


def _sanitize_value(value):
    """Replace shell operators by spaces in a string, recursing into containers.

    Strings are sanitized; lists, tuples and dicts are walked so that nested
    attacker-controlled values (most notably a process ``cmdline``, exposed as a
    list of argv set by the attacker) are sanitized too. Other types (int,
    float, bool, None) are returned unchanged.

    Recursing is required: the top-level-only check left nested values
    exploitable (GHSA-73wf-9vmv-5pv9, incomplete fix of CVE-2026-32608). The
    Mustache renderer does not HTML-escape '|', so an unsanitized pipe in a
    nested value would survive into secure_popen and be interpreted.
    """
    if isinstance(value, str):
        for op in _SHELL_OPERATORS:
            value = value.replace(op, ' ')
        return value
    if isinstance(value, (list, tuple)):
        return type(value)(_sanitize_value(item) for item in value)
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    return value


def _sanitize_mustache_dict(mustache_dict):
    """Return a copy of mustache_dict with shell operators replaced by spaces.

    This prevents command injection when user-controllable data (process names,
    container names, mount points, etc.) is rendered into action command lines
    via Mustache templates. Sanitization is recursive so that strings nested in
    lists or dicts are covered, not only top-level string values.
    """
    if not mustache_dict:
        return mustache_dict

    return {k: _sanitize_value(v) for k, v in mustache_dict.items()}


class GlancesActions:
    """This class manage action if an alert is reached."""

    def __init__(self, args=None):
        """Init GlancesActions class."""
        # Dict with the criticality status
        # - key: stat_name
        # - value: criticality
        # Goal: avoid to execute the same command twice
        self.status = {}

        # Add a timer to avoid any trigger when Glances is started (issue#732)
        # Action can be triggered after refresh * 2 seconds
        if hasattr(args, 'time'):
            self.start_timer = Timer(args.time * 2)
        else:
            self.start_timer = Timer(3)

    def get(self, stat_name):
        """Get the stat_name criticality."""
        try:
            return self.status[stat_name]
        except KeyError:
            return None

    def set(self, stat_name, criticality):
        """Set the stat_name to criticality."""
        self.status[stat_name] = criticality

    def run(self, stat_name, criticality, commands, repeat, mustache_dict=None):
        """Run the commands (in background).

        :param stat_name: plugin_name (+ header)
        :param criticality: criticality of the trigger
        :param commands: a list of command line with optional {{mustache}}
        :param repeat: If True, then repeat the action
        :param  mustache_dict: Plugin stats (can be use within {{mustache}})

        :return: True if the commands have been ran.
        """
        if (self.get(stat_name) == criticality and not repeat) or not self.start_timer.finished():
            # Action already executed => Exit
            return False

        logger.debug(
            "{} action {} for {} ({}) with stats {}".format(
                "Repeat" if repeat else "Run", commands, stat_name, criticality, mustache_dict
            )
        )

        # Run all actions in background
        for cmd in commands:
            # Replace {{arg}} by the dict one (Thk to {Mustache})
            if chevron_tag:
                # Sanitize mustache values to prevent shell operator injection
                safe_dict = _sanitize_mustache_dict(mustache_dict)
                cmd_full = chevron.render(cmd, safe_dict)
            else:
                cmd_full = cmd
            # Execute the action
            logger.info(f"Action triggered for {stat_name} ({criticality}): {cmd_full}")
            try:
                ret = secure_popen(cmd_full)
            except OSError as e:
                logger.error(f"Action error for {stat_name} ({criticality}): {e}")
            else:
                logger.debug(f"Action result for {stat_name} ({criticality}): {ret}")

        self.set(stat_name, criticality)

        return True
