# -*- coding: utf-8 -*-
#
# This file is part of Glances.
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

"""Custom logging class"""

import logging
import logging.config
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
            'formatter': 'short'
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


def glances_logger():
    _logger = logging.getLogger()
    try:
        logging.config.dictConfig(LOGGING_CFG)
    except AttributeError:
        # dictConfig is only available for Python 2.7 or higher
        # Minimal configuration for Python 2.6
        logging.basicConfig(filename=os.path.join(tempfile.gettempdir(), 'glances.log'),
                            level=logging.DEBUG,
                            format='%(asctime)s -- %(levelname)s -- %(message)s')
    return _logger

logger = glances_logger()
