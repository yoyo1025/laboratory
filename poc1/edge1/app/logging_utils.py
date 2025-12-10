import logging
import sys
import time
from contextlib import contextmanager


SERVER_START_TS = time.perf_counter()

logger = logging.getLogger("edge1.app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.propagate = False



@contextmanager
def log_duration(name: str):
    start = time.perf_counter()
    since_start = int(time.perf_counter() - SERVER_START_TS)
    # name の処理を開始（滞留調査）
    logger.info(f"retention_{name},{since_start},1")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        since_start = int(time.perf_counter() - SERVER_START_TS)
        # name の処理時間
        logger.info("%s: %.5f", name, elapsed)
        # name の処理を終了（滞留調査）
        logger.info(f"retention_{name},{since_start},-1")
