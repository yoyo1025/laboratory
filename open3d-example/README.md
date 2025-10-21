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
docker run --rm -v "$PWD:/app" mesh
```

### ICP による位置合わせ

open3d-example/alignment にて  
**ビルド**

```
docker build -t alignment .
```

**実行**

```
docker run --rm -v "$PWD:/app" alignment
```

### 重複率計算

open3d-example/duplication にて
**ビルド**

```
docker build -t duplication .
```

**実行**

```
docker run --rm -v "$PWD:/app" duplication
```

### 差分抽出

open3d-example/subtraction にて
**ビルド**

```
docker build -t subtraction .
```

**実行**

```
docker run --rm -v "$PWD:/app" subtraction
```
