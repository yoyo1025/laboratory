-- 1) PointCloud / PostGIS 拡張を先に作成
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pointcloud;
CREATE EXTENSION IF NOT EXISTS pointcloud_postgis;

-- 2) PCID=1 のスキーマを登録
-- 古い行を削除
DELETE FROM pointcloud_formats WHERE pcid = 1;

-- 正しいスキーマ（position 0-2, size 8 byte, double）
INSERT INTO pointcloud_formats (pcid, srid, schema)
VALUES (
  1, 4326,
  '<pc:PointCloudSchema xmlns:pc="http://pointcloud.org/schemas/PC">
    <pc:dimension><pc:position>0</pc:position><pc:size>8</pc:size><pc:name>X</pc:name><pc:interpretation>double</pc:interpretation></pc:dimension>
    <pc:dimension><pc:position>1</pc:position><pc:size>8</pc:size><pc:name>Y</pc:name><pc:interpretation>double</pc:interpretation></pc:dimension>
    <pc:dimension><pc:position>2</pc:position><pc:size>8</pc:size><pc:name>Z</pc:name><pc:interpretation>double</pc:interpretation></pc:dimension>
  </pc:PointCloudSchema>'
);

CREATE TABLE IF NOT EXISTS pc_data (
  ts        timestamptz NOT NULL,
  geohash8  char(8)     NOT NULL,
  patch     pcpatch,
  point_cnt int,
  PRIMARY KEY (ts, geohash8)
) PARTITION BY RANGE (ts);

-- 2025-07 のパーティション例
CREATE TABLE IF NOT EXISTS pc_data_2025_07
  PARTITION OF pc_data
  FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

