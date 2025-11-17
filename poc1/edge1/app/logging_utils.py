import logging
import time
from contextlib import contextmanager


logger = logging.getLogger("edge1.app")
logger.setLevel(logging.INFO)


@contextmanager
def log_duration(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("%s: %.3fs", name, elapsed)
