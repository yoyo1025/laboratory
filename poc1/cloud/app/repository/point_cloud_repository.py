from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error

class PointCloudRepository:
  def __init__(self, mc: Minio):
    self.mc = mc
    
  # bucket+key の場所に点群データが存在するか確認する
  def check_folder_exists(self, bucket: str, key: str):
    try:
        return self.mc.stat_object(bucket, key)
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject", "NotFound"):
            return None
        raise
  
  # bucket+src_key の場所から点群データを bucket+dst_key にサーバサイドコピーする（uploadsとはminioで履歴用に使用しているフォルダーのこと）
  def copy_to_latest(self, bucket: str, src_key: str, dst_key: str):
    self.mc.copy_object(
        bucket_name=bucket,
        object_name=dst_key,
        source=CopySource(bucket, src_key),
    )