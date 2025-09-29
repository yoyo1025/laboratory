# [/Users/tadanoyousei/laboratory/poc1/edge/app/repository/batch_repository.py]
from minio import Minio
from minio.error import S3Error
from db import SessionLocal
from sqlalchemy import text
import os, tempfile
import open3d as o3d
import numpy as np

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
      # local latestが無ければスキップ
      src_key = self.local_latest_key(geohash)
      if self.stat_or_none(self.mc, LOCAL_BUCKET, src_key) is None:
          return False
      
      # 一時DL
      with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf_in:
        src_tmp = tf_in.name
      # ダウンサンプリング後（点群）書き出し先
      with tempfile.NamedTemporaryFile(suffix=CLOUD_OBJECT_EXT, delete=False) as tf_out:
        dst_tmp = tf_out.name
      # メッシュ書き出し先
      with tempfile.NamedTemporaryFile(suffix=CLOUD_OBJECT_EXT, delete=False) as tf_mesh:
        mesh_tmp = tf_mesh.name
        
      try:
          # MinIO から取得
          self.mc.fget_object(LOCAL_BUCKET, src_key, src_tmp)
          
          # Open3Dで読み込み & ダウンサンプリング
          pcd = o3d.io.read_point_cloud(src_tmp)
          if pcd.is_empty():
            print(f"[sync] skip empty point cloud: {src_key}")
            return False
          
          # ダウンサンプリング
          pcd_ds = pcd.voxel_down_sample(VOXEL)

          # ===== 点群(PLY)を書き出し =====
          write_ok = o3d.io.write_point_cloud(dst_tmp, pcd_ds, write_ascii=False)
          if not write_ok:
            # 失敗時はオリジナルを送る
            dst_tmp = src_tmp
          
          # ===== メッシュ生成 & 書き出し =====
          # 法線推定 → 一貫方向へ
          pcd_ds.estimate_normals(
              search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=max(VOXEL*2, 0.05), max_nn=30)
          )
          pcd_ds.orient_normals_consistent_tangent_plane(k=30)

          # Poisson再構成
          mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
              pcd_ds, depth=9
          )
          densities = np.asarray(densities)
          th = np.quantile(densities, 0.02)   # 下位2%を除去
          mesh.remove_vertices_by_mask(densities < th)

          # クリーンアップ & 軽量化
          mesh = (
              mesh.remove_duplicated_vertices()
                  .remove_degenerate_triangles()
                  .remove_non_manifold_edges()
                  .remove_unreferenced_vertices()
          )
          # お好みで調整可
          mesh = mesh.simplify_vertex_clustering(voxel_size=max(VOXEL*0.15, 0.02))

          # メッシュを書き出し（PLY）
          # ※ TriangleMesh用の関数を使用
          mesh_ok = o3d.io.write_triangle_mesh(mesh_tmp, mesh, write_ascii=False)
          if not mesh_ok:
            print(f"[sync] WARN: failed to write mesh for {geohash} (skip mesh upload)")
            mesh_tmp = None

          # ===== アップロード =====
          self.ensure_bucket(self.mc_cloud, CLOUD_BUCKET)

          # 点群
          dst_key = self.cloud_tmp_key(geohash)
          ct = "model/ply" if CLOUD_OBJECT_EXT.lower() == ".ply" else "application/octet-stream"
          self.mc_cloud.fput_object(CLOUD_BUCKET, dst_key, dst_tmp, content_type=ct)
          print(f"[sync] uploaded (pc) s3://{CLOUD_BUCKET}/{dst_key}")

          # メッシュ
          if mesh_tmp:
            dst_key_mesh = self.cloud_tmp_mesh_key(geohash)
            self.mc_cloud.fput_object(CLOUD_BUCKET, dst_key_mesh, mesh_tmp, content_type=ct)
            print(f"[sync] uploaded (mesh) s3://{CLOUD_BUCKET}/{dst_key_mesh}")

          return True

      finally:
          # 後片付け
          for p in (src_tmp, dst_tmp, mesh_tmp):
              try:
                  if p:
                      os.remove(p)
              except FileNotFoundError:
                  pass
