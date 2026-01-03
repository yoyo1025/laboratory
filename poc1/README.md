## 環境構築（研究室サーバ）
### Make インストール
```bash
sudo apt install build-essential
```
### K6 インストール
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```
### mc インストール
このディレクトリにmcバイナリがダウンロードされる
```
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
./mc --help
```
### Docker インストール
- Docker関連パッケージをクリーンアップ
```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
```
- 必要なパッケージをインストール
```bash
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```
- Docker公式のGPGキー取得
```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```
- リポジトリ登録
```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```
- インストール可能なバージョンを確認

バージョン28代じゃないとAppArmor関連のエラーが発生することに注意
```bash
apt-cache madison docker-ce
```
- インストール
```bash
sudo apt-get install docker-ce=5:28.5.2-1~ubuntu.24.04~noble docker-ce-cli=5:28.5.2-1~ubuntu.24.04~noble containerd.io docker-compose-plugin
```
- containerd.ioのバージョンを指定

最新版を入れるとProxmox・LXC環境とcontainerd.ioの設定がミスマッチしてエラーになる
```bash
apt install containerd.io=1.7.28-1~ubuntu.24.04~noble
```

### Dockerネットワーク作成
```
sudo docker network create -d bridge cloud-network
sudo docker network create -d bridge edge1-network
sudo docker network create -d bridge edge2-network
sudo docker network create -d bridge edge3-network
```

### 起動方法
```
sudo make start-all
```
### MinIOバケット用意
```
make prepare-bucket-workstation
```
### 停止方法
```
sudo make stop-all
```
### 構築実験開始
```
k6 run ./k6/combined.js
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
sudo docker run --rm \
  -v edge1-minio-data:/data \
  alpine \
  sh -c 'cd /data/edge1-minio-data/tmp/xn1vqhzy && for d in *; do [ -d "$d" ] && echo "$d"; done | wc -l'
```