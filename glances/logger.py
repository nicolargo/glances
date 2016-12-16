# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

import logging
import os
import tempfile
import json
from logging.config import dictConfig

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
            "format": "%(levelname)s: %(message)s"
        },
        "free": {
            "format": "%(message)s"
        }
    },
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            'filename': os.path.join(tempfile.gettempdir(), 'glances.log')
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


def tempfile_name():
    """Return the tempfile name (full path)."""
    ret = os.path.join(tempfile.gettempdir(), 'glances.log')
    if os.access(ret, os.F_OK) and not os.access(ret, os.W_OK):
        print("WARNING: Couldn't write to log file {} (Permission denied)".format(ret))
        ret = tempfile.mkstemp(prefix='glances', suffix='.log', text=True)
        print("Create a new log file: {}".format(ret[1]))
        return ret[1]

    return ret


def glances_logger(env_key='LOG_CFG'):
    """Build and return the logger.

    env_key define the env var where a path to a specific JSON logger
            could be defined

    :return: logger -- Logger instance
    """
    _logger = logging.getLogger()

    # Overwrite the default logger file
    LOGGING_CFG['handlers']['file']['filename'] = tempfile_name()

    # By default, use the LOGGING_CFG lgger configuration
    config = LOGGING_CFG

    # Check if a specific configuration is available
    user_file = os.getenv(env_key, None)
    if user_file and os.path.exists(user_file):
        # A user file as been defined. Use it...
        with open(user_file, 'rt') as f:
            config = json.load(f)

    # Load the configuration
    dictConfig(config)

    return _logger

logger = glances_logger()
