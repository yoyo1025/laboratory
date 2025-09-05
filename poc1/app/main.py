from fastapi import Depends, FastAPI, Request, UploadFile, File, Form, Query, HTTPException, status
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import urllib.parse
import pygeohash
from response import upload_response
import os
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, TIMESTAMP, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import FetchedValue
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from urllib.parse import unquote
import logging
from minio import Minio

# Geohashの桁数
GEOHASH_LEVEL = 8

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

# 拡張子指定
ALLOWED_EXT = {".ply"}
# プロジェクトルートパス指定
APP_ROOT = Path(__file__).resolve().parent

db_user = os.getenv("DB_USER", "sample_user")
db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", "sample_password"))
db_host = os.getenv("DB_HOST", "mysql")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME", "sample_db")

SQLALCHEMY_DATABASE_URI = (
    f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    db = SessionLocal ()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()

class Item(Base):
    __tablename__ = "item"         # autoload は書かない
    item_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(50), nullable=False)
    price = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=FetchedValue())
    updated_at = Column(TIMESTAMP, server_default=FetchedValue())

# Request Body
class ItemRequest(BaseModel):
    name: str = Query(..., max_length=50)
    price: float

# GetItemByName
@app.get("/item")
def get_item(id: int = None, name: str = Query(None, max_length=50), db: SessionLocal = Depends(get_session)):
    if id is not None:
        result_set = db.query(Item).filter(Item.item_id == id).all()
    elif name is not None:
        result_set = db.query(Item).filter(Item.name == name).all()
    else:
        result_set = db.query(Item).all()    
    response_body = jsonable_encoder({"list": result_set})
    return JSONResponse(status_code=status.HTTP_200_OK, content=response_body)

# CreateItem
@app.post("/item")
def create_item(request: ItemRequest, db: SessionLocal = Depends(get_session)):
    item = Item(
                name = request.name,
                price = request.price
            )
    db.add(item)
    db.commit()
    response_body = jsonable_encoder({"item_id" : item.item_id})
    return JSONResponse(status_code=status.HTTP_200_OK, content=response_body)

# UpdateItem
@app.put("/item/{id}")
def update_item(id: int, request: ItemRequest, db: SessionLocal = Depends(get_session)):
    item = db.query(Item).filter(Item.item_id == id).first()
    if item is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND)
    item.name = request.name
    item.price = request.price
    db.commit()
    return JSONResponse(status_code=status.HTTP_200_OK)

# DeleteItem
@app.delete("/item/{id}")
def delete_item(id: int, db: SessionLocal = Depends(get_session)):
    db.query(Item).filter(Item.item_id == id).delete()
    db.commit()
    return JSONResponse(status_code=status.HTTP_200_OK)


@app.get("/health")
def health():
    return {"Hello": "World"}

@app.post("/upload", response_model=upload_response.UploadResponse)
async def upload(file: UploadFile = File(...), lat: str = Form(), lon: str = Form()):
    # ファイル拡張子チェック
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=".plyだけ許可されています。")

    # Geohash計算
    geohash = pygeohash.encode(latitude=float(lat), longitude=float(lon), precision=GEOHASH_LEVEL)
    
    # 保存パス生成
    timestamp = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d_%H%M%S")
    save_dir = APP_ROOT / "store" / "edge" / geohash
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{timestamp}.ply"

    # ファイル保存
    contents = await file.read()
    save_path.write_bytes(contents)

    return {
        "filename": file.filename,
        "lat": lat,
        "lon": lon,
        "geohash": geohash,
        "saved_path": str(save_path.relative_to(APP_ROOT))
    }
    
    
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_root")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
mc = Minio(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=MINIO_SECURE)    
    
@app.post("/minio/webhook")
async def minio_webhook(request: Request):
    body = await request.json()
    logger.info(body)
    records = body.get("Records", [body]) if isinstance(body, dict) else []

    handled = 0
    for rec in records:
        s3 = rec.get("s3", {})
        bucket = s3.get("bucket", {}).get("name")
        key = s3.get("object", {}).get("key")
        event = rec.get("eventName", "")

        if not bucket or not key:
            continue

        key = unquote(key)
        if not str(event).startswith("s3:ObjectCreated") or not key.endswith(".txt"):
            continue

        resp = mc.get_object(bucket, key)
        try:
            text = resp.read().decode("utf-8", errors="replace")
            logger.info(f"[MinIO] {bucket}/{key}\n{text}")
        finally:
            resp.close(); resp.release_conn()
        handled += 1

    return {"ok": True, "handled": handled}