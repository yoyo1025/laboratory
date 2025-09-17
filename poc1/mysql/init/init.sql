USE sample_db;

-- areas: 領域
DROP TABLE IF EXISTS areas;
CREATE TABLE IF NOT EXISTS areas (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  geohash     VARCHAR(12)     NOT NULL,
  geohash_level   TINYINT UNSIGNED NULL,
  created_at  TIMESTAMP(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at  TIMESTAMP(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_areas_geohash (geohash),
  KEY idx_areas_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO areas (geohash, geohash_level) VALUES ("xn1vghzy", 8);

-- pc_uploaded_history: アップロード履歴
DROP TABLE IF EXISTS pc_uploaded_history;
CREATE TABLE IF NOT EXISTS pc_uploaded_history (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  area_id       BIGINT UNSIGNED NOT NULL,
  file_name     VARCHAR(255)    NOT NULL,
  object_key    VARCHAR(512)    NOT NULL,
  size_bytes    BIGINT UNSIGNED NULL,
  content_type  VARCHAR(64)     NULL,
  uploaded_at   TIMESTAMP(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_pu_area_time (area_id, uploaded_at),
  KEY idx_pu_object_key (object_key),
  CONSTRAINT fk_pu_area
    FOREIGN KEY (area_id) REFERENCES areas(id)
    ON DELETE CASCADE
    ON UPDATE RESTRICT,
  CONSTRAINT uq_pu_area_object UNIQUE (area_id, object_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO pc_uploaded_history (area_id, file_name, object_key, size_bytes, content_type) VALUES (1, 'latest.ply', 'xn1vghzy/latest/latest.ply', 2800, 'application/octet-stream');

-- area_latest: 各エリアの最新アップロードを1行で保持（循環を分離）
DROP TABLE IF EXISTS area_latest;
CREATE TABLE IF NOT EXISTS area_latest (
  area_id    BIGINT UNSIGNED NOT NULL,
  upload_id  BIGINT UNSIGNED NOT NULL,
  updated_at TIMESTAMP(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (area_id),
  UNIQUE KEY uq_area_latest_upload (upload_id),
  CONSTRAINT fk_al_area
    FOREIGN KEY (area_id) REFERENCES areas(id)
    ON DELETE CASCADE
    ON UPDATE RESTRICT,
  CONSTRAINT fk_al_upload
    FOREIGN KEY (upload_id) REFERENCES pc_uploaded_history(id)
    ON DELETE CASCADE
    ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO area_latest (area_id, upload_id) VALUES (1, 1);