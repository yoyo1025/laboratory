# edge1 Port Inventory

| Port(s) | Component / Endpoint | Definition | Notes |
| --- | --- | --- | --- |
| 80 ← 8082 | `edge1-phpmyadmin` UI | `poc1/edge1/compose.yml:54-55` | Host port 8082 forwards to the container’s port 80 so phpMyAdmin can expose the MySQL UI in the browser. |
| 3000 | Grafana server (`edge1-grafana`) | `poc1/edge1/compose.yml:112-115` | Default Grafana HTTP port for dashboards. |
| 3200 | Grafana Tempo HTTP API/UI | `poc1/edge1/compose.yml:138-139`<br>`poc1/edge1/tempo/tempo.yaml:1-2`<br>`poc1/edge1/grafana/provisioning/datasources/datasource.yml:50-54` | Tempo listens on 3200 for trace queries; Grafana connects to the same URL. |
| 3306 | MySQL (`edge1-mysql`) | `poc1/edge1/compose.yml:37-38`<br>`poc1/edge1/app/db.py:7-13` | Core DB service; the FastAPI app defaults to this port via `DB_PORT`. |
| 4040 | Grafana Pyroscope (`edge1-pyroscope`) | `poc1/edge1/compose.yml:143-145`<br>`poc1/edge1/app/main.py:56-59`<br>`poc1/edge1/grafana/provisioning/datasources/datasource.yml:58-62` | Used for continuous profiling ingest/UI and Grafana’s Pyroscope data source. |
| 4317 | OTLP gRPC | `poc1/edge1/compose.yml:127`<br>`poc1/edge1/app/main.py:39-42`<br>`poc1/edge1/otel-collection-config.yaml:5-6`<br>`poc1/edge1/otel-collection-config.yaml:11-13`<br>`poc1/edge1/tempo/tempo.yaml:5-9` | Collector listens on 4317, the FastAPI app exports traces to it, and Tempo receives gRPC traffic from the collector on the same port. |
| 4318 | OTLP HTTP | `poc1/edge1/otel-collection-config.yaml:5-7` | HTTP alternative receiver enabled on the collector (not exposed via Docker ports). |
| 8000 | FastAPI (`edge1-api`) + MinIO webhook + metrics | `poc1/edge1/compose.yml:6-7`<br>`poc1/edge1/Dockerfile:18-19`<br>`poc1/edge1/compose.yml:70`<br>`poc1/edge1/prometheus/prometheus.yml:9-13` | Core API port, also targeted by MinIO’s webhook (`/minio/webhook`) and scraped by Prometheus. |
| 8100 | Cloud API fallback (`host.docker.internal`) | `poc1/edge1/app/usecase/stream_usecase.py:39-47` | When the edge MinIO miss occurs, the stream use case proxies the request to the cloud API on 8100. |
| 9000 | MinIO API (`edge1-minio`) | `poc1/edge1/compose.yml:60-62`<br>`poc1/edge1/app/main.py:64-69`<br>`poc1/edge1/prometheus/prometheus.yml:14-18`<br>`poc1/edge1/test.txt:3-10` | Primary S3-compatible API used by the app, Prometheus (metrics endpoint), the `mc` bootstrap, and manual curl tests. |
| 9001 | MinIO console | `poc1/edge1/compose.yml:60-63`<br>`poc1/edge1/compose.yml:71` | Exposes the MinIO web console; the server is started with `--console-address ":9001"`. |
| 9090 | Prometheus (`edge1-prometheus`) | `poc1/edge1/compose.yml:101-102`<br>`poc1/edge1/prometheus/prometheus.yml:5-8`<br>`poc1/edge1/grafana/provisioning/datasources/datasource.yml:11-36` | Prometheus UI/API plus the endpoint Grafana uses for metrics queries. |
| 9100 | Cloud MinIO endpoint override | `poc1/edge1/compose.yml:18`<br>`poc1/edge1/app/main.py:71-76` | Default `CLOUD_MINIO_ENDPOINT` so the edge app can reach the cloud MinIO at `host.docker.internal:9100`. |
| 9104 | MySQL exporter (`edge1-mysql-exporter`) | `poc1/edge1/compose.yml:94-95`<br>`poc1/edge1/prometheus/prometheus.yml:19-22` | Exposes mysqld-exporter metrics to Prometheus. |
