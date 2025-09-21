from fastapi import Depends, FastAPI, Request, UploadFile, File, Form, Query, HTTPException, status, BackgroundTasks, Response
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import urllib.parse
import pygeohash
from response import upload_response
import os
from pydantic import BaseModel
from sqlalchemy import Column, TIMESTAMP, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import FetchedValue
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from urllib.parse import unquote
import logging
from minio import Minio
from usecase.aligmnent_usecase import AligmentUsecase  
import tempfile
import open3d as o3d

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
    
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_root")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
mc = Minio(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=MINIO_SECURE)

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