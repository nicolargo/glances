import time
from multiprocessing import Process, Queue

import psutil


def exit_after(seconds, default=None):
    """Exit the function if it takes more than 'second' seconds to complete.
    In this case, return the value of 'default' (default: None)."""

    def handler(q, func, args, kwargs):
        q.put(func(*args, **kwargs))

    def decorator(func):
        def wraps(*args, **kwargs):
            q = Queue()
            p = Process(target=handler, args=(q, func, args, kwargs))
            p.start()
            p.join(timeout=seconds)
            if p.is_alive():
                p.terminate()
                p.join()
                return default
            return q.get()

        return wraps

    return decorator


class Issue3290:
    @exit_after(1, default=None)
    def blocking_io_call(self, fs):
        try:
            return psutil.disk_usage(fs)
        except OSError:
            return None


issue = Issue3290()
while True:
    print(f"{time.time()} {issue.blocking_io_call('/home/nicolargo/tmp/hang')}")
    time.sleep(1)
