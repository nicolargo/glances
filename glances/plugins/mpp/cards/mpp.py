#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#


from dataclasses import dataclass


@dataclass
class MPPStats:
    """Container for a single MPP engine's statistics."""

    def __init__(self):
        self.engine_id: str = "unknown"
        self.name: str = "unknown"
        self.type: str = "unknown"
        self.load: float | None = None
        self.utilization: float | None = None
        self.sessions: int = 0
