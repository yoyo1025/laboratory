from minio import Minio
from minio.error import S3Error
from db import SessionLocal
from sqlalchemy import text
import os, tempfile

CLOUD_OBJECT_EXT = os.getenv("CLOUD_OBJECT_EXT", ".ply")
LOCAL_BUCKET = "local-point-cloud"
CLOUD_BUCKET = "cloud-point-cloud"

class BatchRepository:
  def __init__(self, mc: Minio, mc_cloud: Minio):
    self.mc = mc
    self.mc_cloud = mc_cloud
  
  def local_latest_key(self, geohash: str) -> str:
    # 既存のレイアウトに合わせる
    return f"{geohash}/latest/latest.ply"
  
  def cloud_tmp_key(self, geohash: str) -> str:
    return f"tmp/{geohash}{CLOUD_OBJECT_EXT}"
  
  def ensure_bucket(self, client: Minio, bucket: str):
    # バケットがなければ作成（競合は握りつぶし）
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except Exception as e:
        print(f"ensure_bucket({bucket}): {e}")
  
  def stat_or_none(self, client: Minio, bucket: str, key: str):
    try:
        return client.stat_object(bucket, key)
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject", "NotFound", "NoSuchBucket"):
            return None
        raise
      
  def list_all_geohashes_from_db(self):
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT geohash FROM areas")).all()
        return [r[0] for r in rows]
    finally:
        db.close()

  def upload_latest_for_geohash(self, geohash: str):
      # local latestが無ければスキップ
      src_key = self.local_latest_key(geohash)
      if self.stat_or_none(self.mc, LOCAL_BUCKET, src_key) is None:
          return False

      # 一時DL → クラウドへ fput
      with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf:
          tmp = tf.name
      try:
          self.mc.fget_object(LOCAL_BUCKET, src_key, tmp)
          self.ensure_bucket(self.mc_cloud, CLOUD_BUCKET)
          dst_key = self.cloud_tmp_key(geohash)
          self.mc_cloud.fput_object(CLOUD_BUCKET, dst_key, tmp, content_type="application/octet-stream")
          print(f"[sync] uploaded {src_key} -> s3://{CLOUD_BUCKET}/{dst_key}")
          return True
      finally:
          try: os.remove(tmp)
          except FileNotFoundError: pass