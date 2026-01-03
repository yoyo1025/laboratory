# usecase/stream_usecase.py
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException
from typing import Tuple
import requests

LOCAL_BUCKET_DEFAULT = "edge1-point-cloud"
CLOUD_BUCKET_DEFAULT = "cloud-point-cloud"

NOT_FOUND_CODES = {"NoSuchKey", "NoSuchObject", "NotFound", "NoSuchBucket"}

class StreamUsecase:
    def __init__(self, mc_local: Minio, mc_cloud: Minio, geohash: str, local_bucket: str = LOCAL_BUCKET_DEFAULT, cloud_bucket: str = CLOUD_BUCKET_DEFAULT):
        self.mc_local = mc_local
        self.mc_cloud = mc_cloud
        self.geohash = geohash
        self.local_bucket = local_bucket
        self.cloud_bucket = cloud_bucket

    def _is_not_found(self, err: S3Error) -> bool:
        return err.code in NOT_FOUND_CODES

    def _try_get(self, mc: Minio, bucket: str, key: str):
        st = mc.stat_object(bucket, key)
        obj = mc.get_object(bucket, key)
        return obj, st

    def stream(self) -> Tuple[any, any, str, str, str]:
        # 1) edge (局所モデル)
        local_key = f"{self.geohash}/latest/{self.geohash}.ply"
        try:
            obj, st = self._try_get(self.mc_local, self.local_bucket, local_key)
            return obj, st, "edge", self.local_bucket, local_key
        except S3Error as e:
            if not self._is_not_found(e):
                raise HTTPException(status_code=502, detail=f"edge stat/get error: {e.code}")

        # 2) cloud (大域モデル) クラウド側のAPIへ問い合わせてストリーミング取得
        cloud_url = f"http://host.docker.internal:8100/pointcloud/{self.geohash}"
        try:
            resp = requests.get(cloud_url, stream=True, timeout=10)
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="point cloud not found on edge nor cloud")
            if resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"cloud http get error: {resp.status_code}")
            return resp.raw, resp.headers, "cloud-http", "http", cloud_url
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=f"cloud http request error: {e.__class__.__name__}: {e}")