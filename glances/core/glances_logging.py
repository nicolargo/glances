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

"""Custom logging class."""

import logging
try:
    # Python 2.6
    from logutils.dictconfig import dictConfig
except ImportError:
    # Python >= 2.7
    from logging.config import dictConfig
import os
import tempfile

# Define the logging configuration
LOGGING_CFG = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'console']
    },
    'formatters': {
        'standard': {
            'format': '%(asctime)s -- %(levelname)s -- %(message)s'
        },
        'short': {
            'format': '%(levelname)s: %(message)s'
        },
        'free': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            # http://stackoverflow.com/questions/847850/cross-platform-way-of-getting-temp-directory-in-python
            'filename': os.path.join(tempfile.gettempdir(), 'glances.log')
        },
        'console': {
            'level': 'CRITICAL',
            'class': 'logging.StreamHandler',
            'formatter': 'free'
        }
    },
    'loggers': {
        'debug': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'verbose': {
            'handlers': ['file', 'console'],
            'level': 'INFO'
        },
        'standard': {
            'handlers': ['file'],
            'level': 'INFO'
        }
    }
}


def tempfile_name():
    """Return the tempfile name (full path)."""
    ret = os.path.join(tempfile.gettempdir(), 'glances.log')
    if os.access(ret, os.F_OK) and not os.access(ret, os.W_OK):
        print("WARNING: Couldn't write to log file {0}: (Permission denied)".format(ret))
        ret = tempfile.mkstemp(prefix='glances', suffix='.tmp', text=True)
        print("Create a new log file: {0}".format(ret[1]))
        return ret[1]

    return ret


def glances_logger():
    """Build and return the logger."""
    temp_path = tempfile_name()
    _logger = logging.getLogger()
    LOGGING_CFG['handlers']['file']['filename'] = temp_path
    dictConfig(LOGGING_CFG)

    return _logger

logger = glances_logger()
