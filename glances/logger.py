# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""Custom logger class."""

import os
import json
import getpass
import tempfile

import logging
import logging.config

from glances.globals import BSD, LINUX, MACOS, SUNOS, WINDOWS, WSL
from glances.globals import safe_makedirs

# Choose the good place for the log file (see issue #1575)
# Default root path
if 'HOME' in os.environ:
    _XDG_CACHE_HOME = os.path.join(os.environ['HOME'], '.local', 'share')
else:
    _XDG_CACHE_HOME = ''
# Define the glances log file
if 'XDG_CACHE_HOME' in os.environ \
        and os.path.isdir(os.environ['XDG_CACHE_HOME']) \
        and os.access(os.environ['XDG_CACHE_HOME'], os.W_OK):
    safe_makedirs(os.path.join(os.environ['XDG_CACHE_HOME'], 'glances'))
    LOG_FILENAME = os.path.join(os.environ['XDG_CACHE_HOME'], 'glances', 'glances.log')
elif os.path.isdir(_XDG_CACHE_HOME) and os.access(_XDG_CACHE_HOME, os.W_OK):
    safe_makedirs(os.path.join(_XDG_CACHE_HOME, 'glances'))
    LOG_FILENAME = os.path.join(_XDG_CACHE_HOME, 'glances', 'glances.log')
else:
    LOG_FILENAME = os.path.join(tempfile.gettempdir(),
                                'glances-{}.log'.format(getpass.getuser()))

# Define the logging configuration
LOGGING_CFG = {
    "version": 1,
    "disable_existing_loggers": "False",
    "root": {
        "level": "INFO",
        "handlers": ["file", "console"]
    },
    "formatters": {
        "standard": {
            "format": "%(asctime)s -- %(levelname)s -- %(message)s"
        },
        "short": {
            "format": "%(levelname)s -- %(message)s"
        },
        "long": {
            "format": "%(asctime)s -- %(levelname)s -- %(message)s (%(funcName)s in %(filename)s)"
        },
        "free": {
            "format": "%(message)s"
        }
    },
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1000000,
            "backupCount": 3,
            "formatter": "standard",
            "filename": LOG_FILENAME
        },
        "console": {
            "level": "CRITICAL",
            "class": "logging.StreamHandler",
            "formatter": "free"
        }
    },
    "loggers": {
        "debug": {
            "handlers": ["file", "console"],
            "level": "DEBUG"
        },
        "verbose": {
            "handlers": ["file", "console"],
            "level": "INFO"
        },
        "standard": {
            "handlers": ["file"],
            "level": "INFO"
        },
        "requests": {
            "handlers": ["file", "console"],
            "level": "ERROR"
        },
        "elasticsearch": {
            "handlers": ["file", "console"],
            "level": "ERROR"
        },
        "elasticsearch.trace": {
            "handlers": ["file", "console"],
            "level": "ERROR"
        }
    }
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
    if user_file and os.path.exists(user_file):
        # A user file as been defined. Use it...
        with open(user_file, 'rt') as f:
            config = json.load(f)

    # Load the configuration
    logging.config.dictConfig(config)

    return _logger


logger = glances_logger()
