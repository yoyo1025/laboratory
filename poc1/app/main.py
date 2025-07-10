from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"Hello": "World"}

@app.post("/upload_pointcloud")
def upload():
    return {"Hello": "World"}