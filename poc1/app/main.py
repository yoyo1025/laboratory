from fastapi import FastAPI, UploadFile, File

app = FastAPI()


@app.get("/health")
def health():
    return {"Hello": "World"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename, "contents": contents}