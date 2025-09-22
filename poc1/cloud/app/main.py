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

app = FastAPI()
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

@app.get("/{geohash}")
def get_city_model(geohash: str):
    key = f"{geohash}/{geohash}.ply"
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