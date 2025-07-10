from fastapi import FastAPI, UploadFile, File, Form

app = FastAPI()


@app.get("/health")
def health():
    return {"Hello": "World"}

@app.post("/upload")
async def upload(file: UploadFile = File(...), lat: str = Form(), lon: str = Form()):
    contents = await file.read()
    return {"filename": file.filename, "lat": lat, "lon": lon, "contents": contents}