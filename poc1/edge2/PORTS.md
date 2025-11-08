# edge2 Port Inventory

| Port(s) | Component / Endpoint | Definition | Notes |
| --- | --- | --- | --- |
| 80 ← 8083 | `edge1-phpmyadmin` UI | `poc1/edge2/compose.yml:54-55` | Host 8083 forwards to container port 80 so phpMyAdmin can publish the MySQL UI. |
| 3000 ← 3001 | Grafana server (`edge1-grafana`) | `poc1/edge2/compose.yml:112-115` | Grafana still listens on 3000 in the container but is exposed on host port 3001. |
| 3200 ← 3201 | Grafana Tempo HTTP API/UI | `poc1/edge2/compose.yml:138-139`<br>`poc1/edge2/tempo/tempo.yaml:1-2` | Tempo’s gRPC/HTTP server stays on 3200 internally; host access uses 3201. |
| 3306 ← 3307 | MySQL (`edge1-mysql`) | `poc1/edge2/compose.yml:37-38`<br>`poc1/edge2/app/db.py:7-13` | Application connects to port 3306 inside the network; the host reaches it via 3307. |
| 4040 ← 4041 | Grafana Pyroscope (`edge1-pyroscope`) | `poc1/edge2/compose.yml:143-145`<br>`poc1/edge2/app/main.py:56-59` | Pyroscope listens on 4040 in-container and is published on host 4041. |
| 5317 ← 4317 | OTLP gRPC endpoint | `poc1/edge2/compose.yml:127`<br>`poc1/edge2/app/main.py:39-42`<br>`poc1/edge2/otel-collection-config.yaml:5-13` | Collector gRPC receiver stays on 4317 internally but is mapped to host port 5317 to avoid collisions. |
| 4318 | OTLP HTTP | `poc1/edge2/otel-collection-config.yaml:5-7` | HTTP receiver enabled for completeness; it is not published to the host. |
| 8000 ← 8001 | FastAPI (`edge1-api`) + MinIO webhook + metrics | `poc1/edge2/compose.yml:6-7`<br>`poc1/edge2/Dockerfile:18-19`<br>`poc1/edge2/prometheus/prometheus.yml:9-13` | Container keeps port 8000; host access is via 8001. MinIO still calls `edge1-api:8000` inside the network. |
| 8100 | Cloud API fallback (`host.docker.internal`) | `poc1/edge2/app/usecase/stream_usecase.py:39-47` | Same HTTP fallback path as edge1; no host publication change is required. |
| 9000 ← 9002 | MinIO API (`edge1-minio`) | `poc1/edge2/compose.yml:60-62`<br>`poc1/edge2/app/main.py:64-69`<br>`poc1/edge2/prometheus/prometheus.yml:14-18`<br>`poc1/edge2/test.txt:3-10` | Container serves port 9000; host reaches it through 9002 (and the sample curls were updated accordingly). |
| 9001 ← 9003 | MinIO console | `poc1/edge2/compose.yml:60-63`<br>`poc1/edge2/compose.yml:71` | Console stays on 9001 internally but is exposed via host port 9003. |
| 9090 ← 9091 | Prometheus (`edge1-prometheus`) | `poc1/edge2/compose.yml:101-102`<br>`poc1/edge2/prometheus/prometheus.yml:5-8`<br>`poc1/edge2/grafana/provisioning/datasources/datasource.yml:11-36` | Host now connects on 9091. Grafana still reaches the service on 9090 inside the network. |
| 9100 | Cloud MinIO endpoint override | `poc1/edge2/compose.yml:18`<br>`poc1/edge2/app/main.py:71-76` | The edge service still talks to cloud MinIO via `host.docker.internal:9100`; this port is shared across environments by design. |
| 9104 ← 9105 | MySQL exporter (`edge1-mysql-exporter`) | `poc1/edge2/compose.yml:94-95`<br>`poc1/edge2/prometheus/prometheus.yml:19-22` | Container port 9104 is now exposed as host 9105. |
