from fastapi import FastAPI, Request, status, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask as StarletteBackgroundTask
from urllib.parse import unquote
from minio import Minio
from usecase.aligmnent_usecase import AligmentUsecase  
import open3d as o3d
import os, asyncio, tempfile, logging
from usecase.batch_usecase import BatchUsecase
from usecase.stream_usecase import StreamUsecase
from datetime import timezone
from minio.error import S3Error
from fastapi import HTTPException

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

# ローカルMinioクライアント初期化
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_root")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
mc = Minio(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=MINIO_SECURE)

# クラウドMinioクライアント初期化
CLOUD_MINIO_ENDPOINT = os.getenv("CLOUD_MINIO_ENDPOINT", "host.docker.internal:9100")
CLOUD_MINIO_ACCESS_KEY = os.getenv("CLOUD_MINIO_ACCESS_KEY", "minio_root")
CLOUD_MINIO_SECRET_KEY = os.getenv("CLOUD_MINIO_SECRET_KEY", "minio_password")
CLOUD_MINIO_SECURE = os.getenv("CLOUD_MINIO_SECURE", "false").lower() == "true"
mc_cloud = Minio(CLOUD_MINIO_ENDPOINT, CLOUD_MINIO_ACCESS_KEY, CLOUD_MINIO_SECRET_KEY, secure=CLOUD_MINIO_SECURE)

LOCAL_BUCKET = "local-point-cloud"
CLOUD_BUCKET = "cloud-point-cloud"

@app.on_event("startup")
async def _start_sync():
    app.state.sync_task = asyncio.create_task(BatchUsecase(mc, mc_cloud).periodic_sync_loop())

@app.on_event("shutdown")
async def _stop_sync():
    task = getattr(app.state, "sync_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
def handle_record_sync(rec, mc: Minio):
    s3 = rec.get("s3", {})
    bucket = s3.get("bucket", {}).get("name")
    key = s3.get("object", {}).get("key")
    event = rec.get("eventName", "")

    if not bucket or not key:
        return
    key = unquote(key)

    # tmp/ の .ply の put だけを処理
    if not str(event).startswith("s3:ObjectCreated") or not key.endswith(".ply") or not key.startswith("tmp/"):
        return

    # 一時DL → Open3D で読み込み（整列・マージはフル解像で）
    with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf:
        tmp = tf.name
    try:
        mc.fget_object(bucket, key, tmp)
        pc = o3d.io.read_point_cloud(tmp)
    finally:
        try: os.remove(tmp)
        except FileNotFoundError: pass

    print("INFO: bucket:", bucket)
    print("INFO: object key:", key)
    AligmentUsecase(pc, mc, s3).execute(key)

@app.post("/minio/webhook")
async def PCLocalAlignmentHandler(request: Request, background: BackgroundTasks):
    try:
        body = await request.json()
    except Exception:
        body = {}

    records = body.get("Records", [body]) if isinstance(body, dict) else []
    for rec in records:
        background.add_task(handle_record_sync, rec, mc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/{geohash}")
def get_city_model(geohash: str):
    obj, st, source, key = get_stream_with_fallback(geohash)

    last_modified = st.last_modified
    if last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=timezone.utc)

    headers = {
        "Content-Length": str(st.size),
        "Last-Modified": last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "Content-Disposition": f'attachment; filename="{geohash}.ply"',
        "ETag": getattr(st, "etag", None) or "",
        # どちらから返したかを明記
        "X-Pointcloud-Source": source,
        # 返したオブジェクトキー（デバッグ/可観測性に）
        "X-Pointcloud-Key": key,
    }

    def _close():
        try:
            obj.close()
        except Exception:
            pass

    return StreamingResponse(
        obj.stream(32 * 1024),
        media_type="application/octet-stream",
        headers=headers,
        background=StarletteBackgroundTask(_close),
    )

def get_stream_with_fallback(geohash: str):
    # 1) edge 側（局所モデル）
    local_key = f"{geohash}/latest/latest.ply"
    try:
        st = mc.stat_object(LOCAL_BUCKET, local_key)
        obj = mc.get_object(LOCAL_BUCKET, local_key)
        return obj, st, "edge", local_key
    except S3Error as e:
        # 無い系だけフォールバック、その他は即エラー
        if e.code not in ("NoSuchKey", "NoSuchObject", "NotFound", "NoSuchBucket"):
            raise HTTPException(status_code=502, detail=f"edge stat/get error: {e.code}")

    # 2) cloud 側（大域モデル）
    cloud_key = f"{geohash}/{geohash}.ply"
    try:
        st = mc_cloud.stat_object(CLOUD_BUCKET, cloud_key)
        obj = mc_cloud.get_object(CLOUD_BUCKET, cloud_key)
        return obj, st, "cloud", cloud_key
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject", "NotFound", "NoSuchBucket"):
            # 両方無い
            raise HTTPException(status_code=404, detail="point cloud not found on edge nor cloud")
        raise HTTPException(status_code=502, detail=f"cloud stat/get error: {e.code}")