#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Custom logger class."""

import json
import logging
import logging.config
import logging.handlers
import os

from glances.globals import trusted_by_root


def _log_folder():
    """The folder of the log file, private to the user, or None when none can be made.

    Never a shared temporary folder: there, as root, another user can plant a
    link where the log is opened, and the log is readable by all (security
    audit 2026-10-04, M8). `$XDG_CACHE_HOME/glances` first (issue #1575), then
    `~/.local/share/glances`, `~` resolved from the password database when
    `$HOME` is not set. As root, a candidate owned by another user (`sudo -E`
    keeps `$HOME` and `$XDG_CACHE_HOME`) is skipped (security audit
    2026-10-17, X-2).
    """
    candidates = []
    xdg_cache_home = os.environ.get('XDG_CACHE_HOME')
    if xdg_cache_home and os.path.isdir(xdg_cache_home) and os.access(xdg_cache_home, os.W_OK):
        candidates.append(os.path.join(xdg_cache_home, 'glances'))
    home = os.path.expanduser('~')
    if os.path.isabs(home):
        candidates.append(os.path.join(home, '.local', 'share', 'glances'))
    for folder in candidates:
        try:
            os.makedirs(folder, mode=0o700, exist_ok=True)
        except OSError:
            continue
        if os.access(folder, os.W_OK) and trusted_by_root(folder):
            return folder
    return None


class PrivateRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A rotating log file readable by its owner only.

    A link at the log file is not followed, and the mode of a file the
    process does not own is left alone: as root, a link planted in the log
    folder sent the log elsewhere and made its target 0600 (security audit
    2026-10-17, X-2).
    """

    def _open(self):
        def opener(path, flags):
            fd = os.open(path, flags | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            if hasattr(os, 'fchmod') and os.fstat(fd).st_uid == os.geteuid():
                # A file left by an older Glances keeps the mode it was created with.
                os.fchmod(fd, 0o600)
            return fd

        return open(self.baseFilename, self.mode, encoding=self.encoding, errors=self.errors, opener=opener)


_LOG_FOLDER = _log_folder()
# None when no private folder could be made: the file handler is then a no-op.
LOG_FILENAME = os.path.join(_LOG_FOLDER, 'glances.log') if _LOG_FOLDER else None

# Define the logging configuration
LOGGING_CFG = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"level": "INFO", "handlers": ["file", "console"]},
    "formatters": {
        "standard": {"format": "%(asctime)s -- %(levelname)s -- %(message)s"},
        "short": {"format": "%(levelname)s -- %(message)s"},
        "long": {"format": "%(asctime)s -- %(levelname)s -- %(message)s (%(funcName)s in %(filename)s)"},
        "free": {"format": "%(message)s"},
    },
    "handlers": {
        "file": {
            "level": "DEBUG",
            # The class itself, not its dotted name: this module is still
            # being imported when `glances_logger()` below applies the config.
            "()": PrivateRotatingFileHandler,
            "maxBytes": 1000000,
            "backupCount": 3,
            "formatter": "standard",
            "filename": LOG_FILENAME,
        }
        if LOG_FILENAME
        else {"level": "DEBUG", "class": "logging.NullHandler"},
        "console": {"level": "CRITICAL", "class": "logging.StreamHandler", "formatter": "free"},
    },
    "loggers": {
        "debug": {"handlers": ["file", "console"], "level": "DEBUG"},
        "verbose": {"handlers": ["file", "console"], "level": "INFO"},
        "standard": {"handlers": ["file"], "level": "INFO"},
        "requests": {"handlers": ["file", "console"], "level": "ERROR"},
        "elasticsearch": {"handlers": ["file", "console"], "level": "ERROR"},
        "elasticsearch.trace": {"handlers": ["file", "console"], "level": "ERROR"},
    },
}


def glances_logger(env_key='LOG_CFG'):
    """Build and return the logger.

    env_key define the env var where a path to a specific JSON logger
            could be defined

    :return: logger -- Logger instance
    """
    _logger = logging.getLogger()

    # By default, use the LOGGING_CFG logger configuration
    config = LOGGING_CFG

    # Check if a specific configuration is available
    user_file = os.getenv(env_key, None)
    untrusted_file = None
    if user_file and os.path.exists(user_file):
        if trusted_by_root(user_file):
            # A user file as been defined. Use it...
            with open(user_file) as f:
                config = json.load(f)
        else:
            # As root, a logging configuration names the handler classes to
            # load: it must not come from a file another user can write
            # (security audit 2026-10-17, I-10, S-10).
            untrusted_file = user_file

    # Load the configuration
    logging.config.dictConfig(config)
    if untrusted_file:
        _logger.warning(
            "%s file %s ignored: running as root, it must be owned by root and not writable by others",
            env_key,
            untrusted_file,
        )

    return _logger


logger = glances_logger()
