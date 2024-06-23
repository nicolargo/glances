import sys
import time

sys.path.insert(0, '../glances')

###########

# from glances.cpu_percent import cpu_percent

# for _ in range(0, 5):
#     print([i['total'] for i in cpu_percent.get_percpu()])
#     time.sleep(2)

###########

from glances.main import GlancesMain
from glances.stats import GlancesStats

core = GlancesMain()
stats = GlancesStats(config=core.get_config(), args=core.get_args())

for _ in range(0, 5):
    stats.update()
    print([i['total'] for i in stats.get_plugin('percpu').get_raw()])
    time.sleep(2)
