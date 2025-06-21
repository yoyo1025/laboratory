# laboratory
## open3d-example
### メッシュ化
open3d-example/meshにて  
**ビルド**
```
docker build -t mesh .
```
**実行**
```
docker run --rm -v "$PWD:/app" open3d-example
```

### ICPによる位置合わせ
open3d-example/meshにて  
**ビルド**
```
docker build -t alignment .
```
**実行**
```
docker run --rm -v "$PWD:/app" open3d-example
```
