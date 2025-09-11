FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 

RUN apt-get update && apt-get install --no-install-recommends -y \
    python3-pip libegl1 libgl1 libgomp1 libx11-6 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir "numpy==1.26.*" "open3d==0.18.*"

WORKDIR /app
COPY . .
CMD ["python3", "-u", "main.py"]