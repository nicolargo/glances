#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#


from dataclasses import dataclass


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
