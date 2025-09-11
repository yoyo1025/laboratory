from minio import Minio
import open3d as o3d
import time
import tempfile, os
import numpy as np

base_data_bucket = "local-point-cloud/base-data"
base_data_key = "geohash-level8.ply"
VOXEL = 0.1                     # 10cm
DIST_RANSAC = VOXEL * 1.0       # RANSAC 対応距離（10cm）
DIST_ICP    = VOXEL * 0.5       # ICP   対応距離（5cm）

class AligmentUsecase:
  def __init__(self, merge_pc: any, mc: Minio):
    self.merge_pc = merge_pc
    self.mc = mc
  
  def preprocess(self, pc: any):
    p = pc.voxel_down_sample(VOXEL)
    p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*2, max_nn=30))
    return p
    
  def excute(self):
    start = time.time() 

    # 「bucket/key」の与え方を壊さないための最小対応：
    #  base_data_bucket に '/' が含まれていたら、先頭をバケット、残り+base_data_key をオブジェクトキーにする
    if "/" in base_data_bucket:
      _bucket, _prefix = base_data_bucket.split("/", 1)
      base_bucket = _bucket
      base_key = f"{_prefix}/{base_data_key}"
    else:
      base_bucket = base_data_bucket
      base_key = base_data_key

    # MinIO からベース点群（フル解像）を一時ファイルにダウンロード → 読み込み
    suffix = os.path.splitext(base_key)[1] or ".ply"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
      tmp_in = tf.name
    try:
      self.mc.fget_object(base_bucket, base_key, tmp_in)  # ストリームではなくファイルで取得
      base_pc = o3d.io.read_point_cloud(tmp_in)
    finally:
      try:
        os.remove(tmp_in)
      except FileNotFoundError:
        pass
    
    # base_pc（ベース点群）と merge_pc（マージ点群）をダウンサンプリング
    base_pc_preprocessed = self.preprocess(base_pc)
    merge_pc_preprocessed = self.preprocess(self.merge_pc)
    
    # 特徴量計算
    fpfh1 = o3d.pipelines.registration.compute_fpfh_feature(
      base_pc_preprocessed,
      o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100)
    )
    fpfh2 = o3d.pipelines.registration.compute_fpfh_feature(
      merge_pc_preprocessed,
      o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100)
    )
    
    # RANSAC（source=merge, target=base）に最小修正
    result_ransac = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        merge_pc_preprocessed,                  # source（動かす側）
        base_pc_preprocessed,                   # target（基準）
        fpfh2, fpfh1,                           # source_feature, target_feature
        mutual_filter=True,
        max_correspondence_distance=DIST_RANSAC,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        ransac_n=4,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(DIST_RANSAC)
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(1000000, 1000)
    )
    print("RANSAC fitness:", result_ransac.fitness)
    
    # ICP（source=merge, target=base）に最小修正
    result_icp = o3d.pipelines.registration.registration_icp(
        merge_pc_preprocessed,                  # source
        base_pc_preprocessed,                   # target
        max_correspondence_distance=DIST_ICP,
        init=result_ransac.transformation,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane()
    )
    print("ICP fitness   :", result_icp.fitness)
    print("RMSE          :", result_icp.inlier_rmse)

    # 得られた変換を「フル解像の merge_pc」に適用し、フル解像の base_pc と結合
    T = result_icp.transformation
    merge_aligned = o3d.geometry.PointCloud(self.merge_pc)  # なるべく元を壊さないようコピー
    merge_aligned.transform(T)
    merge_aligned = o3d.geometry.PointCloud(self.merge_pc)
    merge_aligned.transform(T)

    # 「マージ点群」を真っ赤にする
    n = len(merge_aligned.points)
    merge_aligned.colors = o3d.utility.Vector3dVector(
        np.tile([1.0, 0.0, 0.0], (n, 1))
    )
    merged = base_pc + merge_aligned

    # 結果を MinIO の「ベース点群」に上書き保存
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
      tmp_out = tf.name
    try:
      ok = o3d.io.write_point_cloud(tmp_out, merged)
      if not ok:
        raise RuntimeError("failed to write merged point cloud")
      self.mc.fput_object(base_bucket, base_key, tmp_out, content_type="application/octet-stream")
      print("[debug] base points:", len(base_pc.points), "colors:", base_pc.has_colors(), "normals:", base_pc.has_normals())
      print("[debug] merge points:", len(self.merge_pc.points), "colors:", self.merge_pc.has_colors(), "normals:", self.merge_pc.has_normals())
      print("[debug] merged points:", len(merged.points), "colors:", merged.has_colors(), "normals:", merged.has_normals())

    finally:
      try:
        os.remove(tmp_out)
      except FileNotFoundError:
        pass

    print(f"done in {time.time() - start:.2f}s")
