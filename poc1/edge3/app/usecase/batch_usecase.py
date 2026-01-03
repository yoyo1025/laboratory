from repository.batch_repository import BatchRepository
import os, asyncio
from minio import Minio
from logging_utils import logger

SYNC_INTERVAL_SEC = int(os.getenv("SYNC_INTERVAL_SEC", "30"))
CLOUD_BUCKET = "cloud-point-cloud"

class BatchUsecase:
  def __init__(self, mc: Minio, mc_cloud: Minio):
    self.mc_cloud = mc_cloud
    self.batch_repository = BatchRepository(mc, mc_cloud)

  def _sync_once(self):
    geos = self.batch_repository.list_all_geohashes_from_db()
    logger.info(f"[batch] geohashes: {geos}")
    ok = 0
    for g in geos:
      if self.batch_repository.upload_latest_for_geohash(g):
        ok += 1
        
  async def periodic_sync_loop(self):
    # 起動時に一度 ensure
    self.batch_repository.ensure_bucket(self.mc_cloud, CLOUD_BUCKET)

    while True:
        try:
            logger.info("[batch] periodic sync start")
            # 同期処理はブロッキングなのでスレッドプールへ逃がす
            await asyncio.to_thread(self._sync_once)
        except Exception as e:
            logger.info(f"[sync] periodic sync failed: {e}")
        await asyncio.sleep(SYNC_INTERVAL_SEC)
