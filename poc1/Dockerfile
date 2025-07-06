FROM python:3.9-slim

# Open3D が要求するライブラリを追加
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libgomp1 \   
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY ./app ./

# FastAPI は 8000 ポートで起動するように変更
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
