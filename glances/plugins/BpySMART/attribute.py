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
This module contains the definition of the `Attribute` class, used to represent
individual SMART attributes associated with a `Device`.
"""


class Attribute(object):
    """
    Contains all of the information associated with a single SMART attribute
    in a `Device`'s SMART table. This data is intended to exactly mirror that
    obtained through smartctl.
    """

    def __init__(self, num, name, flags, value, worst, thresh, attr_type, updated, when_failed, raw):
        self.num = num
        """**(str):** Attribute's ID as a decimal value (1-255)."""
        self.name = name
        """
        **(str):** Attribute's name, as reported by smartmontools' drive.db.
        """
        self.flags = flags
        """**(str):** Attribute flags as a hexadecimal value (ie: 0x0032)."""
        self.value = value
        """**(str):** Attribute's current normalized value."""
        self.worst = worst
        """**(str):** Worst recorded normalized value for this attribute."""
        self.thresh = thresh
        """**(str):** Attribute's failure threshold."""
        self.type = attr_type
        """**(str):** Attribute's type, generally 'pre-fail' or 'old-age'."""
        self.updated = updated
        """
        **(str):** When is this attribute updated? Generally 'Always' or
        'Offline'
        """
        self.when_failed = when_failed
        """
        **(str):** When did this attribute cross below
        `pySMART.attribute.Attribute.thresh`? Reads '-' when not failed.
        Generally either 'FAILING_NOW' or 'In_the_Past' otherwise.
        """
        self.raw = raw
        """**(str):** Attribute's current raw (non-normalized) value."""

    def __repr__(self):
        """Define a basic representation of the class object."""
        return "<SMART Attribute %r %s/%s raw:%s>" % (
            self.name, self.value, self.thresh, self.raw)

    def __str__(self):
        """
        Define a formatted string representation of the object's content.
        In the interest of not overflowing 80-character lines this does not
        print the value of `pySMART.attribute.Attribute.flags_hex`.
        """
        return "{0:>3} {1:24}{2:4}{3:4}{4:4}{5:9}{6:8}{7:12}{8}".format(
            self.num,
            self.name,
            self.value,
            self.worst,
            self.thresh,
            self.type,
            self.updated,
            self.when_failed,
            self.raw
        )

    def __getstate__(self):
        return {
            'num': self.num,
            'flags': self.flags,
            'raw': self.raw,
            'value': self.value,
            'worst': self.worst,
            'threshold': self.thresh,
            'type': self.type,
            'updated': self.updated,
            'when_failed': self.when_failed,
        }


__all__ = ['Attribute']
