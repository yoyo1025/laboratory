.PHONY: start stop start-all stop-all \
	start-cloud stop-cloud \
	start-edge1 stop-edge1 \
	start-edge2 stop-edge2 \
	start-edge3 stop-edge3 \
	clean-minio

COMPOSE ?= docker compose

CLOUD_COMPOSE  = -f cloud/compose.yml
EDGE1_COMPOSE  = -f edge1/compose.yml
EDGE2_COMPOSE  = -f edge2/compose.yml
EDGE3_COMPOSE  = -f edge3/compose.yml

ALL_COMPOSE = $(CLOUD_COMPOSE) $(EDGE1_COMPOSE) $(EDGE2_COMPOSE) $(EDGE3_COMPOSE)

start: start-all
stop: stop-all

# ---- all projects ----
start-all: clean-minio
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
