### Dockerネットワーク作成
```
docker network create -d bridge cloud-network
```
```
docker network create -d bridge edge1-network
```
```
docker network create -d bridge edge2-network
```
```
docker network create -d bridge edge3-network
```
### 起動方法
```
make start-all
```
### 停止方法
```
make stop-all
```

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