from minio import Minio
import open3d as o3d
import time
import os
import numpy as np
import pygeohash
import re
from datetime import datetime, timezone
from repository.alignment_repository import AlignmentRepository
from db import SessionLocal      

BUCKET = "local-point-cloud"
VOXEL = 0.1
DIST_RANSAC = VOXEL * 1.0
DIST_ICP    = VOXEL * 0.5


def utc_ts():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

class AligmentUsecase:
    def __init__(self, merge_pc: o3d.geometry.PointCloud, mc: Minio, s3: any):
        self.merge_pc = merge_pc
        self.mc = mc
        self.s3 = s3
        self.alignment_repository = AlignmentRepository(mc)
        
    # 前処理（ダウンサンプリング＋法線推定）
    def preprocess(self, pc: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        p = pc.voxel_down_sample(VOXEL)
        p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*2, max_nn=30))
        return p

    # key（フルパス）からファイル名を取り出して geohash を算出
    def calc_geohash(self, key: str) -> str:
        basename = os.path.basename(key)
        m = re.fullmatch(r"x([-+]?)(\d+)-(\d+)-y([-+]?)(\d+)-(\d+)-(\d+)\.ply", basename)
        if not m:
            raise ValueError(f"key format invalid: {basename}")
        x = abs(float(f"{m.group(2)}.{m.group(3)}"))  # 緯度
        y = abs(float(f"{m.group(5)}.{m.group(6)}"))  # 経度
        level = int(m.group(7))
        geohash = pygeohash.encode(latitude=x, longitude=y, precision=level)
        print(f"INFO: extracted: lat={x}, lon={y}, level={level} -> geohash={geohash}")
        return geohash

    # geohashに基づく保存先（uploads/latest）
    def _paths(self, geohash: str, src_key: str):
        base_prefix = f"{geohash}"
        latest_key  = f"{base_prefix}/latest/latest.ply"
        upload_key  = f"{base_prefix}/uploads/{utc_ts()}-{os.path.basename(src_key)}"
        return base_prefix, latest_key, upload_key

    def execute(self, src_key: str):
        start = time.time()
        geohash = self.calc_geohash(src_key)
        base_prefix, latest_key, upload_key = self._paths(geohash, src_key)

        # 履歴にオリジナルをまず保存
        self.alignment_repository.copy_to_uploads(BUCKET, src_key, upload_key)
        # print(f"INFO: copied original to s3://{BUCKET}/{upload_key}")

        # latest が無ければ初期化（マージなし）
        if self.alignment_repository.check_folder_exists(BUCKET, latest_key) is None:
            self.alignment_repository.upload_ply(BUCKET, latest_key, self.merge_pc)
            db = SessionLocal()
            try:
                self.alignment_repository.save_pc_metadata(db, geohash, len(geohash), os.path.basename(upload_key), upload_key, self.s3.get("object", {}).get("size"), "application/octet-stream")
            finally:
                db.close()
            print("INFO: latest not found, initialized")
            print(f"initialized latest at s3://{BUCKET}/{latest_key}")
            print(f"done in {time.time() - start:.2f}s (initialized)")
            return

        # latest 読み込み
        base_pc = self.alignment_repository.download_ply(BUCKET, latest_key)
        
        # 前処理
        base_pc_preprocessed  = self.preprocess(base_pc)
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

        # RANSAC
        result_ransac = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
            merge_pc_preprocessed,                  # source
            base_pc_preprocessed,                   # target
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

        # ICP
        result_icp = o3d.pipelines.registration.registration_icp(
            merge_pc_preprocessed,                  # source
            base_pc_preprocessed,                   # target
            max_correspondence_distance=DIST_ICP,
            init=result_ransac.transformation,
            estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane()
        )
        print("ICP fitness   :", result_icp.fitness)
        print("RMSE          :", result_icp.inlier_rmse)
        
        # 座標変換
        T = result_icp.transformation
        merge_aligned = o3d.geometry.PointCloud(self.merge_pc)  # フル解像を変換
        merge_aligned.transform(T)

        # 新規分を真っ赤に（動作確認のため）
        n = len(merge_aligned.points)
        if n > 0:
            merge_aligned.colors = o3d.utility.Vector3dVector(
                np.tile([1.0, 0.0, 0.0], (n, 1))
            )

        # 合成
        merged = base_pc + merge_aligned

        # 保存
        self.alignment_repository.upload_ply(BUCKET, latest_key, merged)
        db = SessionLocal()
        try:
            self.alignment_repository.save_pc_metadata(db, geohash, len(geohash), os.path.basename(upload_key), upload_key, self.s3.get("object", {}).get("size"), "application/octet-stream")
        finally:
            db.close()
        print("[debug] base points:", len(base_pc.points), "colors:", base_pc.has_colors(), "normals:", base_pc.has_normals())
        print("[debug] merge points:", len(self.merge_pc.points), "colors:", self.merge_pc.has_colors(), "normals:", self.merge_pc.has_normals())
        print("[debug] merged points:", len(merged.points), "colors:", merged.has_colors(), "normals:", merged.has_normals())
        print(f"done in {time.time() - start:.2f}s")

