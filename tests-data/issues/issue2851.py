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

refresh = 2
iteration = 6
pid = os.getpid()
process = psutil.Process(pid)

print("Check Glances sensors plugin CPU consumption overhead")
print("=====================================================")
print()

print(f"Init Glances to make the stats more relevant (wait {iteration * refresh} seconds)")
for i in range(0, iteration):
    stats.update()
    time.sleep(refresh)

print("CPU consumption with sensors plugin disable")
disable(stats.get_plugin('sensors').args, 'sensors')
stats.get_plugin('sensors').reset()
cpu_start = sum(process.cpu_times()[:2])
for i in range(0, iteration):
    stats.update()
    print(f'{i + 1}/{iteration}: {len(stats.get_plugin("sensors").get_raw())} sensor')
    time.sleep(refresh)
cpu_end = sum(process.cpu_times()[:2])
cpu_without_sensors = cpu_end - cpu_start
print(f'Glances process consumption (user + kernel) with sensors plugin disable: {cpu_without_sensors}')

print("CPU consumption with sensors plugin enable")
enable(stats.get_plugin('sensors').args, 'sensors')
stats.get_plugin('sensors').reset()
cpu_start = sum(process.cpu_times()[:2])
for i in range(0, iteration):
    stats.update()
    print(f'{i + 1}/{iteration}: {len(stats.get_plugin("sensors").get_raw())} sensors')
    time.sleep(refresh)
cpu_end = sum(process.cpu_times()[:2])
cpu_with_sensors = cpu_end - cpu_start
print(f'Glances process consumption (user + kernel) with sensors plugin enable: {cpu_with_sensors}')

print(
    f'Percentage of CPU consumption increase with sensors plugin enable: \
 {((cpu_with_sensors - cpu_without_sensors) / cpu_without_sensors) * 100:.2f}%'
)
