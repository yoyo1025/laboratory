# [/Users/tadanoyousei/laboratory/poc1/cloud/app/usecase/point_cloud_usecase.py]
from minio import Minio
from repository.point_cloud_repository import PointCloudRepository
import os, re

BUCKET = "cloud-point-cloud"

_mesh_pat = re.compile(r"^tmp/mesh/(?P<gh>.+)-mesh\.ply$")
_pc_pat   = re.compile(r"^tmp/(?P<gh>.+)\.ply$")

class PointCloudUsecase:
  def __init__(self, mc: Minio, s3: any):
    self.mc = mc
    self.s3 = s3
    self.point_cloud_repository = PointCloudRepository(mc)
  
  def save(self, key: str):
    # mesh or point-cloud で保存先を切り替え
    m = _mesh_pat.match(key)
    if m:
      geohash = m.group("gh")
      dst_key = f"{geohash}/mesh/{geohash}-mesh.ply"
      self.point_cloud_repository.copy_to_latest(BUCKET, key, dst_key)
      print(f"INFO: copied mesh to s3://{BUCKET}/{dst_key}")
      return

    m = _pc_pat.match(key)
    if m:
      geohash = m.group("gh")
      dst_key = f"{geohash}/{geohash}.ply"
      self.point_cloud_repository.copy_to_latest(BUCKET, key, dst_key)
      print(f"INFO: copied pointcloud to s3://{BUCKET}/{dst_key}")
      return

    # 想定外のキーは無視（必要ならログのみ）
    print(f"WARN: ignore object key (not mesh/pc tmp path): {key}")
