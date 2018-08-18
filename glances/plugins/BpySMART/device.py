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
This module contains the definition of the `Device` class, used to represent a
physical storage device connected to the system.
Once initialized, class members contain all relevant information about the
device, including its model, serial number, firmware version, and all SMART
attribute data.

Methods are provided for initiating self tests and querying their results.
"""
# Python built-ins
from __future__ import print_function
import os
import logging
import re  # Don't delete this 'un-used' import
from subprocess import Popen, PIPE
from time import time, strptime, mktime, sleep
import warnings

# pySMART module imports
from .attribute import Attribute
from .test_entry import Test_Entry
from .utils import smartctl_type, SMARTCTL_PATH

logger = logging.getLogger('pySMART')


def smart_health_assement(disk_name):
    """
    This function gets the SMART Health Status of the disk (IF the disk
    is SMART capable and smart is enabled on it else returns None).
    This function is to be used only in abridged mode and not otherwise,
    since in non-abridged mode update gets this information anyways.
    """
    assessment = None
    cmd = Popen(
        [SMARTCTL_PATH, '--health', os.path.join('/dev/', disk_name.replace('nvd','nvme'))],
        stdout=PIPE,
        stderr=PIPE,
    )
    _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
    _stdout = _stdout.split('\n')
    line = _stdout[4]  # We only need this line
    if 'SMART overall-health self-assessment' in line:  # ATA devices
        if line.split(':')[1].strip() == 'PASSED':
            assessment = 'PASS'
        else:
            assessment = 'FAIL'
    if 'SMART Health Status' in line:  # SCSI devices
        if line.split(':')[1].strip() == 'OK':
            assessment = 'PASS'
        else:
            assessment = 'FAIL'
    return assessment


class Device(object):

    """
    Represents any device attached to an internal storage interface, such as a
    hard drive or DVD-ROM, and detected by smartmontools. Includes eSATA
    (considered SATA) but excludes other external devices (USB, Firewire).
    """

    def __init__(self, name, interface=None, abridged=False, smart_options=''):
        """Instantiates and initializes the `pySMART.device.Device`."""
        if not (
            interface is None or
            interface.lower() in [
                'ata', 'csmi', 'sas', 'sat', 'sata', 'scsi', 'atacam', 'nvme', 'unknown interface'
            ]
        ):
            raise ValueError('Unknown interface: {0} specified for {1}'.format(interface, name))
        self.abridged = abridged or interface == 'UNKNOWN INTERFACE'
        self.smart_options = smart_options.split(' ') if smart_options else ['']
        self.name = name.replace('/dev/', '').replace('nvd', 'nvme')
        """
        **(str):** Device's hardware ID, without the '/dev/' prefix.
        (ie: sda (Linux), pd0 (Windows))
        """
        self.model = None
        """**(str):** Device's model number."""
        self.serial = None
        """**(str):** Device's serial number."""
        self.interface = None if interface == 'UNKNOWN INTERFACE' else interface
        """
        **(str):** Device's interface type. Must be one of:
            * **ATA** - Advanced Technology Attachment
            * **SATA** - Serial ATA
            * **SCSI** - Small Computer Systems Interface
            * **SAS** - Serial Attached SCSI
            * **SAT** - SCSI-to-ATA Translation (SATA device plugged into a
            SAS port)
            * **CSMI** - Common Storage Management Interface (Intel ICH /
            Matrix RAID)
        Generally this should not be specified to allow auto-detection to
        occur. Otherwise, this value overrides the auto-detected type and could
        produce unexpected or no data.
        """
        self.capacity = None
        """**(str):** Device's user capacity."""
        self.firmware = None
        """**(str):** Device's firmware version."""
        self.smart_capable = True if 'nvme' in self.name else False
        """
        **(bool):** True if the device has SMART Support Available.
        False otherwise. This is useful for VMs amongst other things.
        """
        self.smart_enabled = True if 'nvme' in self.name else False
        """
        **(bool):** True if the device supports SMART (or SCSI equivalent) and
        has the feature set enabled. False otherwise.
        """
        self.assessment = None
        """
        **(str):** SMART health self-assessment as reported by the device.
        """
        self.messages = []
        """
        **(list of str):** Contains any SMART warnings or other error messages
        reported by the device (ie: ASCQ codes).
        """
        self.is_ssd = True if 'nvme' in self.name else False
        """
        **(bool):** True if this device is a Solid State Drive.
        False otherwise.
        """
        self.rotation_rate = None
        """
        **(int):** The Roatation Rate of the Drive if it is not a SSD.
        The Metric is RPM.
        """
        self.attributes = [None] * 256
        """
        **(list of `Attribute`):** Contains the complete SMART table
        information for this device, as provided by smartctl. Indexed by
        attribute #, values are set to 'None' for attributes not suported by
        this device.
        """
        self.test_capabilities = {
            'offline': False,       # SMART execute Offline immediate (ATA only)
            'short': False if 'nvme' in self.name else True,  # SMART short Self-test
            'long': False if 'nvme' in self.name else True,   # SMART long Self-test
            'conveyance': False,    # SMART Conveyance Self-Test (ATA only)
            'selective': False,     # SMART Selective Self-Test (ATA only)
        }
        # Note have not included 'offline' test for scsi as it runs in the foregorund
        # mode. While this may be beneficial to us in someways it is against the
        # general layout and pattern that the other tests issued using pySMART are
        # followed hence not doing it currently
        """
        **(dict): ** This dictionary contains key == 'Test Name' and
        value == 'True/False' of self-tests that this device is capable of.
        """
        # Note: The above are just default values and can/will be changed
        # upon update() when the attributes and type of the disk is actually
        # determined.
        self.tests = []
        """
        **(list of `Log_Entry`):** Contains the complete SMART self-test log
        for this device, as provided by smartctl. If no SMART self-tests have
        been recorded, contains a `None` type instead.
        """
        self._test_running = False
        """
        **(bool):** True if a self-test is currently being run.
        False otherwise.
        """
        self._test_ECD = None
        """
        **(str):** Estimated completion time of the running SMART selftest.
        Not provided by SAS/SCSI devices.
        """
        self._test_progress = None
        """
        **(int):** Estimate progress percantage of the running SMART selftest.
        """
        self.diags = {}
        """
        **(dict of str):** Contains parsed and processed diagnostic information
        extracted from the SMART information. Currently only populated for
        SAS and SCSI devices, since ATA/SATA SMART attributes are manufacturer
        proprietary.
        """
        self.temperature = None
        """
        **(int or None): Since SCSI disks do not report attributes like ATA ones
        we need to grep/regex the shit outta the normal "smartctl -a" output
        """
        if self.name is None:
            warnings.warn(
                "\nDevice '{0}' does not exist! This object should be destroyed.".format(name)
            )
            return
        # If no interface type was provided, scan for the device
        # Lets do this only for the non-abridged case
        # (we can work with no interface for abridged case)
        elif self.interface is None and not self.abridged:
            logger.trace("Determining interface of disk: {0}".format(self.name))
            cmd = Popen(
                [SMARTCTL_PATH, '-d', 'test', os.path.join('/dev/', self.name)],
                stdout=PIPE,
                stderr=PIPE
            )
            _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
            if _stdout != '':
                # I do not like this parsing logic but it works for now!
                # just for reference _stdout.split('\n') gets us
                # something like
                # [
                #     ...copyright string...,
                #     '',
                #     "/dev/ada2: Device of type 'atacam' [ATA] detected",
                #     "/dev/ada2: Device of type 'atacam' [ATA] opened",
                #     ''
                # ]
                # The above example should be enough for anyone to understand the line below
                try:
                    self.interface = _stdout.split('\n')[-2].split("'")[1]
                except:
                    # for whatever reason we could not get the interface type
                    # we should mark this as an `abbridged` case and move on
                    self.interface = None
                    self.abbridged = True
                # TODO: Uncomment the classify call if we ever find out that we need it
                # Disambiguate the generic interface to a specific type
                # self._classify()
            else:
                warnings.warn(
                    "\nDevice '{0}' does not exist! This object should be destroyed.".format(name)
                )
                return
        # If a valid device was detected, populate its information
        # OR if in unabridged mode, then do it even without interface info
        if self.interface is not None or self.abridged:
            self.update()

    def __repr__(self):
        """Define a basic representation of the class object."""
        return "<{0} device on /dev/{1} mod:{2} sn:{3}>".format(
            self.interface.upper() if self.interface else 'UNKNOWN INTERFACE',
            self.name,
            self.model,
            self.serial
        )

    def __getstate__(self, all_info=True):
        """
        Allows us to send a pySMART Device object over a serializable
        medium which uses json (or the likes of json) payloads
        """
        state_dict = {
            'interface': self.interface if self.interface else 'UNKNOWN INTERFACE',
            'model': self.model,
            'firmware': self.firmware,
            'smart_capable': self.smart_capable,
            'smart_enabled': self.smart_enabled,
            'smart_status': self.assessment,
            'messages': self.messages,
            'test_capabilities': self.test_capabilities.copy(),
            'tests': [t.__getstate__() for t in self.tests] if self.tests else None,
            'diagnostics': self.diags.copy(),
            'temperature': self.temperature,
            'attributes': [attr.__getstate__() if attr else None for attr in self.attributes]
        }
        if all_info:
            state_dict.update({
                'name': self.name,
                'path': os.path.join('/dev/', self.name),
                'serial': self.serial,
                'is_ssd': self.is_ssd,
                'rotation_rate': self.rotation_rate,
                'capacity': self.capacity
            })
        return state_dict

    def smart_toggle(self, action):
        """
        A basic function to enable/disable SMART on device.

        ##Args:
        * **action (str):** Can be either 'on'(for enabling) or 'off'(for disabling).

        ##Returns"
        * **(bool):** Return True (if action succeded) else False
        * **(str):** None if option succeded else contains the error message.
        """
        # Lets make the action verb all lower case
        if self.interface == 'nvme':
            return (False, "NVME devices do not currently support toggling SMART enabled")
        action_lower = action.lower()
        if action_lower not in ['on', 'off']:
            return (False, 'Unsupported action {0}'.format(action))
        # Now lets check if the device's smart enabled status is already that of what
        # the supplied action is intending it to be. If so then just return successfully
        if self.smart_enabled:
            if action_lower == 'on':
                return (True, None)
        else:
            if action_lower == 'off':
                return (True, None)
        cmd = Popen(
            [
                SMARTCTL_PATH,
                '-s',
                action_lower,
                os.path.join('/dev/', self.name)
            ],
            stdout=PIPE, stderr=PIPE)
        _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
        if cmd.returncode != 0:
            return (False, _stdout + _stderr)
        # if everything worked out so far lets perform an update() and check the result
        self.update()
        if action_lower == 'off' and self.smart_enabled:
            return (False, 'Failed to turn SMART off.')
        if action_lower == 'on' and not self.smart_enabled:
            return (False, 'Failed to turn SMART on.')
        return (True, None)

    def all_attributes(self):
        """
        Prints the entire SMART attribute table, in a format similar to
        the output of smartctl.
        """
        header_printed = False
        for attr in self.attributes:
            if attr is not None:
                if not header_printed:
                    print("{0:>3} {1:24}{2:4}{3:4}{4:4}{5:9}{6:8}{7:12}"
                          "{8}".format(
                              'ID#', 'ATTRIBUTE_NAME', 'CUR', 'WST', 'THR',
                              'TYPE', 'UPDATED', 'WHEN_FAIL', 'RAW'))
                    header_printed = True
                print(attr)
        if not header_printed:
            print("This device does not support SMART attributes.")

    def all_selftests(self):
        """
        Prints the entire SMART self-test log, in a format similar to
        the output of smartctl.
        """
        if self.tests:
            all_tests = []
            if smartctl_type[self.interface] == 'scsi':
                header = ("{0:3}{1:17}{2:23}{3:7}{4:14}{5:15}".format(
                    'ID',
                    'Test Description',
                    'Status',
                    'Hours',
                    '1st_Error@LBA',
                    '[SK  ASC  ASCQ]'
                ))
            else:
                header = ("{0:3}{1:17}{2:30}{3:5}{4:7}{5:17}".format(
                    'ID',
                    'Test_Description',
                    'Status',
                    'Left',
                    'Hours',
                    '1st_Error@LBA'))
            all_tests.append(header)
            for test in self.tests:
                all_tests.append(str(test))

            return all_tests
        else:
            no_tests = "No self-tests have been logged for this device."
            return no_tests


    def _classify(self):
        """
        Disambiguates generic device types ATA and SCSI into more specific
        ATA, SATA, SAS, SAT and SCSI.
        """
        # SCSI devices might be SCSI, SAS or SAT
        # ATA device might be ATA or SATA
        if self.interface in ['scsi', 'ata']:
            test = 'sat' if self.interface == 'scsi' else 'sata'
            # Look for a SATA PHY to detect SAT and SATA
            cmd = Popen(
                [
                    SMARTCTL_PATH,
                    '-d',
                    smartctl_type[test],
                    '-l',
                    'sataphy',
                    os.path.join('/dev/', self.name)
                ],
                stdout=PIPE,
                stderr=PIPE
            )
            _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
            if 'GP Log 0x11' in _stdout.split('\n')[3]:
                self.interface = test
        # If device type is still SCSI (not changed to SAT above), then
        # check for a SAS PHY
        if self.interface == 'scsi':
            cmd = Popen(
                [
                    SMARTCTL_PATH,
                    '-d',
                    'scsi',
                    '-l',
                    'sasphy',
                    os.path.join('/dev/', self.name)
                ],
                stdout=PIPE,
                stderr=PIPE
            )
            _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
            if 'SAS SSP' in _stdout.split('\n')[4]:
                self.interface = 'sas'
            # Some older SAS devices do not support the SAS PHY log command.
            # For these, see if smartmontools reports a transport protocol.
            else:
                cmd = Popen(
                    [
                        SMARTCTL_PATH,
                        '-d',
                        'scsi',
                        '-a',
                        os.path.join('/dev/', self.name)
                    ],
                    stdout=PIPE,
                    stderr=PIPE
                )
                _stdout, _stderr = [i.decode('utf8', 'ignore') for i in cmd.communicate()]
                for line in _stdout.split('\n'):
                    if 'Transport protocol' in line and 'SAS' in line:
                        self.interface = 'sas'

    def _guess_SMART_type(self, line):
        """
        This function is not used in the generic wrapper, however the header
        is defined so that it can be monkey-patched by another application.
        """
        pass

    def _make_SMART_warnings(self):
        """
        Parses an ATA/SATA SMART table for attributes with the 'when_failed'
        value set. Generates an warning message for any such attributes and
        updates the self-assessment value if necessary.
        """
        if smartctl_type[self.interface] == 'scsi':
            return
        for attr in self.attributes:
            warn_str = ""
            if attr is not None:
                if attr.when_failed == 'In_the_past':
                    warn_str = "{0} failed in the past with value {1}. [Threshold: {2}]".format(
                        attr.name, attr.worst, attr.thresh)
                    self.messages.append(warn_str)
                    if not self.assessment == 'FAIL':
                        self.assessment = 'WARN'
                elif attr.when_failed == 'FAILING_NOW':
                    warn_str = "{0} is failing now with value {1}. [Threshold: {2}]".format(
                        attr.name, attr.value, attr.thresh)
                    self.assessment = 'FAIL'
                    self.messages.append(warn_str)
                elif not attr.when_failed == '-':
                    warn_str = "{0} says it failed '{1}'. [V={2},W={3},T={4}]".format(
                        attr.name, attr.when_failed, attr.value, attr.worst, attr.thresh)
                    self.messages.append(warn_str)
                    if not self.assessment == 'FAIL':
                        self.assessment = 'WARN'

    def get_selftest_result(self, output=None):
        """
        Refreshes a device's `pySMART.device.Device.tests` attribute to obtain
        the latest test results. If a new test result is obtained, its content
        is returned.

        ###Args:
        * **output (str, optional):** If set to 'str', the string
        representation of the most recent test result will be returned, instead
        of a `Test_Entry` object.

        ##Returns:
        * **(int):** Return status code. One of the following:
            * 0 - Success. Object (or optionally, string rep) is attached.
            * 1 - Self-test in progress. Must wait for it to finish.
            * 2 - No new test results.
            * 3 - The Self-test was Aborted by host
        * **(`Test_Entry` or str):** Most recent `Test_Entry` object (or
        optionally it's string representation) if new data exists.  Status
        message string on failure.
        * **(int):** Estimate progress percantage of the running SMART selftest, if known.
        Otherwise 'None'.
        """
        # SCSI self-test logs hold 20 entries while ATA logs hold 21
        if smartctl_type[self.interface] == 'scsi':
            maxlog = 20
        else:
            maxlog = 21
        # If we looked only at the most recent test result we could be fooled
        # by two short tests run close together (within the same hour)
        # appearing identical. Comparing the length of the log adds some
        # confidence until it maxes, as above. Comparing the least-recent test
        # result greatly diminishes the chances that two sets of two tests each
        # were run within an hour of themselves, but with 16-17 other tests run
        # in between them.
        if self.tests:
            _first_entry = self.tests[0]
            _len = len(self.tests)
            _last_entry = self.tests[_len - 1]
        else:
            _len = 0
        self.update()
        # Since I have changed the update() parsing to DTRT to pickup currently
        # running selftests we can now purely rely on that for self._test_running
        # Thus check for that variable first and return if it is True with appropos message.
        if self._test_running is True:
            return (1, 'Self-test in progress. Please wait.', self._test_progress)
        # Check whether the list got longer (ie: new entry)
        # If so return the newest test result
        # If not, because it's max size already, check for new entries
        if (
            (self.tests is not None and len(self.tests) != _len) or
            (
                len == maxlog and
                (
                    _first_entry.type != self.tests[0].type or
                    _first_entry.hours != self.tests[0].hours or
                    _last_entry.type != self.tests[len(self.tests) - 1].type or
                    _last_entry.hours != self.tests[len(self.tests) - 1].hours
                )
            )
        ):
            return (
                0 if 'Aborted' not in self.tests[0].status else 3,
                str(self.tests[0]) if output == 'str' else self.tests[0],
                None
            )
        else:
            return (2, 'No new self-test results found.', None)

    def abort_selftest(self):
        """
        Aborts non-captive SMART Self Tests.   Note that this command
        will  abort the Offline Immediate Test routine only if your disk
        has the "Abort Offline collection upon new command"  capability.

        ##Args: Nothing (just aborts directly)

        ##Returns:
        * **(int):** The returncode of calling `smartctl -X device_path`
        """
        cmd = Popen(
            [
                SMARTCTL_PATH,
                '-d',
                smartctl_type[self.interface],
                '-X',
                os.path.join("/dev/", self.name),
            ],
            stdout=PIPE,
            stderr=PIPE
        )
        cmd.wait()
        return cmd.returncode

    def run_selftest(self, test_type, ETA_type='date'):
        """
        Instructs a device to begin a SMART self-test. All tests are run in
        'offline' / 'background' mode, allowing normal use of the device while
        it is being tested.

        ##Args:
        * **test_type (str):** The type of test to run. Accepts the following
        (not case sensitive):
            * **short** - Brief electo-mechanical functionality check.
            Generally takes 2 minutes or less.
            * **long** - Thorough electro-mechanical functionality check,
            including complete recording media scan. Generally takes several
            hours.
            * **conveyance** - Brief test used to identify damage incurred in
            shipping. Generally takes 5 minutes or less. **This test is not
            supported by SAS or SCSI devices.**
            * **offline** - Runs SMART Immediate Offline Test. The effects of
            this test are visible only in that it updates the SMART Attribute
            values, and if errors are found they will appear in the SMART error
            log, visible with the '-l error' option to smartctl. **This test is
            not supported by SAS or SCSI devices in pySMART use cli smartctl for
            running 'offline' selftest (runs in foreground) on scsi devices.**
            * **ETA_type** - Format to return the estimated completion time/date
            in. Default is 'date'. One could otherwise specidy 'seconds'.
            Again only for ATA devices.

        ##Returns:
        * **(int):** Return status code.  One of the following:
            * 0 - Self-test initiated successfully
            * 1 - Previous self-test running. Must wait for it to finish.
            * 2 - Unknown or unsupported (by the device) test type requested.
            * 3 - Unspecified smartctl error. Self-test not initiated.
        * **(str):** Return status message.
        * **(str)/(float):** Estimated self-test completion time if a test is started.
        The optional argument of 'ETA_type' (see above) controls the return type.
        if 'ETA_type' == 'date' then a date string is returned else seconds(float)
        is returned.
        Note: The self-test completion time can only be obtained for ata devices.
        Otherwise 'None'.
        """
        # Lets call get_selftest_result() here since it does an update() and
        # checks for an existing selftest is running or not, this way the user
        # can issue a test from the cli and this can still pick that up
        # Also note that we do not need to obtain the results from this as the
        # data is already stored in the Device class object's variables
        self.get_selftest_result()
        if self._test_running:
            return (1, 'Self-test in progress. Please wait.', self._test_ECD)
        test_type = test_type.lower()
        interface = smartctl_type[self.interface]
        try:
            if not self.test_capabilities[test_type]:
                return (
                    2,
                    "Device {0} does not support the '{1}' test ".format(self.name, test_type),
                    None
                )
        except KeyError:
            return (2, "Unknown test type '{0}' requested.".format(test_type), None)
        cmd = Popen(
            [
                SMARTCTL_PATH,
                '-d',
                interface,
                '-t',
                test_type,
                os.path.join('/dev/', self.name)
            ],
            stdout=PIPE,
            stderr=PIPE
        )
        _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
        _success = False
        _running = False
        for line in _stdout.split('\n'):
            if 'has begun' in line:
                _success = True
                self._test_running = True
            if 'aborting current test' in line:
                _running = True
                try:
                    self._test_progress = 100 - int(line.split("(")[-1].split("%")[0])
                except ValueError:
                    pass

            if _success and 'complete after' in line:
                self._test_ECD = line[25:].rstrip()
                if ETA_type == 'seconds':
                    self._test_ECD = mktime(strptime(self._test_ECD, "%a %b %d %H:%M:%S %Y")) - time()
                self._test_progress = 0
        if _success:
            return (0, "Self-test started successfully", self._test_ECD)
        else:
            if _running:
                return (1, 'Self-test already in progress. Please wait.', self._test_ECD)
            else:
                return (3, 'Unspecified Error. Self-test not started.', None)

    def run_selftest_and_wait(self, test_type, output=None, polling=5, progress_handler=None):
        """
        This is essentially a wrapper around run_selftest() such that we
        call self.run_selftest() and wait on the running selftest till
        it finished before returning.
        The above holds true for all pySMART supported tests with the
        exception of the 'offline' test (ATA only) as it immediately
        returns, since the entire test only affects the smart error log
        (if any errors found) and updates the SMART attributes. Other
        than that it is not visibile anywhere else, so we start it and
        simply return.
        ##Args:
        * **test_type (str):** The type of test to run. Accepts the following
        (not case sensitive):
            * **short** - Brief electo-mechanical functionality check.
            Generally takes 2 minutes or less.
            * **long** - Thorough electro-mechanical functionality check,
            including complete recording media scan. Generally takes several
            hours.
            * **conveyance** - Brief test used to identify damage incurred in
            shipping. Generally takes 5 minutes or less. **This test is not
            supported by SAS or SCSI devices.**
            * **offline** - Runs SMART Immediate Offline Test. The effects of
            this test are visible only in that it updates the SMART Attribute
            values, and if errors are found they will appear in the SMART error
            log, visible with the '-l error' option to smartctl. **This test is
            not supported by SAS or SCSI devices in pySMART use cli smartctl for
            running 'offline' selftest (runs in foreground) on scsi devices.**
        * **output (str, optional):** If set to 'str', the string
            representation of the most recent test result will be returned,
            instead of a `Test_Entry` object.
        * **polling (int, default=5):** The time duration to sleep for between
            checking for test_results and progress.
        * **progress_handler (function, optional):** This if provided is called
            with self._test_progress as the supplied argument everytime a poll to
            check the status of the selftest is done.
        ##Returns:
        * **(int):** Return status code.  One of the following:
            * 0 - Self-test executed and finished successfully
            * 1 - Previous self-test running. Must wait for it to finish.
            * 2 - Unknown or illegal test type requested.
            * 3 - The Self-test was Aborted by host
            * 4 - Unspecified smartctl error. Self-test not initiated.
        * **(`Test_Entry` or str):** Most recent `Test_Entry` object (or
        optionally it's string representation) if new data exists.  Status
        message string on failure.
        """
        test_initiation_result = self.run_selftest(test_type)
        if test_initiation_result[0] != 0:
            return test_initiation_result[:2]
        if test_type == 'offline':
            # Since this test is not logged anywhere in the smart test log
            # lemme just go ahead and make a test_entry for it!
            # Note giving it num = 0 since I do not want to conflict with the test log
            local_test_entry = Test_Entry(
                'ata', 0, 'SMART Immediate Offline Test', 'Started: Successfully',
                self.attributes[9].raw, '-')
            if output == 'str':
                local_test_entry = str(local_test_entry)
            selftest_results = (0, local_test_entry)
            self._test_running = False
        else:
            # Lets set the default result just in case shit happens!
            selftest_results = (3, 'Unspecified Error. Self-test not run.', None)
        # if not then the test initiated correctly and we can start the polling.
        # For now default 'polling' value is 5 seconds if not specified by the user
        while self._test_running:
            selftest_results = self.get_selftest_result(output=output)
            if selftest_results[0] != 1:
                # the selftest is run and finished lets return with the results
                break
            # Otherwise see if we are provided with the progress_handler to update progress
            if progress_handler is not None:
                progress_handler(selftest_results[2] if selftest_results[2] is not None else 50)
            # Now sleep 'polling' seconds before checking the progress again
            sleep(polling)
        # Now if (selftes_results[0] == 2) i.e No new selftest (because the same
        # selftest was run twice within the last hour) but we know for a fact that
        # we just ran a new selftest then just return the latest entry in self.tests
        if selftest_results[0] == 2:
            selftest_return_value = 0 if 'Aborted' not in self.tests[0].status else 3
            return (selftest_return_value, str(self.tests[0]) if output == 'str' else self.tests[0])
        return selftest_results[:2]

    def update(self):
        """
        Queries for device information using smartctl and updates all
        class members, including the SMART attribute table and self-test log.
        Can be called at any time to refresh the `pySMART.device.Device`
        object's data content.
        """
        # set temperature back to None so that if update() is called more than once
        # any logic that relies on self.temperature to be None to rescan it works.it
        self.temperature = None
        if self.abridged:
            interface = None
            popen_list = [
                SMARTCTL_PATH,
                *self.smart_options,
                '-i',
                os.path.join('/dev/', self.name)
            ]
        else:
            interface = smartctl_type[self.interface]
            popen_list = [
                SMARTCTL_PATH,
                '-d',
                interface,
                *self.smart_options,
                '-a',
                os.path.join('/dev/', self.name)
            ]
        popen_list = list(filter(None, popen_list))
        logger.trace("Executing the following cmd: {0}".format(popen_list))
        cmd = Popen(popen_list, stdout=PIPE, stderr=PIPE)
        _stdout, _stderr = [i.decode('utf8', 'ignore') for i in cmd.communicate()]
        parse_self_tests = False
        parse_running_test = False
        parse_ascq = False
        message = ''
        self.tests = []
        self._test_running = False
        self._test_progress = None
        # Lets skip the first couple of non-useful lines
        _stdout = _stdout.split('\n')[4:]
        for line in _stdout:
            if line.strip() == '':  # Blank line stops sub-captures
                if parse_self_tests is True:
                    parse_self_tests = False
                    if len(self.tests) == 0:
                        self.tests = None
                if parse_ascq:
                    parse_ascq = False
                    self.messages.append(message)
            if parse_ascq:
                message += ' ' + line.lstrip().rstrip()
            if parse_self_tests:
                num = line[1:3]
                if '#' not in num:
                    continue
                if interface == 'scsi':
                    format = 'scsi'
                    test_type = line[5:23].rstrip()
                    status = line[23:46].rstrip()
                    segment = line[46:55].lstrip().rstrip()
                    hours = line[55:65].lstrip().rstrip()
                    LBA = line[65:78].lstrip().rstrip()
                    line_ = ' '.join(line.split('[')[1].split()).split(' ')
                    sense = line_[0]
                    ASC = line_[1]
                    ASCQ = line_[2][:-1]
                    self.tests.append(Test_Entry(
                        format,
                        num,
                        test_type,
                        status,
                        hours,
                        LBA,
                        segment=segment,
                        sense=sense,
                        ASC=ASC,
                        ASCQ=ASCQ
                    ))
                else:
                    format = 'ata'
                    test_type = line[5:25].rstrip()
                    status = line[25:54].rstrip()
                    remain = line[54:58].lstrip().rstrip()
                    hours = line[60:68].lstrip().rstrip()
                    LBA = line[77:].rstrip()
                    self.tests.append(
                        Test_Entry(format, num, test_type, status, hours, LBA, remain=remain)
                    )
            # Basic device information parsing
            if 'Device Model' in line or 'Product' in line or 'Model Number' in line:
                self.model = line.split(':')[1].lstrip().rstrip()
                self._guess_SMART_type(line.lower())
                continue
            if 'Model Family' in line:
                self._guess_SMART_type(line.lower())
                continue
            if 'LU WWN' in line:
                self._guess_SMART_type(line.lower())
                continue
            if 'Serial Number' in line or 'Serial number' in line:
                self.serial = line.split(':')[1].split()[0].rstrip()
                continue
            if 'Firmware Version' in line or 'Revision' in line:
                self.firmware = line.split(':')[1].lstrip().rstrip()
            if 'User Capacity' in line:
                self.capacity = (
                    line.replace(']', '[').split('[')[1].lstrip().rstrip())
            if 'SMART support' in line:
                # self.smart_capable = 'Available' in line
                # self.smart_enabled = 'Enabled' in line
                # Since this line repeats twice the above method is flawed
                # Lets try the following instead, it is a bit redundant but
                # more robust.
                if ('Unavailable' in line or 'device lacks SMART capability' in line):
                    self.smart_capable = False
                    self.smart_enabled = False
                elif 'Enabled' in line:
                    self.smart_enabled = True
                elif 'Disabled' in line:
                    self.smart_enabled = False
                elif ('Available' in line or 'device has SMART capability' in line):
                    self.smart_capable = True
                continue
            if 'does not support SMART' in line:
                self.smart_capable = False
                self.smart_enabled = False
                continue
            if 'Rotation Rate' in line:
                if 'Solid State Device' in line:
                    self.is_ssd = True
                elif 'rpm' in line:
                    self.is_ssd = False
                    try:
                        self.rotation_rate = int(line.split(':')[1].lstrip().rstrip()[:-4])
                    except ValueError:
                        # Cannot parse the RPM? Assigning None instead
                        self.rotation_rate = None
                continue

            if 'SMART overall-health self-assessment' in line:  # ATA devices
                if line.split(':')[1].strip() == 'PASSED':
                    self.assessment = 'PASS'
                else:
                    self.assessment = 'FAIL'
            if 'SMART Health Status' in line:  # SCSI devices
                if line.split(':')[1].strip() == 'OK':
                    self.assessment = 'PASS'
                else:
                    self.assessment = 'FAIL'
                    parse_ascq = True  # Set flag to capture status message
                    message = line.split(':')[1].lstrip().rstrip()
            # Parse SMART test capabilities (ATA only)
            # Note: SCSI does not list this but and allows for only 'offline', 'short' and 'long'
            if 'SMART execute Offline immediate' in line:
                self.test_capabilities['offline'] = False if 'No' in line else True
            if 'Self-test supported' in line:
                self.test_capabilities['short'] = False if 'No' in line else True
                self.test_capabilities['short'] = False if 'No' in line else True
            if 'Conveyance Self-test supported' in line:
                self.test_capabilities['conveyance'] = False if 'No' in line else True
            # Note: Currently I have not added any support in pySMART for selective Self-tests
            # Thus commenting it out
            # if 'Selective Self-test supported' in line:
            #     self.test_capabilities['selective'] = False if 'No' in line else True
            # SMART Attribute table parsing
            if '0x0' in line and '_' in line and not interface=='nvme':
                # Replace multiple space separators with a single space, then
                # tokenize the string on space delimiters
                line_ = ' '.join(line.split()).split(' ')
                if '' not in line_:
                    self.attributes[int(line_[0])] = Attribute(
                        line_[0], line_[1], line[2], line_[3], line_[4],
                        line_[5], line_[6], line_[7], line_[8], line_[9])
            # For some reason smartctl does not show a currently running test
            # for 'ATA' in the Test log so I just have to catch it this way i guess!
            # For 'scsi' I still do it since it is the only place I get % remaining in scsi
            if 'Self-test execution status' in line:
                if 'progress' in line:
                    self._test_running = True
                    # for ATA the "%" remaining is on the next line
                    # thus set the parse_running_test flag and move on
                    parse_running_test = True
                    continue
                elif '%' in line:
                    # for scsi the progress is on the same line
                    # so we can just parse it and move on
                    self._test_running = True
                    try:
                        self._test_progress = 100 - int(line.split("%")[0][-3:].strip())
                    except ValueError:
                        pass
            if parse_running_test is True:
                try:
                    self._test_progress = 100 - int(line.split("%")[0][-3:].strip())
                except ValueError:
                    pass
                parse_running_test = False
            if 'Description' in line and '(hours)' in line:
                parse_self_tests = True  # Set flag to capture test entries
            if 'No self-tests have been logged' in line:
                self.tests = None
            # Everything from here on is parsing SCSI information that takes
            # the place of similar ATA SMART information
            if 'used endurance' in line:
                pct = int(line.split(':')[1].strip()[:-1])
                self.diags['Life_Left'] = str(100 - pct) + '%'
            if 'Specified cycle count' in line:
                self.diags['Start_Stop_Spec'] = line.split(':')[1].strip()
                if self.diags['Start_Stop_Spec'] == '0':
                    self.diags['Start_Stop_Pct_Left'] = '-'
            if 'Accumulated start-stop cycles' in line:
                self.diags['Start_Stop_Cycles'] = line.split(':')[1].strip()
                if 'Start_Stop_Pct_Left' not in self.diags:
                    self.diags['Start_Stop_Pct_Left'] = str(int(round(
                        100 - (int(self.diags['Start_Stop_Cycles']) /
                               int(self.diags['Start_Stop_Spec'])), 0))) + '%'
            if 'Specified load-unload count' in line:
                self.diags['Load_Cycle_Spec'] = line.split(':')[1].strip()
                if self.diags['Load_Cycle_Spec'] == '0':
                    self.diags['Load_Cycle_Pct_Left'] = '-'
            if 'Accumulated load-unload cycles' in line:
                self.diags['Load_Cycle_Count'] = line.split(':')[1].strip()
                if 'Load_Cycle_Pct_Left' not in self.diags:
                    self.diags['Load_Cycle_Pct_Left'] = str(int(round(
                        100 - (int(self.diags['Load_Cycle_Count']) /
                               int(self.diags['Load_Cycle_Spec'])), 0))) + '%'
            if 'Elements in grown defect list' in line:
                self.diags['Reallocated_Sector_Ct'] = line.split(':')[1].strip()
            if 'read:' in line and interface == 'scsi':
                line_ = ' '.join(line.split()).split(' ')
                if (line_[1] == '0' and line_[2] == '0' and line_[3] == '0' and line_[4] == '0'):
                    self.diags['Corrected_Reads'] = '0'
                elif line_[4] == '0':
                    self.diags['Corrected_Reads'] = str(int(line_[1]) + int(line_[2]) + int(line_[3]))
                else:
                    self.diags['Corrected_Reads'] = line_[4]
                self.diags['Reads_GB'] = line_[6]
                self.diags['Uncorrected_Reads'] = line_[7]
            if 'write:' in line and interface == 'scsi':
                line_ = ' '.join(line.split()).split(' ')
                if (line_[1] == '0' and line_[2] == '0' and
                        line_[3] == '0' and line_[4] == '0'):
                    self.diags['Corrected_Writes'] = '0'
                elif line_[4] == '0':
                    self.diags['Corrected_Writes'] = str(int(line_[1]) + int(line_[2]) + int(line_[3]))
                else:
                    self.diags['Corrected_Writes'] = line_[4]
                self.diags['Writes_GB'] = line_[6]
                self.diags['Uncorrected_Writes'] = line_[7]
            if 'verify:' in line and interface == 'scsi':
                line_ = ' '.join(line.split()).split(' ')
                if (line_[1] == '0' and line_[2] == '0' and
                        line_[3] == '0' and line_[4] == '0'):
                    self.diags['Corrected_Verifies'] = '0'
                elif line_[4] == '0':
                    self.diags['Corrected_Verifies'] = str(int(line_[1]) + int(line_[2]) + int(line_[3]))
                else:
                    self.diags['Corrected_Verifies'] = line_[4]
                self.diags['Verifies_GB'] = line_[6]
                self.diags['Uncorrected_Verifies'] = line_[7]
            if 'non-medium error count' in line:
                self.diags['Non-Medium_Errors'] = line.split(':')[1].strip()
            if 'Accumulated power on time' in line:
                self.diags['Power_On_Hours'] = line.split(':')[1].split(' ')[1]
            if 'Current Drive Temperature' in line or ('Temperature' in line and interface =='nvme'):
                try:
                    self.temperature = int(line.split(':')[-1].strip().split()[0])
                except ValueError:
                    pass
        if not self.abridged:
            if not interface == 'scsi':
                # Parse the SMART table for below-threshold attributes and create
                # corresponding warnings for non-SCSI disks
                self._make_SMART_warnings()
            else:
                # For SCSI disks, any diagnostic attribute which was not captured
                # above gets set to '-' to indicate unsupported/unavailable.
                for diag in ['Corrected_Reads', 'Corrected_Writes',
                             'Corrected_Verifies', 'Uncorrected_Reads',
                             'Uncorrected_Writes', 'Uncorrected_Verifies',
                             'Reallocated_Sector_Ct',
                             'Start_Stop_Spec', 'Start_Stop_Cycles',
                             'Load_Cycle_Spec', 'Load_Cycle_Count',
                             'Start_Stop_Pct_Left', 'Load_Cycle_Pct_Left',
                             'Power_On_Hours', 'Life_Left', 'Non-Medium_Errors',
                             'Reads_GB', 'Writes_GB', 'Verifies_GB']:
                    if diag not in self.diags:
                        self.diags[diag] = '-'
                # If not obtained above, make a direct attempt to extract power on
                # hours from the background scan results log.
                if self.diags['Power_On_Hours'] == '-':
                    cmd = Popen(
                        [
                            SMARTCTL_PATH,
                            '-d',
                            'scsi',
                            '-l',
                            'background',
                            os.path.join('/dev/', self.name)
                        ],
                        stdout=PIPE,
                        stderr=PIPE
                    )
                    _stdout, _stderr = [i.decode('utf8') for i in cmd.communicate()]
                    for line in _stdout.split('\n'):
                        if 'power on time' in line:
                            self.diags['Power_On_Hours'] = line.split(':')[1].split(' ')[1]
        # map temperature
        if self.temperature is None:
            # in this case the disk is probably ata
            try:
                # Some disks report temperature to attribute number 190 ('Airflow_Temperature_Cel')
                # see https://bugs.freenas.org/issues/20860
                temp_attr = self.attributes[194] or self.attributes[190]
                self.temperature = int(temp_attr.raw)
            except (ValueError, AttributeError):
                pass
        # Now that we have finished the update routine, if we did not find a runnning selftest
        # nuke the self._test_ECD and self._test_progress
        if self._test_running is False:
            self._test_ECD = None
            self._test_progress = None

__all__ = ['Device', 'smart_health_assement']
