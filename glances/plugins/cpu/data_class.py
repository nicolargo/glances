from typing import Optional

from glances.data_class import GlancesStatsModel


class Stats(GlancesStatsModel):
    total: Optional[float] = None
    system: Optional[float] = None
    user: Optional[float] = None
    iowait: Optional[float] = None
    dpc: Optional[float] = None
    idle: Optional[float] = None
    irq: Optional[float] = None
    nice: Optional[float] = None
    steal: Optional[float] = None
    guest: Optional[float] = None
    ctx_switches: Optional[int] = None
    interrupt: Optional[int] = None
    soft_interrupts: Optional[int] = None
    syscalls: Optional[int] = None
    cpucore: Optional[int] = None

    # Do no work...
    def __post_init__(self):
        self.name = 'cpu'
        self.description = 'CPU stats'
