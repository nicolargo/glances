# Copyright (C) 2014 Marc Herndon
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.
#
################################################################
"""
This module contains generic utilities and configuration information for use
by the other submodules of the `pySMART` package.
"""

import logging
import logging.handlers
import os
import io
import traceback
from shutil import which

_srcfile = __file__
TRACE = logging.DEBUG - 5


class TraceLogger(logging.Logger):
    def __init__(self, name):
        logging.Logger.__init__(self, name)
        logging.addLevelName(TRACE, 'TRACE')
        return

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE, msg, *args, **kwargs)

    def findCaller(self, stack_info=False):
        """
        Overload built-in findCaller method
        to omit not only logging/__init__.py but also the current file
        """
        f = logging.currentframe()
        # On some versions of IronPython, currentframe() returns None if
        # IronPython isn't run with -X:Frames.
        if f is not None:
            f = f.f_back
        rv = "(unknown file)", 0, "(unknown function)", None
        while hasattr(f, "f_code"):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)
            if filename in (logging._srcfile, _srcfile):
                f = f.f_back
                continue
            sinfo = None
            if stack_info:
                sio = io.StringIO()
                sio.write('Stack (most recent call last):\n')
                traceback.print_stack(f, file=sio)
                sinfo = sio.getvalue()
                if sinfo[-1] == '\n':
                    sinfo = sinfo[:-1]
                sio.close()
            rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
            break
        return rv


def configure_trace_logging():
    if getattr(logging.handlers.logging.getLoggerClass(), 'trace', None) is None:
        logging.setLoggerClass(TraceLogger)


smartctl_type = {
    'ata': 'ata',
    'csmi': 'ata',
    'nvme': 'nvme',
    'sas': 'scsi',
    'sat': 'sat',
    'sata': 'ata',
    'scsi': 'scsi',
    'atacam': 'atacam'
}
SMARTCTL_PATH = which('smartctl')
"""
**(dict of str):** Contains actual interface types (ie: sas, csmi) as keys and
the corresponding smartctl interface type (ie: scsi, ata) as values.
"""

__all__ = ['smartctl_type', 'SMARTCTL_PATH']
