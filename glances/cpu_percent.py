#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""CPU percent stats shared between CPU and Quicklook plugins."""

import platform
from typing import TypedDict

import psutil

from glances.logger import logger
from glances.timer import Timer

__all__ = ["cpu_percent"]

CPU_IMPLEMENTERS = {
    0x41: 'ARM Limited',
    0x42: 'Broadcom',
    0x43: 'Cavium',
    0x44: 'DEC',
    0x46: 'Fujitsu',
    0x48: 'HiSilicon',
    0x49: 'Infineon Technologies',
    0x4D: 'Motorola/Freescale',
    0x4E: 'NVIDIA',
    0x50: 'Applied Micro (APM)',
    0x51: 'Qualcomm',
    0x53: 'Samsung',
    0x56: 'Marvell',
    0x61: 'Apple',
    0x66: 'Faraday',
    0x69: 'Intel',
    0x6D: 'Microsoft',
    0x70: 'Phytium',
    0xC0: 'Ampere Computing',
}

CPU_PARTS = {
    # ARM Limited (0x41)
    0x41: {
        0xD03: 'Cortex-A53',
        0xD04: 'Cortex-A35',
        0xD05: 'Cortex-A55',
        0xD06: 'Cortex-A65',
        0xD07: 'Cortex-A57',
        0xD08: 'Cortex-A72',
        0xD09: 'Cortex-A73',
        0xD0A: 'Cortex-A75',
        0xD0B: 'Cortex-A76',
        0xD0C: 'Neoverse N1',
        0xD0D: 'Cortex-A77',
        0xD0E: 'Cortex-A76AE',
        0xD13: 'Cortex-R52',
        0xD20: 'Cortex-M23',
        0xD21: 'Cortex-M33',
        0xD40: 'Neoverse V1',
        0xD41: 'Cortex-A78',
        0xD42: 'Cortex-A78AE',
        0xD43: 'Cortex-A65AE',
        0xD44: 'Cortex-X1',
        0xD46: 'Cortex-A510',
        0xD47: 'Cortex-A710',
        0xD48: 'Cortex-X2',
        0xD49: 'Neoverse N2',
        0xD4A: 'Neoverse E1',
        0xD4B: 'Cortex-A78C',
        0xD4C: 'Cortex-X1C',
        0xD4D: 'Cortex-A715',
        0xD4E: 'Cortex-X3',
        0xD4F: 'Neoverse V2',
        0xD80: 'Cortex-A520',
        0xD81: 'Cortex-A720',
        0xD82: 'Cortex-X4',
        0xD84: 'Neoverse V3',
        0xD85: 'Cortex-X925',
        0xD87: 'Cortex-A725',
    },
    # Apple (0x61)
    0x61: {
        0x000: 'Swift',
        0x001: 'Cyclone',
        0x002: 'Typhoon',
        0x003: 'Twister',
        0x004: 'Hurricane',
        0x005: 'Monsoon/Mistral',
        0x006: 'Vortex/Tempest',
        0x007: 'Lightning/Thunder',
        0x008: 'Firestorm/Icestorm (M1)',
        0x009: 'Avalanche/Blizzard (M2)',
        0x00E: 'Everest/Sawtooth (M3)',
        0x010: 'Blizzard/Avalanche (A16)',
        0x011: 'Coll (M4)',
    },
    # Qualcomm (0x51)
    0x51: {
        0x00F: 'Scorpion',
        0x02D: 'Scorpion',
        0x04D: 'Krait',
        0x06F: 'Krait',
        0x201: 'Kryo',
        0x205: 'Kryo',
        0x211: 'Kryo',
        0x800: 'Kryo 260/280 Gold (Cortex-A73)',
        0x801: 'Kryo 260/280 Silver (Cortex-A53)',
        0x802: 'Kryo 385 Gold (Cortex-A75)',
        0x803: 'Kryo 385 Silver (Cortex-A55)',
        0x804: 'Kryo 485 Gold (Cortex-A76)',
        0x805: 'Kryo 485 Silver (Cortex-A55)',
        0xC00: 'Falkor',
        0xC01: 'Saphira',
    },
    # Samsung (0x53)
    0x53: {
        0x001: 'Exynos M1/M2',
        0x002: 'Exynos M3',
        0x003: 'Exynos M4',
        0x004: 'Exynos M5',
    },
    # NVIDIA (0x4e)
    0x4E: {
        0x000: 'Denver',
        0x003: 'Denver 2',
        0x004: 'Carmel',
    },
    # Marvell (0x56)
    0x56: {
        0x131: 'Feroceon 88FR131',
        0x581: 'PJ4/PJ4b',
        0x584: 'PJ4B-MP',
    },
    # Cavium (0x43)
    0x43: {
        0x0A0: 'ThunderX',
        0x0A1: 'ThunderX 88XX',
        0x0A2: 'ThunderX 81XX',
        0x0A3: 'ThunderX 83XX',
        0x0AF: 'ThunderX2 99xx',
        0x0B0: 'OcteonTX2',
        0x0B1: 'OcteonTX2 T98',
        0x0B2: 'OcteonTX2 T96',
        0x0B3: 'OcteonTX2 F95',
        0x0B4: 'OcteonTX2 F95N',
        0x0B5: 'OcteonTX2 F95MM',
    },
    # Broadcom (0x42)
    0x42: {
        0x00F: 'Brahma B15',
        0x100: 'Brahma B53',
        0x516: 'Vulcan',
    },
    # HiSilicon (0x48)
    0x48: {
        0xD01: 'Kunpeng-920',
        0xD40: 'Cortex-A76 (Kirin)',
    },
    # Ampere (0xc0)
    0xC0: {
        0xAC3: 'Ampere-1',
        0xAC4: 'Ampere-1a',
    },
    # Fujitsu (0x46)
    0x46: {
        0x001: 'A64FX',
    },
    # Intel (0x69) - ARM-based chips
    0x69: {
        0x200: 'i80200',
        0x210: 'PXA250A',
        0x212: 'PXA210A',
        0x242: 'i80321-400',
        0x243: 'i80321-600',
        0x290: 'PXA250B/PXA26x',
        0x292: 'PXA210B',
        0x2C2: 'i80321-400-B0',
        0x2C3: 'i80321-600-B0',
        0x2D0: 'PXA250C/PXA255/PXA26x',
        0x2D2: 'PXA210C',
        0x411: 'PXA27x',
        0x41C: 'IPX425-533',
        0x41D: 'IPX425-400',
        0x41F: 'IPX425-266',
        0x682: 'PXA32x',
        0x683: 'PXA930/PXA935',
        0x688: 'PXA30x',
        0x689: 'PXA31x',
    },
}


