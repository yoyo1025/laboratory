### MinIO内のフォルダ構成
- エッジ側
```
edge-point-cloud/
    ├── tmp/
    │   └── xn1vqhzy/
    │       └── ハッシュ値/
    │           └── x座標-y座標-geohashレベル.ply
    └── xn1vqhzy/
        ├── latest/
        │   └── latest.ply
        └── xn1vqhzy/
            └── uploads/
                └── タイムスタンプ-x座標-y座標-geohashレベル.ply
```

```
docker run --rm \
  -v edge1-minio-data:/data \
  alpine \
  sh -c 'cd /data/edge1-minio-data/tmp/xn1vqhzy && for d in *; do [ -d "$d" ] && echo "$d"; done | wc -l'
```