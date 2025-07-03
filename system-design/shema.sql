-- 詳細：生点群
CREATE TABLE raw_points (
  id        bigserial PRIMARY KEY,
  ts        timestamptz NOT NULL,
  geohash8  char(8)     NOT NULL,
  x real, y real, z real,
);

-- 詳細：マージ済み
CREATE TABLE pc_data (
  ts timestamptz, geohash8 char(8), patch pcpatch,
  point_cnt int, PRIMARY KEY (ts, geohash8)
) PARTITION BY RANGE (ts);

-- 詳細：メッシュ
CREATE TABLE mesh_data (
  ts timestamptz, geohash8 char(8), mesh_ply bytea,
  face_cnt int, PRIMARY KEY (ts, geohash8)
) PARTITION BY RANGE (ts);

-- 概要モデル
CREATE TABLE summary_pc (
  ts timestamptz, geohash_pref varchar(6), patch pcpatch,
  point_cnt int, PRIMARY KEY (ts, geohash_pref)
) PARTITION BY RANGE (ts);