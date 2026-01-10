from fastapi import FastAPI, Request, status, BackgroundTasks, Response
import os
from urllib.parse import unquote
import logging
from minio import Minio
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask as StarletteBackgroundTask
from usecase.point_cloud_usecase import PointCloudUsecase
from usecase.stream_usecase import StreamUsecase
from datetime import timezone
from prometheus_fastapi_instrumentator import Instrumentator

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
    "service.name": "cloud-app" 
})


# Configure the OTLP exporter to send traces to our collector
otlp_exporter = OTLPSpanExporter(
    endpoint="cloud-otel-collector:4317", # The collector's gRPC endpoint
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
  server_address = "http://cloud-pyroscope:4040" , 
) 

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
    
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "cloud-minio:9100")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_root")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
     
mc = Minio(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=MINIO_SECURE)

def handle_record_sync(rec, mc: Minio):
    s3 = rec.get("s3", {})
    bucket = s3.get("bucket", {}).get("name")
    key = s3.get("object", {}).get("key")
    event = rec.get("eventName", "")
    
    # 文字化け対策
    if not bucket or not key:
        return
    key = unquote(key)
    
    PointCloudUsecase(mc, s3).save(key)

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
    key = f"{geohash}/latest/{geohash}.ply"
    obj, st = StreamUsecase(mc, key).stream()
    
    # HTTPヘッダを整形
    last_modified = st.last_modified
    # MinIOのlast_modifiedはTZ付きdatetime想定
    if last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=timezone.utc)
    headers = {
        "Content-Length": str(st.size),
        "Last-Modified": last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "Content-Disposition": f'attachment; filename="{geohash}.ply"',
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
    
Instrumentator().instrument(app).expose(app)