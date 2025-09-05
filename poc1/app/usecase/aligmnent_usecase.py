from minio import Minio
import open3d as o3d
import time

base_data_bucket = "local-point-cloud/base-data"
base_data_key = "geohash-level8.ply"
VOXEL = 0.1                     # 10cm
DIST_RANSAC = VOXEL * 1.0       # RANSAC 対応距離（10cm）
DIST_ICP    = VOXEL * 0.5       # ICP   対応距離（5cm）

class AligmentUsecase:
  def __init__(self, merge_pc: any, mc: Minio):
    self.merge_pc = merge_pc
    self.mc = mc
  
  def preprocess(pc: any):
    p = pc.voxel_down_sample(VOXEL)
    p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*2, max_nn=30))
    return p
    
  def excute(self):
    start = time.time() 
    # ペース点群をMinioから取得
    base_pc = self.mc.get_object(base_data_bucket, base_data_key)
    
    # base_pc（ベース点群）と merge_pc（マージ点群）をダウンサンプリング
    base_pc_preprocessed = self.preprocess(base_pc)
    merge_pc_preprocessed = self.preprocess(self.merge_pc)
    
    # 特徴量計算
    fpfh1 = o3d.pipelines.registration.compute_fpfh_feature(base_pc_preprocessed, o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100))
    fpfh2 = o3d.pipelines.registration.compute_fpfh_feature(merge_pc_preprocessed, o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100))
    
    # RANSACで初期整合
    result_ransac = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        base_pc_preprocessed, merge_pc_preprocessed, fpfh1, fpfh2,
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
    
    # ICPで精密整合
    result_icp = o3d.pipelines.registration.registration_icp(
        base_pc_preprocessed, merge_pc_preprocessed,
        max_correspondence_distance=DIST_ICP,
        init=result_ransac.transformation,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane()
    )
    print("ICP fitness   :", result_icp.fitness)
    print("RMSE          :", result_icp.inlier_rmse)