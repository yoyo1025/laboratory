from minio import Minio
import open3d as o3d
import time
import tempfile, os
import numpy as np
import pygeohash
import re
from minio.error import S3Error
from datetime import datetime, timezone
from minio.commonconfig import CopySource

BUCKET = "local-point-cloud"   # バケット名（固定）
VOXEL = 0.1                    # 10cm
DIST_RANSAC = VOXEL * 1.0      # RANSAC 対応距離（10cm）
DIST_ICP    = VOXEL * 0.5      # ICP   対応距離（5cm）


def utc_ts():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# ========= ユースケース =========
class AligmentUsecase:
    def __init__(self, merge_pc: o3d.geometry.PointCloud, mc: Minio):
        self.merge_pc = merge_pc
        self.mc = mc

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

    def _stat(self, bucket: str, key: str):
        try:
            return self.mc.stat_object(bucket, key)
        except S3Error as e:
            if e.code in ("NoSuchKey", "NoSuchObject", "NotFound"):
                return None
            raise

    def _download_ply(self, bucket: str, key: str) -> o3d.geometry.PointCloud:
        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf:
            tmp = tf.name
        try:
            self.mc.fget_object(bucket, key, tmp)
            pc = o3d.io.read_point_cloud(tmp)
            return pc
        finally:
            try: os.remove(tmp)
            except FileNotFoundError: pass

    def _upload_ply(self, bucket: str, key: str, pc: o3d.geometry.PointCloud):
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

    def _copy_to_uploads(self, bucket: str, src_key: str, dst_key: str):
        # オリジナルをそのまま履歴へ（サーバサイドコピー）
        self.mc.copy_object(
            bucket_name=bucket,
            object_name=dst_key,
            source=CopySource(bucket, src_key),
        )

    # NOTE: 位置合わせロジックは元コードそのまま（パラメータ/手順を変更しない）
    def execute(self, src_key: str):
        start = time.time()
        geohash = self.calc_geohash(src_key)
        base_prefix, latest_key, upload_key = self._paths(geohash, src_key)

        # 1) 履歴にオリジナルをまず保存
        self._copy_to_uploads(BUCKET, src_key, upload_key)
        print(f"INFO: copied original to s3://{BUCKET}/{upload_key}")

        # 2) latest が無ければ初期化（マージなし）
        if self._stat(BUCKET, latest_key) is None:
            self._upload_ply(BUCKET, latest_key, self.merge_pc)
            print("INFO: latest not found, initialized")
            print(f"initialized latest at s3://{BUCKET}/{latest_key}")
            print(f"done in {time.time() - start:.2f}s (initialized)")
            return

        # 3) latest 読み込み
        base_pc = self._download_ply(BUCKET, latest_key)

        # === ここから整列・マージ（元のロジックを変更しない）===
        base_pc_preprocessed  = self.preprocess(base_pc)
        merge_pc_preprocessed = self.preprocess(self.merge_pc)

        fpfh1 = o3d.pipelines.registration.compute_fpfh_feature(
            base_pc_preprocessed,
            o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100)
        )
        fpfh2 = o3d.pipelines.registration.compute_fpfh_feature(
            merge_pc_preprocessed,
            o3d.geometry.KDTreeSearchParamHybrid(radius=VOXEL*5, max_nn=100)
        )

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

        result_icp = o3d.pipelines.registration.registration_icp(
            merge_pc_preprocessed,                  # source
            base_pc_preprocessed,                   # target
            max_correspondence_distance=DIST_ICP,
            init=result_ransac.transformation,
            estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane()
        )
        print("ICP fitness   :", result_icp.fitness)
        print("RMSE          :", result_icp.inlier_rmse)

        T = result_icp.transformation
        merge_aligned = o3d.geometry.PointCloud(self.merge_pc)  # フル解像を変換
        merge_aligned.transform(T)

        # 新規分を真っ赤に
        n = len(merge_aligned.points)
        if n > 0:
            merge_aligned.colors = o3d.utility.Vector3dVector(
                np.tile([1.0, 0.0, 0.0], (n, 1))
            )

        merged = base_pc + merge_aligned

        # 4) latest を上書き
        self._upload_ply(BUCKET, latest_key, merged)

        print("[debug] base points:", len(base_pc.points), "colors:", base_pc.has_colors(), "normals:", base_pc.has_normals())
        print("[debug] merge points:", len(self.merge_pc.points), "colors:", self.merge_pc.has_colors(), "normals:", self.merge_pc.has_normals())
        print("[debug] merged points:", len(merged.points), "colors:", merged.has_colors(), "normals:", merged.has_normals())
        print(f"done in {time.time() - start:.2f}s")

