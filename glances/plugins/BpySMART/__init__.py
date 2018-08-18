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
Copyright (C) 2014 Marc Herndon

pySMART is a simple Python wrapper for the `smartctl` component of
`smartmontools`. It works under Linux and Windows, as long as smartctl is on
the system path. Running with administrative (root) privilege is strongly
recommended, as smartctl cannot accurately detect all device types or parse
all SMART information without full permissions.

With only a device's name (ie: /dev/sda, pd0), the API will create a
`Device` object, populated with all relevant information about
that device. The documented API can then be used to query this object for
information, initiate device self-tests, and perform other functions.

Usage
-----
The most common way to use pySMART is to create a logical representation of the
physical storage device that you would like to work with, as shown:

    #!bash
    >>> from pySMART import Device
    >>> sda = Device('/dev/sda')
    >>> sda
    <SATA device on /dev/sda mod:WDC WD5000AAKS-60Z1A0 sn:WD-WCAWFxxxxxxx>

`Device` class members can be accessed directly, and a number of helper methods
are provided to retrieve information in bulk.  Some examples are shown below:

    #!bash
    >>> sda.assessment  # Query the SMART self-assessment
    'PASS'
    >>> sda.attributes[9]  # Query a single SMART attribute
    <SMART Attribute 'Power_On_Hours' 068/000 raw:23644>
    >>> sda.all_attributes()  # Print the entire SMART attribute table
    ID# ATTRIBUTE_NAME          CUR WST THR TYPE     UPDATED WHEN_FAIL    RAW
      1 Raw_Read_Error_Rate     200 200 051 Pre-fail Always  -           0
      3 Spin_Up_Time            141 140 021 Pre-fail Always  -           3908
      4 Start_Stop_Count        098 098 000 Old_age  Always  -           2690
      5 Reallocated_Sector_Ct   200 200 140 Pre-fail Always  -           0
        ... # Edited for brevity
    199 UDMA_CRC_Error_Count    200 200 000 Old_age  Always  -           0
    200 Multi_Zone_Error_Rate   200 200 000 Old_age  Offline -           0
    >>> sda.tests[0]  # Query the most recent self-test result
    <SMART Self-test [Short offline|Completed without error] hrs:23734 LBA:->
    >>> sda.all_selftests()  # Print the entire self-test log
    ID Test_Description Status                        Left Hours  1st_Error@LBA
     1 Short offline    Completed without error       00%  23734  -
     2 Short offline    Completed without error       00%  23734  -
       ... # Edited for brevity
     7 Short offline    Completed without error       00%  23726  -
     8 Short offline    Completed without error       00%  1      -

Alternatively, the package provides a `DeviceList` class. When instantiated,
this will auto-detect all local storage devices and create a list containing
one `Device` object for each detected storage device.

    #!bash
    >>> from pySMART import DeviceList
    >>> devlist = DeviceList()
    >>> devlist
    <DeviceList contents:
    <SAT device on /dev/sdb mod:WDC WD20EADS-00R6B0 sn:WD-WCAVYxxxxxxx>
    <SAT device on /dev/sdc mod:WDC WD20EADS-00S2B0 sn:WD-WCAVYxxxxxxx>
    <CSMI device on /dev/csmi0,0 mod:WDC WD5000AAKS-60Z1A0 sn:WD-WCAWFxxxxxxx>
    >
    >>> devlist.devices[0].attributes[5]  # Access Device data as above
    <SMART Attribute 'Reallocated_Sector_Ct' 173/140 raw:214>

Using the pySMART wrapper, Python applications be be rapidly developed to take
advantage of the powerful features of smartmontools.

Acknowledgements
----------------
I would like to thank the entire team behind smartmontools for creating and
maintaining such a fantastic product.

In particular I want to thank Christian Franke, who maintains the Windows port
of the software.  For several years I have written Windows batch files that
rely on smartctl.exe to automate evaluation and testing of large pools of
storage devices under Windows.  Without his work, my job would have been
significantly more miserable. :)

Having recently migrated my development from Batch to Python for Linux
portabiity, I thought a simple wrapper for smartctl would save time in the
development of future automated test tools.
"""
from . import utils
utils.configure_trace_logging()

from .attribute import Attribute
from .device import Device, smart_health_assement
from .device_list import DeviceList
from .test_entry import Test_Entry


__version__ = '0.3'