class CpuInfo(TypedDict):
    cpu_name: str
    cpu_hz: float | None
    cpu_hz_current: float | None


class PerCpuPercentInfo(TypedDict):
    key: str
    cpu_number: int
    total: float
    user: float
    system: float
    idle: float
    nice: float | None
    iowait: float | None
    irq: float | None
    softirq: float | None
    steal: float | None
    guest: float | None
    guest_nice: float | None
    dpc: float | None
    interrupt: float | None


class CpuPercent:
    """Get and store the CPU percent."""

    def __init__(self, cached_timer_cpu: int = 2):
        # cached_timer_cpu is the minimum time interval between stats updates
        # since last update is passed (will retrieve old cached info instead)
        self.cached_timer_cpu = cached_timer_cpu
        # psutil.cpu_freq() consumes lots of CPU
        # So refresh CPU frequency stats every refresh * 2
        self.cached_timer_cpu_info = cached_timer_cpu * 2

        # Get CPU name
        self.timer_cpu_info = Timer(0)
        self.cpu_info: CpuInfo = {'cpu_name': self.__get_cpu_name(), 'cpu_hz_current': None, 'cpu_hz': None}

        # Warning from PsUtil documentation
        # The first time this function is called with interval = 0.0 or None
        # it will return a meaningless 0.0 value which you are supposed to ignore.
        self.timer_cpu = Timer(0)
        self.cpu_percent = self._compute_cpu()
        self.timer_percpu = Timer(0)
        self.percpu_percent = self._compute_percpu()

    def get_key(self):
        """Return the key of the per CPU list."""
        return 'cpu_number'

    def get_info(self) -> CpuInfo:
        """Get additional information about the CPU"""
        # Never update more than 1 time per cached_timer_cpu_info
        if self.timer_cpu_info.finished() and hasattr(psutil, 'cpu_freq'):
            # Get the CPU freq current/max
            try:
                cpu_freq = psutil.cpu_freq()
            except Exception as e:
                logger.debug(f'Can not grab CPU information ({e})')
            else:
                if hasattr(cpu_freq, 'current'):
                    self.cpu_info['cpu_hz_current'] = cpu_freq.current
                else:
                    self.cpu_info['cpu_hz_current'] = None
                if hasattr(cpu_freq, 'max') and cpu_freq.max != 0.0:
                    self.cpu_info['cpu_hz'] = cpu_freq.max
                else:
                    self.cpu_info['cpu_hz'] = None
                # Reset timer for cache
                self.timer_cpu_info.reset(duration=self.cached_timer_cpu_info)
        return self.cpu_info

    @staticmethod
    def __get_cpu_name() -> str:
        # Get the CPU name once from the /proc/cpuinfo file
        # Read the first line with the "model name" ("Model" for Raspberry Pi)
        ret = f'CPU {platform.processor()}'
        try:
            cpuinfo_lines = open('/proc/cpuinfo').readlines()
        except (FileNotFoundError, PermissionError):
            logger.debug("No permission to read '/proc/cpuinfo'")
            return ret

        cpu_implementer = None
        for line in cpuinfo_lines:
            # Look for the CPU name
            if line.startswith('model name') or line.startswith('Model') or line.startswith('cpu model'):
                return line.split(':')[1].strip()
            # Look for the CPU name on ARM architecture (see #3127)
            if line.startswith('CPU implementer'):
                cpu_implementer = CPU_IMPLEMENTERS.get(int(line.split(':')[1].strip(), 16), ret)
                ret = cpu_implementer
            if line.startswith('CPU part') and cpu_implementer in CPU_PARTS:
                cpu_part = CPU_PARTS[cpu_implementer].get(int(line.split(':')[1].strip(), 16), 'Unknown')
                ret = f'{cpu_implementer} {cpu_part}'

        return ret

    def get_cpu(self) -> float:
        """Update and/or return the CPU using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_cpu.finished():
            # Reset timer for cache
            self.timer_cpu.reset(duration=self.cached_timer_cpu)
            # Update the stats
            self.cpu_percent = self._compute_cpu()
        return self.cpu_percent

    @staticmethod
    def _compute_cpu() -> float:
        return psutil.cpu_percent(interval=0.0)

    def get_percpu(self) -> list[PerCpuPercentInfo]:
        """Update and/or return the per CPU list using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_percpu.finished():
            # Reset timer for cache
            self.timer_percpu.reset(duration=self.cached_timer_cpu)
            # Update stats
            self.percpu_percent = self._compute_percpu()
        return self.percpu_percent

    def _compute_percpu(self) -> list[PerCpuPercentInfo]:
        psutil_percpu = enumerate(psutil.cpu_times_percent(interval=0.0, percpu=True))
        return [
            {
                'key': self.get_key(),
                'cpu_number': cpu_number,
                'total': round(100 - cpu_times.idle, 1),
                'user': cpu_times.user,
                'system': cpu_times.system,
                'idle': cpu_times.idle,
                'nice': cpu_times.nice if hasattr(cpu_times, 'nice') else None,
                'iowait': cpu_times.iowait if hasattr(cpu_times, 'iowait') else None,
                'irq': cpu_times.irq if hasattr(cpu_times, 'irq') else None,
                'softirq': cpu_times.softirq if hasattr(cpu_times, 'softirq') else None,
                'steal': cpu_times.steal if hasattr(cpu_times, 'steal') else None,
                'guest': cpu_times.guest if hasattr(cpu_times, 'guest') else None,
                'guest_nice': cpu_times.steal if hasattr(cpu_times, 'guest_nice') else None,
                'dpc': cpu_times.dpc if hasattr(cpu_times, 'dpc') else None,
                'interrupt': cpu_times.interrupt if hasattr(cpu_times, 'interrupt') else None,
            }
            for cpu_number, cpu_times in psutil_percpu
        ]


# CpuPercent instance shared between plugins
cpu_percent = CpuPercent()
