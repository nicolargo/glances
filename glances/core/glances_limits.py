#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

# !!!
# Each plugin define its limits
# This class only browse all plugin and propose 
# an API interface to display all the limits
# /!!!


class glancesLimits:
    """
    Manage limits for each stats. A limit can be:
    * a set of careful, warning and critical values
    * a filter (for example: hide some network interfaces)

    The limit list is stored in an hash table:
    __limits_list[STAT] = [CAREFUL, WARNING, CRITICAL]

    STD is for defaults limits (CPU/MEM/SWAP/FS)
    CPU_IOWAIT limits (iowait in %)
    CPU_STEAL limits (steal in %)
    LOAD is for LOAD limits (5 min/15 min)
    TEMP is for sensors limits (temperature in °C)
    HDDTEMP is for hddtemp limits (temperature in °C)
    FS is for partitions space limits
    IODISK_HIDE is a list of disk (name) to hide
    NETWORK_HIDE is a list of network interface (name) to hide
    """
    __limits_list = {'STD': [50, 70, 90],
                     'CPU_USER': [50, 70, 90],
                     'CPU_SYSTEM': [50, 70, 90],
                     'CPU_IOWAIT': [40, 60, 80],
                     'CPU_STEAL': [10, 15, 20],
                     'LOAD': [0.7, 1.0, 5.0],
                     'MEM': [50, 70, 90],
                     'SWAP': [50, 70, 90],
                     'TEMP': [60, 70, 80],
                     'HDDTEMP': [45, 52, 60],
                     'FS': [50, 70, 90],
                     'PROCESS_CPU': [50, 70, 90],
                     'PROCESS_MEM': [50, 70, 90],
                     'IODISK_HIDE': [],
                     'NETWORK_HIDE': []}

    def __init__(self, config):
        """
        Init the limits with: default values and configuration file
        """

        self.config = config

        # Test if the configuration file has a limits section
        if config.has_section('global'):
            # Read STD limits
            self.__setLimits('STD', 'global', 'careful')
            self.__setLimits('STD', 'global', 'warning')
            self.__setLimits('STD', 'global', 'critical')
        if config.has_section('cpu'):
            # Read CPU limits
            self.__setLimits('CPU_USER', 'cpu', 'user_careful')
            self.__setLimits('CPU_USER', 'cpu', 'user_warning')
            self.__setLimits('CPU_USER', 'cpu', 'user_critical')
            self.__setLimits('CPU_SYSTEM', 'cpu', 'system_careful')
            self.__setLimits('CPU_SYSTEM', 'cpu', 'system_warning')
            self.__setLimits('CPU_SYSTEM', 'cpu', 'system_critical')
            self.__setLimits('CPU_IOWAIT', 'cpu', 'iowait_careful')
            self.__setLimits('CPU_IOWAIT', 'cpu', 'iowait_warning')
            self.__setLimits('CPU_IOWAIT', 'cpu', 'iowait_critical')
            self.__setLimits('CPU_STEAL', 'cpu', 'steal_careful')
            self.__setLimits('CPU_STEAL', 'cpu', 'steal_warning')
            self.__setLimits('CPU_STEAL', 'cpu', 'steal_critical')
        if config.has_section('load'):
            # Read LOAD limits
            self.__setLimits('LOAD', 'load', 'careful')
            self.__setLimits('LOAD', 'load', 'warning')
            self.__setLimits('LOAD', 'load', 'critical')
        if config.has_section('memory'):
            # Read MEM limits
            self.__setLimits('MEM', 'memory', 'careful')
            self.__setLimits('MEM', 'memory', 'warning')
            self.__setLimits('MEM', 'memory', 'critical')
        if config.has_section('swap'):
            # Read MEM limits
            self.__setLimits('SWAP', 'swap', 'careful')
            self.__setLimits('SWAP', 'swap', 'warning')
            self.__setLimits('SWAP', 'swap', 'critical')
        if config.has_section('temperature'):
            # Read TEMP limits
            self.__setLimits('TEMP', 'temperature', 'careful')
            self.__setLimits('TEMP', 'temperature', 'warning')
            self.__setLimits('TEMP', 'temperature', 'critical')
        if config.has_section('hddtemperature'):
            # Read HDDTEMP limits
            self.__setLimits('HDDTEMP', 'hddtemperature', 'careful')
            self.__setLimits('HDDTEMP', 'hddtemperature', 'warning')
            self.__setLimits('HDDTEMP', 'hddtemperature', 'critical')
        if config.has_section('filesystem'):
            # Read FS limits
            self.__setLimits('FS', 'filesystem', 'careful')
            self.__setLimits('FS', 'filesystem', 'warning')
            self.__setLimits('FS', 'filesystem', 'critical')
        if config.has_section('process'):
            # Process limits
            self.__setLimits('PROCESS_CPU', 'process', 'cpu_careful')
            self.__setLimits('PROCESS_CPU', 'process', 'cpu_warning')
            self.__setLimits('PROCESS_CPU', 'process', 'cpu_critical')
            self.__setLimits('PROCESS_MEM', 'process', 'mem_careful')
            self.__setLimits('PROCESS_MEM', 'process', 'mem_warning')
            self.__setLimits('PROCESS_MEM', 'process', 'mem_critical')
        if config.has_section('iodisk'):
            # Hidden disks' list
            self.__setHidden('IODISK_HIDE', 'iodisk', 'hide')
        if config.has_section('network'):
            # Network interfaces' list
            self.__setHidden('NETWORK_HIDE', 'network', 'hide')

    def __setHidden(self, stat, section, alert='hide'):
        """
        stat: 'IODISK', 'NETWORK'
        section: 'iodisk', 'network'
        alert: 'hide'
        """
        value = self.config.get_raw_option(section, alert)

        # print("%s / %s = %s -> %s" % (section, alert, value, stat))
        if (value is not None):
            self.__limits_list[stat] = value.split(",")

    def __setLimits(self, stat, section, alert):
        """
        stat: 'CPU', 'LOAD', 'MEM', 'SWAP', 'TEMP', etc.
        section: 'cpu', 'load', 'memory', 'swap', 'temperature', etc.
        alert: 'careful', 'warning', 'critical'
        """
        value = self.config.get_option(section, alert)

        # print("%s / %s = %s -> %s" % (section, alert, value, stat))
        if alert.endswith('careful'):
            self.__limits_list[stat][0] = value
        elif alert.endswith('warning'):
            self.__limits_list[stat][1] = value
        elif alert.endswith('critical'):
            self.__limits_list[stat][2] = value

    def setAll(self, newlimits):
        self.__limits_list = newlimits
        return True

    def getAll(self):
        return self.__limits_list

    def getHide(self, stat):
        try:
            self.__limits_list[stat]
        except KeyError:
            return []
        else:
            return self.__limits_list[stat]

    def getCareful(self, stat):
        return self.__limits_list[stat][0]

    def getWarning(self, stat):
        return self.__limits_list[stat][1]

    def getCritical(self, stat):
        return self.__limits_list[stat][2]
