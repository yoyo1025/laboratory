.PHONY: start stop start-all stop-all \
	start-cloud stop-cloud \
	start-edge1 stop-edge1 \
	start-edge2 stop-edge2 \
	start-edge3 stop-edge3 \
	clean-minio \
	collect-stream-logs collect-stream-logs-all \
	collect-stream-stats collect-stream-stats-all

COMPOSE ?= docker compose

LOG_DIR ?= result/deliverly
DURATION ?= 180
INTERVAL ?= 1

CLOUD_COMPOSE  = -f cloud/compose.yml
EDGE1_COMPOSE  = -f edge1/compose.yml
EDGE2_COMPOSE  = -f edge2/compose.yml
EDGE3_COMPOSE  = -f edge3/compose.yml

ALL_COMPOSE = $(CLOUD_COMPOSE) $(EDGE1_COMPOSE) $(EDGE2_COMPOSE) $(EDGE3_COMPOSE)

start: start-all
stop: stop-all

# ---- all projects ----
start-all: clean-minio stop-all
	$(COMPOSE) -p cloud  $(CLOUD_COMPOSE) up -d --build
	$(COMPOSE) -p edge1  $(EDGE1_COMPOSE) up -d --build
	$(COMPOSE) -p edge2  $(EDGE2_COMPOSE) up -d --build
	$(COMPOSE) -p edge3  $(EDGE3_COMPOSE) up -d --build

stop-all:
	$(COMPOSE) -p cloud  $(CLOUD_COMPOSE) down -v
	$(COMPOSE) -p edge1  $(EDGE1_COMPOSE) down -v
	$(COMPOSE) -p edge2  $(EDGE2_COMPOSE) down -v
	$(COMPOSE) -p edge3  $(EDGE3_COMPOSE) down -v

# ---- individual projects ----
start-cloud:
	$(COMPOSE) -p cloud $(CLOUD_COMPOSE) up -d --build

stop-cloud:
	$(COMPOSE) -p cloud $(CLOUD_COMPOSE) down -v

start-edge1:
	$(COMPOSE) -p edge1 $(EDGE1_COMPOSE) up -d --build

stop-edge1:
	$(COMPOSE) -p edge1 $(EDGE1_COMPOSE) down -v

start-edge2:
	$(COMPOSE) -p edge2 $(EDGE2_COMPOSE) up -d --build

stop-edge2:
	$(COMPOSE) -p edge2 $(EDGE2_COMPOSE) down -v

start-edge3:
	$(COMPOSE) -p edge3 $(EDGE3_COMPOSE) up -d --build

stop-edge3:
	$(COMPOSE) -p edge3 $(EDGE3_COMPOSE) down -v

# ---- data cleanup ----
clean-minio:
	rm -rf edge1/docker/minio/data/edge1-point-cloud/tmp/xn1vqhzy
	rm -rf edge1/docker/minio/data/edge1-point-cloud/xn1vqhzy/uploads
	rm -rf edge2/docker/minio/data/edge2-point-cloud/tmp/xn1vqhzy
	rm -rf edge2/docker/minio/data/edge2-point-cloud/xn1vqhzy/uploads
	rm -rf edge3/docker/minio/data/edge3-point-cloud/tmp/xn1vqhzy
	rm -rf edge3/docker/minio/data/edge3-point-cloud/xn1vqhzy/uploads

prepare-bucket:
	mc alias set cloud-minio  http://localhost:9100 minio_root minio_password
	mc alias set edge1-minio  http://localhost:9000 minio_root minio_password
	mc alias set edge2-minio  http://localhost:9002 minio_root minio_password
	mc alias set edge3-minio  http://localhost:9004 minio_root minio_password

	mc ls cloud-minio/cloud-point-cloud        >/dev/null 2>&1 || mc mb cloud-minio/cloud-point-cloud
	mc ls edge1-minio/edge1-point-cloud        >/dev/null 2>&1 || mc mb edge1-minio/edge1-point-cloud
	mc ls edge2-minio/edge2-point-cloud        >/dev/null 2>&1 || mc mb edge2-minio/edge2-point-cloud
	mc ls edge3-minio/edge3-point-cloud        >/dev/null 2>&1 || mc mb edge3-minio/edge3-point-cloud

	mc anonymous set upload cloud-minio/cloud-point-cloud/tmp
	mc anonymous set upload edge1-minio/edge1-point-cloud/tmp
	mc anonymous set upload edge2-minio/edge2-point-cloud/tmp
	mc anonymous set upload edge3-minio/edge3-point-cloud/tmp

	mc event add cloud-minio/cloud-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"
	mc event add edge1-minio/edge1-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"
	mc event add edge2-minio/edge2-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"
	mc event add edge3-minio/edge3-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"

	mc cp ./data/global-model.ply cloud-minio/cloud-point-cloud/aaaaaaaa/latest/aaaaaaaa.ply
	mc cp ./data/local-model.ply edge1-minio/edge1-point-cloud/bbbbbbbb/latest/bbbbbbbb.ply
	mc cp ./data/local-model.ply edge2-minio/edge2-point-cloud/cccccccc/latest/cccccccc.ply
	mc cp ./data/local-model.ply edge3-minio/edge3-point-cloud/dddddddd/latest/dddddddd.ply

