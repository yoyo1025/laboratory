# 1) ベースイメージ
FROM python:3.12-slim

# 2) 必要な OS パッケージ
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 && \
    rm -rf /var/lib/apt/lists/*

# 3) 作業ディレクトリ
WORKDIR /app

# 4) 依存関係
COPY requirements.txt ./

RUN pip3 install --upgrade pip3 && pip3 install -r requirements.txt

# 5) アプリ本体
COPY . .

# 6) デフォルトコマンド（GUI は開かない想定）
CMD ["python", "open3d-example/main.py", "--no-view"]
