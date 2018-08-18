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
This module contains the definition of the `Test_Entry` class, used to
represent individual entries in a `Device`'s SMART Self-test Log.
"""


class Test_Entry(object):
    """
    Contains all of the information associated with a single SMART Self-test
    log entry. This data is intended to exactly mirror that obtained through
    smartctl.
    """

    def __init__(self, format, num, test_type, status, hours, LBA, remain=None, segment=None, sense=None, ASC=None, ASCQ=None):
        self._format = format
        """
        **(str):** Indicates whether this entry was taken from an 'ata' or
        'scsi' self-test log. Used to display the content properly.
        """
        self.num = num
        """
        **(str):** Entry's position in the log from 1 (most recent) to 21
        (least recent).  ATA logs save the last 21 entries while SCSI logs
        only save the last 20.
        """
        self.type = test_type
        """
        **(str):** Type of test run.  Generally short, long (extended), or
        conveyance, plus offline (background) or captive (foreground).
        """
        self.status = status
        """
        **(str):** Self-test's status message, for example 'Completed without
        error' or 'Completed: read failure'.
        """
        self.hours = hours
        """
        **(str):** The device's power-on hours at the time the self-test
        was initiated.
        """
        self.LBA = LBA
        """
        **(str):** Indicates the first LBA at which an error was encountered
        during this self-test. Presented as a decimal value for ATA/SATA
        devices and in hexadecimal notation for SAS/SCSI devices.
        """
        self.remain = remain
        """
        **(str):** Percentage value indicating how much of the self-test is
        left to perform. '00%' indicates a complete test, while any other
        value could indicate a test in progress or one that failed prior to
        completion. Only reported by ATA devices.
        """
        self.segment = segment
        """
        **(str):** A manufacturer-specific self-test segment number reported
        by SCSI devices on self-test failure. Set to '-' otherwise.
        """
        self.sense = sense
        """
        **(str):** SCSI sense key reported on self-test failure. Set to '-'
        otherwise.
        """
        self.ASC = ASC
        """
        **(str):** SCSI 'Additonal Sense Code' reported on self-test failure.
        Set to '-' otherwise.
        """
        self.ASCQ = ASCQ
        """
        **(str):** SCSI 'Additonal Sense Code Quaifier' reported on self-test
        failure. Set to '-' otherwise.
        """

    def __getstate__(self):
        try:
            num = int(self.num)
        except:
            num = None
        return {
            'num': num,
            'type': self.type,
            'status': self.status,
            'hours': self.hours,
            'lba': self.LBA,
            'remain': self.remain,
            'segment': self.segment,
            'sense': self.sense,
            'asc': self.ASC,
            'ascq': self.ASCQ
        }

    def __repr__(self):
        """Define a basic representation of the class object."""
        return "<SMART Self-test [%s|%s] hrs:%s LBA:%s>" % (
            self.type, self.status, self.hours, self.LBA)

    def __str__(self):
        """
        Define a formatted string representation of the object's content.
        Looks nearly identical to the output of smartctl, without overflowing
        80-character lines.
        """
        if self._format == 'ata':
            return "{0:>2} {1:17}{2:30}{3:5}{4:7}{5:17}".format(
                self.num, self.type, self.status, self.remain, self.hours,
                self.LBA)
        else:
            # 'Segment' could not be fit on the 80-char line. It's of limited
            # utility anyway due to it's manufacturer-proprietary nature...
            return ("{0:>2} {1:17}{2:23}{3:7}{4:14}[{5:4}{6:5}{7:4}]".format(
                self.num,
                self.type,
                self.status,
                self.hours,
                self.LBA,
                self.sense,
                self.ASC,
                self.ASCQ
            ))

__all__ = ['Test_Entry']
