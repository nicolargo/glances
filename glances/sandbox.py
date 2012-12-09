#!/usr/bin/env python

import psutil
import time

psutil_get_cpu_percent_tag = True
psutil_get_io_counter_tag = True

class GlancesGrabProcesses:
    """
    Get processed stats using the PsUtil lib
    """

    def __get_process_stats__(self, proc):
        """
        Get process (proc) statistics
        """
        procstat = {}
        
        procstat['memory_info'] = proc.get_memory_info()

        if psutil_get_cpu_percent_tag:
            procstat['cpu_percent'] = \
                proc.get_cpu_percent(interval=0)

        procstat['memory_percent'] = proc.get_memory_percent()

        try:
            if psutil_get_io_counter_tag:
                procstat['io_counters'] = proc.get_io_counters()
        except:
            procstat['io_counters'] = {}

        procstat['pid'] = proc.pid
        procstat['username'] = proc.username

        if hasattr(proc, 'get_nice'):
            procstat['nice'] = proc.get_nice()
        elif hasattr(proc, 'nice'):
            procstat['nice'] = proc.nice

        procstat['status'] = str(proc.status)[:1].upper()
        procstat['cpu_times'] = proc.get_cpu_times()
        procstat['name'] = proc.name
        procstat['cmdline'] = " ".join(proc.cmdline)

        return procstat

    
    def update(self):
        self.processlist = []
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0}

        for proc in psutil.process_iter():
            # Update processlist
            self.processlist.append(self.__get_process_stats__(proc))
            #~ self.processlist.append(proc)
            # Update processcount
            try:
                self.processcount[str(proc.status)] += 1
            except KeyError:
                # Key did not exist, create it
                self.processcount[str(proc.status)] = 1
            self.processcount['total'] += 1


    def getcount(self):
        return self.processcount

    
    def getlist(self):
        return self.processlist


if __name__ == "__main__":
    while True:
        p = GlancesGrabProcesses()
        p.update()
        print p.getlist()
        print p.getcount()
        time.sleep(1)

