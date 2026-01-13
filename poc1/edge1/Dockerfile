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

COPY ./app ./

# FastAPI は 8000 ポートで起動するように変更
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]