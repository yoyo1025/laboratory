from minio import Minio
from minio.error import S3Error
from db import SessionLocal
from sqlalchemy import text
import os, tempfile
import open3d as o3d  # 追加（既に記載済みならそのまま）

CLOUD_OBJECT_EXT = os.getenv("CLOUD_OBJECT_EXT", ".ply")
LOCAL_BUCKET = "local-point-cloud"
CLOUD_BUCKET = "cloud-point-cloud"
VOXEL = 0.15

class BatchRepository:
  def __init__(self, mc: Minio, mc_cloud: Minio):
    self.mc = mc
    self.mc_cloud = mc_cloud
  
  def local_latest_key(self, geohash: str) -> str:
    return f"{geohash}/latest/latest.ply"
  
  def cloud_tmp_key(self, geohash: str) -> str:
    return f"tmp/{geohash}{CLOUD_OBJECT_EXT}"
  
  def ensure_bucket(self, client: Minio, bucket: str):
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
      
      # 一時DL
      with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf_in:
        src_tmp = tf_in.name
      # ダウンサンプリング後の書き出し先
      with tempfile.NamedTemporaryFile(suffix=CLOUD_OBJECT_EXT, delete=False) as tf_out:
        dst_tmp = tf_out.name
        
      try:
          # MinIO から取得
          self.mc.fget_object(LOCAL_BUCKET, src_key, src_tmp)
          
          # Open3Dで読み込み & ダウンサンプリング
          pcd = o3d.io.read_point_cloud(src_tmp)
          if pcd.is_empty():
            print(f"[sync] skip empty point cloud: {src_key}")
            return False
          
          # ダウンサンプリング（10cm）
          pcd_ds = pcd.voxel_down_sample(VOXEL)

          # バイナリPLYに書き出し
          write_ok = o3d.io.write_point_cloud(dst_tmp, pcd_ds, write_ascii=False)
          if not write_ok:
            # 失敗時はオリジナルを送る
            dst_tmp = src_tmp

          # アップロード
          self.ensure_bucket(self.mc_cloud, CLOUD_BUCKET)
          dst_key = self.cloud_tmp_key(geohash)
          self.mc_cloud.fput_object(CLOUD_BUCKET, dst_key, dst_tmp, content_type="application/octet-stream")
          print(f"[sync] uploaded (downsampled) {src_key} -> s3://{CLOUD_BUCKET}/{dst_key}")
          return True

      finally:
          # 後片付け
          for p in (src_tmp, dst_tmp):
              try:
                  os.remove(p)
              except FileNotFoundError:
                  pass