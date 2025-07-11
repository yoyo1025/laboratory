from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import pygeohash

# Geohashの桁数
GEOHASH_LEVEL = 8

app = FastAPI()

class UploadResponse(BaseModel):
    filename: str
    lat: str
    lon: str
    geohash: str
    saved_path: str

ALLOWED_EXT = {".ply"}
APP_ROOT = Path(__file__).resolve().parent

@app.get("/health")
def health():
    return {"Hello": "World"}

@app.post("/upload", response_model=UploadResponse)
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