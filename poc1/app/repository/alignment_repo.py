from minio import Minio
from minio.error import S3Error
import tempfile, os
import open3d as o3d
from minio.commonconfig import CopySource

class AlignmentRepository:
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
    
    # bucket+key の場所から点群データをダウンロードしてOpen3DのPointCloudとして返す
    def download_ply(self, bucket: str, key: str) -> o3d.geometry.PointCloud:
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf:
            tmp = tf.name
        try:
            self.mc.fget_object(bucket, key, tmp)
            pc = o3d.io.read_point_cloud(tmp)
            return pc
        finally:
            try: os.remove(tmp)
            except FileNotFoundError: pass
    
    # bucket+key の場所にOpen3DのPointCloudをアップロードする        
    def upload_ply(self, bucket: str, key: str, pc: o3d.geometry.PointCloud):
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf:
            tmp_out = tf.name
        try:
            ok = o3d.io.write_point_cloud(tmp_out, pc)
            if not ok:
                raise RuntimeError("failed to write point cloud to temp file")
            self.mc.fput_object(bucket, key, tmp_out, content_type="application/octet-stream")
        finally:
            try: os.remove(tmp_out)
            except FileNotFoundError: pass
    
    # bucket+src_key の場所から点群データを bucket+dst_key にサーバサイドコピーする（uploadsとはminioで履歴用に使用しているフォルダーのこと）
    def copy_to_uploads(self, bucket: str, src_key: str, dst_key: str):
        self.mc.copy_object(
            bucket_name=bucket,
            object_name=dst_key,
            source=CopySource(bucket, src_key),
        )