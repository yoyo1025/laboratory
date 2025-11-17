from pydantic import BaseModel

class UploadResponse(BaseModel):
    filename: str
    lat: str
    lon: str
    geohash: str
    saved_path: str