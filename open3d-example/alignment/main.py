# 

# icp_bunny12.py ---------------------------------------------------
import open3d as o3d
import numpy as np
import copy

# ---------------- 0. ハイパーパラメータ ----------------
VOXEL = 0.005                     # 5 mm ボクセル（バニー約10 cm想定）
# 許容誤差の設定
DIST_RANSAC = VOXEL * 1.5         # RANSAC 対応距離
DIST_ICP    = VOXEL * 0.5         # ICP   対応距離

# ---------------- 1. 読み込み & 着色 ------------------
src_raw = o3d.io.read_point_cloud("bunny1.ply")   # 低密度
tgt_raw = o3d.io.read_point_cloud("bunny2.ply")   # 高密度
src_raw.paint_uniform_color([1.0, 0.0, 0.0])    # 赤
tgt_raw.paint_uniform_color([0.0, 0.0, 1.0])  # シアン

# ---------------- 2. 前処理 ---------------------------
def preprocess(pcd):
    # ダウンサンプリング
    p = pcd.voxel_down_sample(VOXEL)
    # 法線の推定
    p.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius = VOXEL*2, max_nn = 30))
    return p

src = preprocess(src_raw)
tgt = preprocess(tgt_raw)

# RANSACのための準備 対応候補点を解析
src_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
    src, o3d.geometry.KDTreeSearchParamHybrid(radius = VOXEL*5, max_nn = 100))
tgt_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
    tgt, o3d.geometry.KDTreeSearchParamHybrid(radius = VOXEL*5, max_nn = 100))

# ---------------- 3. RANSAC で初期姿勢 -----------------
result_ransac = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
    src, tgt, src_fpfh, tgt_fpfh,
    mutual_filter = True,
    max_correspondence_distance = DIST_RANSAC,
    estimation_method = o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
    ransac_n = 4,
    checkers = [
        o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
        o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(DIST_RANSAC)
    ],
    criteria = o3d.pipelines.registration.RANSACConvergenceCriteria(4000000, 500)
)
print("RANSAC fitness :", result_ransac.fitness)

# ---------------- 4. ICP で微調整 ----------------------
result_icp = o3d.pipelines.registration.registration_icp(
    src, tgt,
    max_correspondence_distance = DIST_ICP,
    init = result_ransac.transformation,
    estimation_method = o3d.pipelines.registration.TransformationEstimationPointToPlane()
)
print("ICP fitness    :", result_icp.fitness)
print("RMSE           :", result_icp.inlier_rmse)

# ---------------- 5. マージ & 保存 --------------------
src_aligned = copy.deepcopy(src_raw).transform(result_icp.transformation)
merged = tgt_raw + src_aligned
o3d.io.write_point_cloud("bunny12_icp_merged.ply", merged)
print("→ bunny12_icp_merged.ply を保存しました")
