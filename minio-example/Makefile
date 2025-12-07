start: clean-minio
	docker compose up --build -d

restart: stop
	docker compose up --build -d

stop:
	docker compose down -v

clean-minio:
	rm -rf docker/minio/data/minio-benchmark/tmp/

create-mb:
	mc alias set minio-benchmark http://localhost:7000 minio_root minio_password
	mc mb minio-benchmark/minio-benchmark
	mc anonymous set upload minio-benchmark/minio-benchmark/tmp
