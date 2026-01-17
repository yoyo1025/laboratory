from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException
import time
from logging_utils import logger, SERVER_START_TS

CLOUD_BUCKET = "cloud-point-cloud"
NOT_FOUND_CODES = {"NoSuchKey", "NoSuchObject", "NotFound", "NoSuchBucket"}

class StreamUsecase:
  def __init__(self, mc: Minio, key: str):
    self.mc = mc
    self.key = key
  def _is_not_found(self, err: S3Error) -> bool:
    return err.code in NOT_FOUND_CODES
  def _log_retention(self, name: str, start: float, end: float) -> None:
    start_since = int(start - SERVER_START_TS)
    end_since = int(end - SERVER_START_TS)
    logger.info(f"retention_{name},{start_since},1")
    logger.info(f"retention_{name},{end_since},-1")
  def stream(self):
    start = time.perf_counter()
    try:
      st = self.mc.stat_object(CLOUD_BUCKET, self.key)
    except S3Error as e:
      end = time.perf_counter()
      elapsed = end - start
      if self._is_not_found(e):
        self._log_retention("stream.cloud_get_miss", start, end)
        logger.info("processed_time_%s: %.5f", "stream.cloud_get_miss", elapsed)
        raise HTTPException(status_code=404, detail="point cloud not found")
      self._log_retention("stream.cloud_get_error", start, end)
      raise
    
    try:
      obj = self.mc.get_object(CLOUD_BUCKET, self.key)
    except S3Error as e:
      end = time.perf_counter()
      self._log_retention("stream.cloud_get_error", start, end)
      raise HTTPException(status_code=502, detail=f"failed to read object: {e.code}")

    end = time.perf_counter()
    elapsed = end - start
    self._log_retention("stream.cloud_get_hit", start, end)
    logger.info("processed_time_%s: %.5f", "stream.cloud_get_hit", elapsed)
    return obj, st
