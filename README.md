# laboratory

## open3d-example

### メッシュ化

open3d-example/mesh にて  
**ビルド**

```
docker build -t mesh .
```

**実行**

```
docker run --rm -v "$PWD:/app" open3d-example
```

### ICP による位置合わせ

open3d-example/alignment にて  
**ビルド**

```
docker build -t alignment .
```

**実行**

```
docker run --rm -v "$PWD:/app" open3d-example
```
