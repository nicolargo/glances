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

print("Check Glances process* plugins CPU consumption overhead")
print("=======================================================")
print()

print(f"Init Glances to make the stats more relevant (wait {iteration * refresh} seconds)")
for i in range(0, iteration):
    stats.update()
    time.sleep(refresh)

print("CPU consumption with process* plugins disable")
for p in ['processcount', 'processlist', 'programlist']:
    disable(stats.get_plugin(p).args, p)
    stats.get_plugin(p).reset()
cpu_start = sum(process.cpu_times()[:2])
for i in range(0, iteration):
    stats.update()
    print(f'{i + 1}/{iteration}')
    time.sleep(refresh)
cpu_end = sum(process.cpu_times()[:2])
cpu_without_sensors = cpu_end - cpu_start
print(f'Glances process consumption (user + kernel) with process* plugins disable: {cpu_without_sensors}')

print("CPU consumption with process* plugins enable")
for p in ['processcount', 'processlist', 'programlist']:
    enable(stats.get_plugin(p).args, p)
    stats.get_plugin(p).reset()
cpu_start = sum(process.cpu_times()[:2])
for i in range(0, iteration):
    stats.update()
    print(f'{i + 1}/{iteration}: {len(stats.get_plugin("processlist").get_raw())} processes')
    time.sleep(refresh)
cpu_end = sum(process.cpu_times()[:2])
cpu_with_sensors = cpu_end - cpu_start
print(f'Glances process consumption (user + kernel) with process* plugins enable: {cpu_with_sensors}')

print(
    f'Percentage of CPU consumption increase with process* plugins enable: \
 {((cpu_with_sensors - cpu_without_sensors) / cpu_without_sensors) * 100:.2f}%'
)
