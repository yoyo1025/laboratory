from fastapi import FastAPI, Request, status, BackgroundTasks, Response
from urllib.parse import unquote
from minio import Minio
from usecase.aligmnent_usecase import AligmentUsecase  
import open3d as o3d
from minio.error import S3Error
from sqlalchemy import text
import os, asyncio, tempfile, logging
from db import SessionLocal

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
    
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_root")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
mc = Minio(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=MINIO_SECURE)

CLOUD_MINIO_ENDPOINT = os.getenv("CLOUD_MINIO_ENDPOINT", "host.docker.internal:9100")
CLOUD_MINIO_ACCESS_KEY = os.getenv("CLOUD_MINIO_ACCESS_KEY", "minio_root")
CLOUD_MINIO_SECRET_KEY = os.getenv("CLOUD_MINIO_SECRET_KEY", "minio_password")
CLOUD_MINIO_SECURE = os.getenv("CLOUD_MINIO_SECURE", "false").lower() == "true"

mc_cloud = Minio(CLOUD_MINIO_ENDPOINT, CLOUD_MINIO_ACCESS_KEY, CLOUD_MINIO_SECRET_KEY, secure=CLOUD_MINIO_SECURE)

SYNC_INTERVAL_SEC = int(os.getenv("SYNC_INTERVAL_SEC", "60"))
LOCAL_BUCKET = "local-point-cloud"
CLOUD_BUCKET = "cloud-point-cloud"
CLOUD_OBJECT_EXT = os.getenv("CLOUD_OBJECT_EXT", ".ply")

def ensure_bucket(client: Minio, bucket: str):
    # バケットがなければ作成（競合は握りつぶし）
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except Exception as e:
        logger.info("ensure_bucket(%s): %s", bucket, e)

def local_latest_key(geohash: str) -> str:
    # 既存のレイアウトに合わせる
    return f"{geohash}/latest/latest.ply"

def cloud_tmp_key(geohash: str) -> str:
    return f"tmp/{geohash}{CLOUD_OBJECT_EXT}"

def stat_or_none(client: Minio, bucket: str, key: str):
    try:
        return client.stat_object(bucket, key)
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject", "NotFound", "NoSuchBucket"):
            return None
        raise

def list_all_geohashes_from_db():
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT geohash FROM areas")).all()
        return [r[0] for r in rows]
    finally:
        db.close()

def upload_latest_for_geohash(geohash: str):
    # local latestが無ければスキップ
    src_key = local_latest_key(geohash)
    if stat_or_none(mc, LOCAL_BUCKET, src_key) is None:
        return False

    # 一時DL → クラウドへ fput
    with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tf:
        tmp = tf.name
    try:
        mc.fget_object(LOCAL_BUCKET, src_key, tmp)
        ensure_bucket(mc_cloud, CLOUD_BUCKET)
        dst_key = cloud_tmp_key(geohash)
        mc_cloud.fput_object(CLOUD_BUCKET, dst_key, tmp, content_type="application/octet-stream")
        logger.info("[sync] uploaded %s -> s3://%s/%s", src_key, CLOUD_BUCKET, dst_key)
        return True
    finally:
        try: os.remove(tmp)
        except FileNotFoundError: pass

async def periodic_sync_loop():
    # 起動時に一度 ensure
    ensure_bucket(mc_cloud, CLOUD_BUCKET)

    while True:
        try:
            geos = list_all_geohashes_from_db()
            ok = 0
            for g in geos:
                if upload_latest_for_geohash(g):
                    ok += 1
            logger.info("[sync] cycle done: geohashes=%d uploaded=%d", len(geos), ok)
        except Exception as e:
            logger.exception("[sync] periodic sync failed: %s", e)
        await asyncio.sleep(SYNC_INTERVAL_SEC)

@app.on_event("startup")
async def _start_sync():
    app.state.sync_task = asyncio.create_task(periodic_sync_loop())

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