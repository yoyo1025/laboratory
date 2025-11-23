// k6/minio_upload.js
import http from 'k6/http';
import { check } from 'k6';

// ■ 負荷シナリオ設定
export const options = {
  scenarios: {
    pointcloud_upload: {
      executor: 'constant-arrival-rate',
      rate: 150,          // 1秒あたり80リクエスト
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 10000,
      maxVUs: 10000,
      exec: 'uploadScenario',
    },
  },
};

// ■ MinIO の設定
const BASE_URL = 'http://localhost:7000';   // mc alias minio-benchmark の URL
const BUCKET_NAME = 'minio-benchmark';      // バケット名
const OBJECT_PREFIX = 'tmp';                // 「フォルダ」相当

// ■ アップロードするファイルを読み込み（k6 スクリプトと同じディレクトリ or 相対パス）
const payload = open('./sample.ply', 'b');  // 'b' = バイナリ

export function uploadScenario() {
  // 一意なオブジェクトキーを作る（上書き防止）
  const now = Date.now();
  const objectKey = `${OBJECT_PREFIX}/${now}-${__VU}-${__ITER}.ply`;

  // S3 互換のパス: http://host:port/bucket/key
  const url = `${BASE_URL}/${BUCKET_NAME}/${objectKey}`;

  const res = http.put(url, payload, {
    headers: {
      'Content-Type': 'application/octet-stream',
    },
    timeout: '60s',
  });

  check(res, {
    'status is 200 or 204': (r) => r.status === 200 || r.status === 204,
  });
}
