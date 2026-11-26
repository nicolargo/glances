#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#


import os
from dataclasses import dataclass

from glances.logger import logger


@dataclass
class NPUStats:
    """Container for NPU statistics"""

    def __init__(self):
        self.npu_id: str = "unknown"
        self.name: str = "unknown"
        self.load: int | None = None
        self.freq: int | None = None
        self.freq_current: int | None = None
        self.freq_max: int | None = None
        self.mem: int | None = None
        self.memory_used: int | None = None
        self.memory_total: int | None = None
        self.temperature: float | None = None
        self.power: float | None = None


def read_npu_file(path: str, as_int: bool = False) -> int | str | None:
    """Safely read a sysfs value, as an int when as_int is set."""
    try:
        if os.path.exists(path):
            with open(path) as f:
                if as_int:
                    return int(f.read().strip())
                return f.read().strip()
    except (OSError, ValueError) as e:
        logger.error(f"NPU - Error reading file {path}: {e}")
    return None