prepare-bucket-workstation:
	./mc alias set cloud-minio  http://localhost:9100 minio_root minio_password
	./mc alias set edge1-minio  http://localhost:9000 minio_root minio_password
	./mc alias set edge2-minio  http://localhost:9002 minio_root minio_password
	./mc alias set edge3-minio  http://localhost:9004 minio_root minio_password

	./mc ls cloud-minio/cloud-point-cloud        >/dev/null 2>&1 || ./mc mb cloud-minio/cloud-point-cloud
	./mc ls edge1-minio/edge1-point-cloud        >/dev/null 2>&1 || ./mc mb edge1-minio/edge1-point-cloud
	./mc ls edge2-minio/edge2-point-cloud        >/dev/null 2>&1 || ./mc mb edge2-minio/edge2-point-cloud
	./mc ls edge3-minio/edge3-point-cloud        >/dev/null 2>&1 || ./mc mb edge3-minio/edge3-point-cloud

	./mc anonymous set upload cloud-minio/cloud-point-cloud/tmp
	./mc anonymous set upload edge1-minio/edge1-point-cloud/tmp
	./mc anonymous set upload edge2-minio/edge2-point-cloud/tmp
	./mc anonymous set upload edge3-minio/edge3-point-cloud/tmp

	./mc event add cloud-minio/cloud-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"
	./mc event add edge1-minio/edge1-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"
	./mc event add edge2-minio/edge2-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"
	./mc event add edge3-minio/edge3-point-cloud arn:minio:sqs::FASTAPI:webhook --event put --prefix "tmp/" --suffix ".ply"

	./mc cp ./data/global-model.ply cloud-minio/cloud-point-cloud/aaaaaaaa/latest/aaaaaaaa.ply
	./mc cp ./data/local-model.ply edge1-minio/edge1-point-cloud/bbbbbbbb/latest/bbbbbbbb.ply
	./mc cp ./data/local-model.ply edge2-minio/edge2-point-cloud/cccccccc/latest/cccccccc.ply
	./mc cp ./data/local-model.ply edge3-minio/edge3-point-cloud/dddddddd/latest/dddddddd.ply

count-ply: count-ply1 count-ply2 count-ply3

count-ply1:
	docker run --rm \
	  -v edge1-minio-data:/data \
	  alpine \
	  sh -c 'cd /data/edge1-point-cloud/xn1vqhzy/uploads && for d in *; do [ -d "$$d" ] && echo "$$d"; done | wc -l'

count-ply2:
	docker run --rm \
	  -v edge2-minio-data:/data \
	  alpine \
	  sh -c 'cd /data/edge2-point-cloud/xn1vqhzy/uploads && for d in *; do [ -d "$$d" ] && echo "$$d"; done | wc -l'

count-ply3:
	docker run --rm \
	  -v edge3-minio-data:/data \
	  alpine \
	  sh -c 'cd /data/edge3-point-cloud/xn1vqhzy/uploads && for d in *; do [ -d "$$d" ] && echo "$$d"; done | wc -l'

# ---- stream log/metrics collection ----
collect-stream-logs:
	COMPOSE="$(COMPOSE)" SINCE="$(SINCE)" UNTIL="$(UNTIL)" ./scripts/collect_stream_logs.sh $(EDGE) $(RPS) $(LOG_DIR)

collect-stream-logs-all:
	COMPOSE="$(COMPOSE)" SINCE="$(SINCE)" UNTIL="$(UNTIL)" ./scripts/collect_stream_logs.sh 1 $(RPS) $(LOG_DIR)
	COMPOSE="$(COMPOSE)" SINCE="$(SINCE)" UNTIL="$(UNTIL)" ./scripts/collect_stream_logs.sh 2 $(RPS) $(LOG_DIR)
	COMPOSE="$(COMPOSE)" SINCE="$(SINCE)" UNTIL="$(UNTIL)" ./scripts/collect_stream_logs.sh 3 $(RPS) $(LOG_DIR)

collect-stream-stats:
	COMPOSE="$(COMPOSE)" INTERVAL=$(INTERVAL) ./scripts/collect_stream_stats.sh $(EDGE) $(RPS) $(DURATION) $(LOG_DIR)

collect-stream-stats-all:
	COMPOSE="$(COMPOSE)" INTERVAL=$(INTERVAL) ./scripts/collect_stream_stats.sh 1 $(RPS) $(DURATION) $(LOG_DIR) & \
	COMPOSE="$(COMPOSE)" INTERVAL=$(INTERVAL) ./scripts/collect_stream_stats.sh 2 $(RPS) $(DURATION) $(LOG_DIR) & \
	COMPOSE="$(COMPOSE)" INTERVAL=$(INTERVAL) ./scripts/collect_stream_stats.sh 3 $(RPS) $(DURATION) $(LOG_DIR) & \
	wait
