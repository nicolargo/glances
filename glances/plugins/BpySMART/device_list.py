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
This module contains the definition of the `DeviceList` class, used to
represent all physical storage devices connected to the system.
Once initialized, the sole member `devices` will contain a list of `Device`
objects.

This class has no public methods.  All interaction should be through the
`Device` class API.
"""
# Python built-ins
from subprocess import Popen, PIPE

# pySMART module imports
from .device import Device
from .utils import SMARTCTL_PATH


class DeviceList(object):
    """
    Represents a list of all the storage devices connected to this computer.
    """

    def __init__(self, init=True):
        """
        Instantiates and optionally initializes the `DeviceList`.

        ###Args:
        * **init (bool):** By default, `pySMART.device_list.DeviceList.devices`
        is populated with `Device` objects during instantiation. Setting init
        to False will skip initialization and create an empty
        `pySMART.device_list.DeviceList` object instead.
        """
        self.devices = []
        """
        **(list of `Device`):** Contains all storage devices detected during
        instantiation, as `Device` objects.
        """
        if init:
            self._initialize()

    def __repr__(self):
        """Define a basic representation of the class object."""
        rep = "<DeviceList contents:\n"
        for device in self.devices:
            rep += str(device) + '\n'
        return rep + '>'
        # return "<DeviceList contents:%r>" % (self.devices)

    def _cleanup(self):
        """
        Removes duplicate ATA devices that correspond to an existing CSMI
        device. Also removes any device with no capacity value, as this
        indicates removable storage, ie: CD/DVD-ROM, ZIP, etc.
        """
        # We can't operate directly on the list while we're iterating
        # over it, so we collect indeces to delete and remove them later
        to_delete = []
        # Enumerate the list to get tuples containing indeces and values
        for index, device in enumerate(self.devices):
            if device.interface == 'csmi':
                for otherindex, otherdevice in enumerate(self.devices):
                    if (otherdevice.interface == 'ata' or
                            otherdevice.interface == 'sata'):
                        if device.serial == otherdevice.serial:
                            to_delete.append(otherindex)
                            device._sd_name = otherdevice.name
            if device.capacity is None and index not in to_delete:
                to_delete.append(index)
        # Recreate the self.devices list without the marked indeces
        self.devices[:] = [v for i, v in enumerate(self.devices)
                           if i not in to_delete]

    def _initialize(self):
        """
        Scans system busses for attached devices and add them to the
        `DeviceList` as `Device` objects.
        """
        cmd = Popen([SMARTCTL_PATH, '--scan-open'], stdout=PIPE, stderr=PIPE)
        _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
        for line in _stdout.split('\n'):
            if not ('failed:' in line or line == ''):
                name = line.split(' ')[0].replace('/dev/', '')
                # CSMI devices are explicitly of the 'csmi' type and do not
                # require further disambiguation
                if name[0:4] == 'csmi':
                    self.devices.append(Device(name, interface='csmi'))
                # Other device types will be disambiguated by Device.__init__
                else:
                    self.devices.append(Device(name))
        # Remove duplicates and unwanted devices (optical, etc.) from the list
        self._cleanup()
        # Sort the list alphabetically by device name
        self.devices.sort(key=lambda device: device.name)

__all__ = ['DeviceList']
