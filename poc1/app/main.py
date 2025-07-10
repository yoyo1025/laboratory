from fastapi import FastAPI, UploadFile, File, Form
import pygeohash

# Geohashの桁数
GEOHASH_LEVEL = 8

app = FastAPI()


@app.get("/health")
def health():
    return {"Hello": "World"}

@app.post("/upload")
async def upload(file: UploadFile = File(...), lat: str = Form(), lon: str = Form()):
    geohash = pygeohash.encode(latitude=float(lat), longitude=float(lon), precision=GEOHASH_LEVEL)
    contents = await file.read()
    return {"filename": file.filename, "lat": lat, "lon": lon, "geohash": geohash, "contents": contents}