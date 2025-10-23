import os
import sys
import time

import psutil

sys.path.insert(0, '../glances')

from glances.globals import disable, enable
from glances.main import GlancesMain
from glances.stats import GlancesStats

core = GlancesMain()
stats = GlancesStats(config=core.get_config(), args=core.get_args())

iteration = 6
pid = os.getpid()
process = psutil.Process(pid)

print(f"Init Glances to make the stats more relevant (wait {iteration} seconds)")
for i in range(0, iteration):
    stats.update()
    time.sleep(1)

disable(stats.get_plugin('sensors').args, 'sensors')
print("CPU consumption with sensors plugin disable")
process.cpu_percent()
stats.get_plugin('sensors').reset()
for i in range(0, iteration):
    stats.update()
    print(f'{i + 1}/{iteration}: {len(stats.get_plugin("sensors").get_raw())} sensor')
    time.sleep(1)
print(f'CPU consumption with sensors plugin disable: {process.cpu_percent()}')

enable(stats.get_plugin('sensors').args, 'sensors')
print("CPU consumption with sensors plugin enable")
process.cpu_percent()
stats.get_plugin('sensors').reset()
for i in range(0, iteration):
    stats.update()
    print(f'{i + 1}/{iteration}: {len(stats.get_plugin("sensors").get_raw())} sensors')
    time.sleep(1)
print(f'CPU consumption with sensors plugin enable: {process.cpu_percent()}')
