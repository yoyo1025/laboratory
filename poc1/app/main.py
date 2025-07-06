import os, tempfile, json, numpy as np, open3d as o3d, pygeohash as geohash
import psycopg2, psycopg2.extras
from fastapi import FastAPI, UploadFile, File, Form

app = FastAPI()

# DB接続情報は環境変数で
DB_PARAMS = dict(
    host=os.getenv("PGHOST", "db"),
    dbname=os.getenv("PGDB", "pointclouds"),
    user=os.getenv("PGUSER", "postgres"),
    password=os.getenv("PGPASSWORD", "mysecretpassword"),
)
db_conn = psycopg2.connect(**DB_PARAMS)
psycopg2.extras.register_default_jsonb(loads=lambda x: x)  # list→array変換を簡潔に

@app.get("/health")
def health():
    return {"Hello": "World"}

@app.post("/upload_pointcloud")
async def upload_pointcloud(
    file: UploadFile = File(...),
    lat: float = Form(...),
    lon: float = Form(...)
):
    ghash = geohash.encode(lat, lon, precision=8)
    print(f"Geohash: {ghash}")
    
    # 一時ファイルに保存してOpen3Dで読み込み
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ply") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    pcd = o3d.io.read_point_cloud(tmp_path)
    os.remove(tmp_path)  # 後片付け

    pts = np.asarray(pcd.points)  # (N,3)
    if pts.size == 0:
        return {"status": "fail", "reason": "empty pointcloud"}
    
    flat = pts.reshape(-1).astype(float).tolist()
    pg_array = "{" + ",".join(map(str, flat)) + "}"     # ← 1D double precision[]
    cur = db_conn.cursor()

    cur.execute(
        """
        INSERT INTO pc_data (ts, geohash8, patch, point_cnt)
        VALUES (NOW(), %(gh)s,
                PC_MakePatch(1, %(arr)s::double precision[]),
                %(cnt)s);
        """,
        {"gh": ghash, "arr": pg_array, "cnt": pts.shape[0]},
    )
    db_conn.commit()


    return {"status": "success", "inserted_points": pts.shape[0], "geohash": ghash}
