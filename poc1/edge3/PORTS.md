# edge3 Port Inventory

| Port(s) | Component / Endpoint | Definition | Notes |
| --- | --- | --- | --- |
| 80 ← 8084 | `edge3-phpmyadmin` UI | `poc1/edge3/compose.yml:54-55` | Host port 8084 now fronts the phpMyAdmin container on port 80. |
| 3000 ← 3002 | Grafana server (`edge3-grafana`) | `poc1/edge3/compose.yml:112-115` | Grafana stays on 3000 internally; the host reaches it through 3002. |
| 3200 ← 3202 | Grafana Tempo HTTP API/UI | `poc1/edge3/compose.yml:138-139`<br>`poc1/edge3/tempo/tempo.yaml:1-2` | Tempo gRPC/HTTP services keep port 3200 but are exposed via host port 3202. |
| 3306 ← 3308 | MySQL (`edge3-mysql`) | `poc1/edge3/compose.yml:37-38`<br>`poc1/edge3/app/db.py:7-13` | MySQL still listens on 3306 inside the network; host access is mapped to 3308. |
| 4040 ← 4042 | Grafana Pyroscope (`edge3-pyroscope`) | `poc1/edge3/compose.yml:143-145`<br>`poc1/edge3/app/main.py:56-59` | Host reaches Pyroscope via 4042 while containers keep using 4040. |
| 6317 ← 4317 | OTLP gRPC endpoint | `poc1/edge3/compose.yml:127`<br>`poc1/edge3/app/main.py:39-42`<br>`poc1/edge3/otel-collection-config.yaml:5-13` | Collector gRPC receiver (4317) is published on host port 6317 so it can coexist with edge3/edge2. |
| 4318 | OTLP HTTP | `poc1/edge3/otel-collection-config.yaml:5-7` | HTTP receiver remains internal; no host port is exposed. |
| 8000 ← 8002 | FastAPI (`edge3-api`) + MinIO webhook + metrics | `poc1/edge3/compose.yml:6-7`<br>`poc1/edge3/Dockerfile:18-19`<br>`poc1/edge3/prometheus/prometheus.yml:9-13` | FastAPI keeps listening on 8000 internally; host clients use port 8002. |
| 8100 | Cloud API fallback (`host.docker.internal`) | `poc1/edge3/app/usecase/stream_usecase.py:39-47` | Same fallback endpoint shared across all edge nodes for cloud requests. |
| 9000 ← 9004 | MinIO API (`edge3-minio`) | `poc1/edge3/compose.yml:60-62`<br>`poc1/edge3/app/main.py:64-69`<br>`poc1/edge3/prometheus/prometheus.yml:14-18`<br>`poc1/edge3/test.txt:3-10` | Host-facing MinIO API is now on port 9004; internal traffic continues to use 9000. |
| 9001 ← 9005 | MinIO console | `poc1/edge3/compose.yml:60-63`<br>`poc1/edge3/compose.yml:71` | Console remains on 9001 inside Docker but is accessible via host port 9005. |
| 9090 ← 9092 | Prometheus (`edge3-prometheus`) | `poc1/edge3/compose.yml:101-102`<br>`poc1/edge3/prometheus/prometheus.yml:5-8`<br>`poc1/edge3/grafana/provisioning/datasources/datasource.yml:11-36` | Host connections should use 9092; Grafana still targets 9090 on the internal network. |
| 9100 | Cloud MinIO endpoint override | `poc1/edge3/compose.yml:18`<br>`poc1/edge3/app/main.py:71-76` | Edge3 also references the shared cloud MinIO address (`host.docker.internal:9100`). |
| 9104 ← 9106 | MySQL exporter (`edge3-mysql-exporter`) | `poc1/edge3/compose.yml:94-95`<br>`poc1/edge3/prometheus/prometheus.yml:19-22` | Container port 9104 is made available on the host as 9106. |
