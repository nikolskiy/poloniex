import time
import threading
from functools import wraps


def rate_limited(max_per_second: int):
    """
    Rate limiting decorator inspired by
    https://gist.github.com/gregburek/1441055
    """
    lock = threading.Lock()
    min_interval = 1.0 / max_per_second

    def decorate(func):
        last_time_called = time.perf_counter()

        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            lock.acquire()
            nonlocal last_time_called
            elapsed = time.perf_counter() - last_time_called
            left_to_wait = min_interval - elapsed

            if left_to_wait > 0:
                time.sleep(left_to_wait)

            try:
                ret = func(*args, **kwargs)
            finally:
                last_time_called = time.perf_counter()
                lock.release()
            return ret

        return rate_limited_function

    return decorate

