import open3d as o3d
import copy

# ---------------- 0. パラメータ設定 ----------------
VOXEL = 0.05                    # 5 cm（部屋スケール）
DIST_RANSAC = VOXEL * 2.0       # RANSAC 対応距離（10cm）
DIST_ICP    = VOXEL * 0.5       # ICP   対応距離（2.5cm）

# ---------------- 1. 点群の読み込み ----------------
room1_raw = o3d.io.read_point_cloud("test2.ply")
room2_raw = o3d.io.read_point_cloud("test4.ply")

# ---------------- 2. 前処理関数 --------------------
def preprocess(pcd):
    p = pcd.voxel_down_sample(VOXEL)
    p.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*2, max_nn=30))
    return p

room1 = preprocess(room1_raw)
room2 = preprocess(room2_raw)

# ---------------- 3. 特徴量計算 ---------------------
fpfh1 = o3d.pipelines.registration.compute_fpfh_feature(
    room1, o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100))
fpfh2 = o3d.pipelines.registration.compute_fpfh_feature(
    room2, o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100))

# ---------------- 4. RANSACで初期整合 ----------------
result_ransac = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
    room1, room2, fpfh1, fpfh2,
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

# ---------------- 5. ICPで精密整合 -------------------
result_icp = o3d.pipelines.registration.registration_icp(
    room1, room2,
    max_correspondence_distance=DIST_ICP,
    init=result_ransac.transformation,
    estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane()
)

## ここまでは位置合わせのコードとほぼ同じ？

T = result_icp.transformation

d_th = VOXEL * 1.5
eval_res = o3d.pipelines.registration.evaluate_registration(
    room1_raw, room2_raw, d_th, T
)

print(f"Overlap(fitness): {eval_res.fitness:.3f}")
print(f"Inlier RMSE    : {eval_res.inlier_rmse:.4f} m")