from fastapi import FastAPI, Request, status, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask as StarletteBackgroundTask
from urllib.parse import unquote
from minio import Minio
from usecase.aligmnent_usecase import AligmentUsecase
import open3d as o3d
import os, asyncio, tempfile, logging, secrets
from usecase.batch_usecase import BatchUsecase
from usecase.stream_usecase import StreamUsecase
from datetime import timezone
from pydantic import BaseModel, Field
import pygeohash
from decimal import Decimal
from db import SessionLocal
from repository.upload_reservation_repository import UploadReservationRepository
from prometheus_fastapi_instrumentator import Instrumentator

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

@app.get("/pointcloud/{geohash}")
def get_city_model(geohash: str):
    obj, st, source, bucket, key = StreamUsecase(mc, mc_cloud, geohash).stream()

    last_modified = st.last_modified
    if last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=timezone.utc)

    headers = {
        "Content-Length": str(st.size),
        "Last-Modified": last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "Content-Disposition": f'attachment; filename="{geohash}.ply"',
        "X-Pointcloud-Source": source,  # edge / cloud の識別
        "X-Pointcloud-Bucket": bucket,
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
    
class UploadPrepareRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    geohash_level: int = Field(..., ge=1, le=12)


upload_reservation_repo = UploadReservationRepository()


def _coordinate_parts(value: float):
    dec = Decimal(str(value))
    sign = "-" if dec.is_signed() else "+"
    dec_abs = dec.copy_abs()
    value_str = format(dec_abs, "f")
    integer_part, _, fraction_part = value_str.partition(".")
    if not fraction_part:
        fraction_part = "0"
    fraction_part = fraction_part.rstrip("0") or "0"
    return sign, integer_part, fraction_part


def _build_filename(lat: float, lon: float, level: int) -> str:
    lat_sign, lat_int, lat_frac = _coordinate_parts(lat)
    lon_sign, lon_int, lon_frac = _coordinate_parts(lon)
    return (
        f"x{lat_sign}{lat_int}-{lat_frac}-"
        f"y{lon_sign}{lon_int}-{lon_frac}-"
        f"{level}.ply"
    )


@app.post("/upload/prepare")
def prepare_upload(payload: UploadPrepareRequest):
    """予約を記録してアップロード用フォルダーを返す。"""
    geohash = pygeohash.encode(
        latitude=payload.lat,
        longitude=payload.lon,
        precision=payload.geohash_level,
    )
    filename = _build_filename(payload.lat, payload.lon, payload.geohash_level)
    token = secrets.token_hex(8)
    object_prefix = f"tmp/{geohash}/{token}"
    object_key = f"{object_prefix}/{filename}"

    db = SessionLocal()
    try:
        reservation_id = upload_reservation_repo.create_reservation(
            db,
            user_id=payload.user_id,
            geohash=geohash,
            geohash_level=payload.geohash_level,
            latitude=payload.lat,
            longitude=payload.lon,
            upload_object_key=object_key,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    ## 本来はここで認証やpresigned URL発行などを行う
    folder_path = f"{LOCAL_BUCKET}/{object_prefix}"
    return {
        "reservation_id": reservation_id,
        "bucket": LOCAL_BUCKET,
        "folder_path": folder_path,
        "object_key": object_key,
        "filename": filename,
        "geohash": geohash,
    }

Instrumentator().instrument(app).expose(app)