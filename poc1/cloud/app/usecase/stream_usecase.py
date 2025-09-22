from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException

CLOUD_BUCKET = "cloud-point-cloud"

class StreamUsecase:
  def __init__(self, mc: Minio, key: str):
    self.mc = mc
    self.key = key
  def stream(self):
    try:
      st = self.mc.stat_object(CLOUD_BUCKET, self.key)
    except S3Error as e:
      if e.code in ("NoSuchKey", "NoSuchObject", "NotFound", "NoSuchBucket"):
          raise HTTPException(status_code=404, detail="point cloud not found")
      raise
    
    try:
        obj = self.mc.get_object(CLOUD_BUCKET, self.key)
    except S3Error as e:
        raise HTTPException(status_code=502, detail=f"failed to read object: {e.code}")

    return obj, st