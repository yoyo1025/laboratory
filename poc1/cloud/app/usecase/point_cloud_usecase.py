from minio import Minio
from repository.point_cloud_repository import PointCloudRepository
import os

BUCKET = "cloud-point-cloud"

class PointCloudUsecase:
  def __init__(self, mc: Minio, s3: any):
    self.mc = mc
    self.s3 = s3
    self.point_cloud_repository = PointCloudRepository(mc)
  
  def save(self, key: str):
    geohash = os.path.splitext(os.path.basename(key))[0]
    dst_key = f"{geohash}/{geohash}.ply"
    
    self.point_cloud_repository.copy_to_latest(BUCKET, key, dst_key)
    print(f"INFO: copied original to s3://{BUCKET}/{dst_key}")