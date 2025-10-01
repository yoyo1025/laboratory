FROM python:3.9

RUN apt-get update \
    && apt install -y default-mysql-client \
    && apt-get -y install gcc libmariadb-dev \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libgomp1 \   
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 5) アプリ本体
COPY . .

# 6) デフォルトコマンド（GUI は開かない想定）
CMD ["python", "main.py", "--no-view"]