# [/Users/tadanoyousei/laboratory/poc1/edge/app/repository/batch_repository.py]
from minio import Minio
from minio.error import S3Error
from db import SessionLocal
from sqlalchemy import text
import os, tempfile
import open3d as o3d
import numpy as np

CLOUD_OBJECT_EXT = os.getenv("CLOUD_OBJECT_EXT", ".ply")
LOCAL_BUCKET = "edge1-point-cloud"
CLOUD_BUCKET = "cloud-point-cloud"
VOXEL = 0.15
GLOBAL_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "global-model.ply")
)

class BatchRepository:
  def __init__(self, mc: Minio, mc_cloud: Minio):
    self.mc = mc
    self.mc_cloud = mc_cloud
  
  def local_latest_key(self, geohash: str) -> str:
    return f"{geohash}/latest/{geohash}.ply"
  
  def cloud_tmp_key(self, geohash: str) -> str:
    return f"tmp/{geohash}{CLOUD_OBJECT_EXT}"

  def cloud_tmp_mesh_key(self, geohash: str) -> str:
    return f"tmp/mesh/{geohash}-mesh{CLOUD_OBJECT_EXT}"
  
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
      # ハードコーディングを承知のうえgeohashを上書き
      geohash="bbbbbbbb"
      # local latestが無ければスキップ
      src_key = self.local_latest_key(geohash)
      if self.stat_or_none(self.mc, LOCAL_BUCKET, src_key) is None:
          return False

      # 一時DL
      with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf_in:
        src_tmp = tf_in.name

      # （加工結果を書き出す先として確保していたが、加工を無効化するなら不要）
      # with tempfile.NamedTemporaryFile(suffix=CLOUD_OBJECT_EXT, delete=False) as tf_out:
      #   dst_tmp = tf_out.name
      # with tempfile.NamedTemporaryFile(suffix=CLOUD_OBJECT_EXT, delete=False) as tf_mesh:
      #   mesh_tmp = tf_mesh.name

      dst_tmp = None
      mesh_tmp = None

      try:
          # MinIO から取得
          self.mc.fget_object(LOCAL_BUCKET, src_key, src_tmp)

          # ==========================
          # 点群加工（Open3D）を無効化
          # ==========================
          # pcd = o3d.io.read_point_cloud(src_tmp)
          # if pcd.is_empty():
          #   return False
          #
          # pcd_ds = pcd.voxel_down_sample(VOXEL)
          #
          # write_ok = o3d.io.write_point_cloud(dst_tmp, pcd_ds, write_ascii=False)
          # if not write_ok:
          #   dst_tmp = src_tmp
          #
          # pcd_ds.estimate_normals(
          #     search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=max(VOXEL*2, 0.05), max_nn=30)
          # )
          # pcd_ds.orient_normals_consistent_tangent_plane(k=30)
          #
          # mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
          #     pcd_ds, depth=9
          # )
          # densities = np.asarray(densities)
          # th = np.quantile(densities, 0.02)
          # mesh.remove_vertices_by_mask(densities < th)
          #
          # mesh = (
          #     mesh.remove_duplicated_vertices()
          #         .remove_degenerate_triangles()
          #         .remove_non_manifold_edges()
          #         .remove_unreferenced_vertices()
          # )
          # mesh = mesh.simplify_vertex_clustering(voxel_size=max(VOXEL*0.15, 0.02))
          #
          # mesh_ok = o3d.io.write_triangle_mesh(mesh_tmp, mesh, write_ascii=False)
          # if not mesh_ok:
          #   mesh_tmp = None

          # 加工しないので、アップロード対象は固定の global-model
          if not os.path.exists(GLOBAL_MODEL_PATH):
              print(f"[sync] global model not found: {GLOBAL_MODEL_PATH}")
              return False
          dst_tmp = GLOBAL_MODEL_PATH

          # ===== アップロード =====
          self.ensure_bucket(self.mc_cloud, CLOUD_BUCKET)

          # ハードコーディングを承知のうえgeohashを上書き
          geohash="xxxxxxxx"
          dst_key = self.cloud_tmp_key(geohash)
          ct = "model/ply" if CLOUD_OBJECT_EXT.lower() == ".ply" else "application/octet-stream"
          self.mc_cloud.fput_object(CLOUD_BUCKET, dst_key, dst_tmp, content_type=ct)

          # メッシュはアップロードしない
          # if mesh_tmp:
          #   dst_key_mesh = self.cloud_tmp_mesh_key(geohash)
          #   self.mc_cloud.fput_object(CLOUD_BUCKET, dst_key_mesh, mesh_tmp, content_type=ct)

          return True

      finally:
          # 後片付け
          # dst_tmp は src_tmp と同一になるので、二重削除しないように注意
          try:
              if src_tmp:
                  os.remove(src_tmp)
          except FileNotFoundError:
              pass