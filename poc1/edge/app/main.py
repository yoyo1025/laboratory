from fastapi import FastAPI, Request, status, BackgroundTasks, HTTPException, Response, APIRouter
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask as StarletteBackgroundTask
from urllib.parse import unquote
from minio import Minio
from usecase.aligmnent_usecase import AligmentUsecase
import open3d as o3d
import os, asyncio, tempfile, logging, secrets
from usecase.batch_usecase import BatchUsecase
from usecase.stream_usecase import StreamUsecase
from datetime import timezone, datetime
from email.utils import parsedate_to_datetime
from pydantic import BaseModel, Field
import pygeohash
from decimal import Decimal
from db import SessionLocal
from repository.upload_reservation_repository import UploadReservationRepository
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.routing import APIRoute 

# Tempo 用ライブラリ
from opentelemetry import trace 
from opentelemetry.sdk.trace import TracerProvider 
from opentelemetry.sdk.trace.export import BatchSpanProcessor 
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor 
from opentelemetry.sdk.resources import Resource 
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter 

# Pyroscope 用ライブラリ
import pyroscope

app = FastAPI()

# Define a resource to identify our service
resource = Resource(attributes={
    "service.name": "the-app" 
})

# Configure the OTLP exporter to send traces to our collector
otlp_exporter = OTLPSpanExporter(
    endpoint="edge1-otel-collector:4317", # The collector's gRPC endpoint
    insecure=True 
)

# Set up the tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Create a BatchSpanProcessor to send traces in batches
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument the app automatically
FastAPIInstrumentor.instrument_app(app)

pyroscope.configure( 
  application_name = "backend" , 
  server_address = "http://edge1-pyroscope:4040" , 
) 

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

# ローカルMinioクライアント初期化
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "edge1-minio:9000")
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

class  PyroscopeRoute ( APIRoute ): 
    def  get_route_handler ( self ): 
        original_handler = super ().get_route_handler() 
        async  def  custom_handler ( request: Request ) -> Response: 
            route = request.scope.get( "route" ) 
            template = getattr (route, "path_format" , getattr (route, "path" , request.url.path)) 
            method = request.method 
            tag = f"{method}:{template}" 
            with pyroscope.tag_wrapper({ "endpoint" : tag}): 
                return  await original_handler(request) 
        return custom_handler 

api_router = APIRouter(prefix= "" , route_class=PyroscopeRoute) 

app.include_router(api_router) 

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

@api_router.post("/minio/webhook")
async def PCLocalAlignmentHandler(request: Request, background: BackgroundTasks):
    try:
        body = await request.json()
    except Exception:
        body = {}

    records = body.get("Records", [body]) if isinstance(body, dict) else []
    for rec in records:
        background.add_task(handle_record_sync, rec, mc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@api_router.get("/pointcloud/{geohash}")
def get_city_model(geohash: str):
    # ユースケース：まずエッジMinIOを探し、無ければクラウドAPI(HTTP)へフォールバック
    # obj: 本体(ファイルライク/HTTPストリーム), st: メタ情報(MinIO Stat or HTTPヘッダdict)
    # source/bucket/key: デバッグ・トレース用メタ
    obj, st, source, bucket, key = StreamUsecase(mc, mc_cloud, geohash).stream()

    # --- Last-Modified を統一して取り出す（MinIO属性 or HTTPヘッダ） ---
    lm = getattr(st, "last_modified", None) or (st.get("Last-Modified") if isinstance(st, dict) else None)
    # 文字列（HTTPヘッダ）の場合は datetime へパース
    if isinstance(lm, str):
        try:
            lm = parsedate_to_datetime(lm)
        except Exception:
            lm = None
    # 値が無ければ現在UTC、TZ無しならUTCを付与
    if lm is None:
        lm = datetime.now(timezone.utc)
    elif lm.tzinfo is None:
        lm = lm.replace(tzinfo=timezone.utc)

    # --- Content-Length を統一して取り出す（MinIO属性 or HTTPヘッダ） ---
    size_val = getattr(st, "size", None)
    if size_val is None and isinstance(st, dict):
        cl = st.get("Content-Length")
        size_val = int(cl) if cl and cl.isdigit() else None  # 数値にできない場合は未設定（チャンク配信）

    # --- 応答ヘッダを組み立て（取得元をカスタムヘッダで可視化） ---
    headers = {
        **({"Content-Length": str(size_val)} if isinstance(size_val, int) else {}),  # 分かるときだけ付与
        "Last-Modified": lm.strftime("%a, %d %b %Y %H:%M:%S GMT"),  # RFC1123
        "Content-Disposition": f'attachment; filename="{geohash}.ply"',  # ダウンロード名
        "X-Pointcloud-Source": source,  # edge / cloud-http
        "X-Pointcloud-Bucket": bucket,
        "X-Pointcloud-Key": key,
    }

    # --- 本体のストリームを最小分岐で生成（メモリに載せず転送） ---
    chunk = 32 * 1024  # 32KB チャンク
    if hasattr(obj, "stream"):
        # MinIOオブジェクト（.stream が提供される）
        body_iter = obj.stream(chunk)
    elif hasattr(obj, "iter_content"):
        # requests.Response（HTTP経由）
        body_iter = obj.iter_content(chunk_size=chunk)
    elif hasattr(obj, "read"):
        # urllib3 の raw など read() しかない場合
        body_iter = iter(lambda: obj.read(chunk), b"")
    else:
        # 想定外の型
        raise HTTPException(status_code=502, detail="unsupported stream body object")

    # --- StreamingResponse で逐次返却。送信完了後に close（あれば）を実行 ---
    return StreamingResponse(
        body_iter,
        media_type="application/octet-stream",
        headers=headers,
        background=StarletteBackgroundTask(getattr(obj, "close", lambda: None)),
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


@api_router.post("/upload/prepare")
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