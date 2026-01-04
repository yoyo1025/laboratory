import http from 'k6/http';
import { check } from 'k6';

const EDGE_TARGETS = [
  { name: 'edge1', api: 'http://localhost:8000', minio: 'http://localhost:9000' },
  { name: 'edge2', api: 'http://localhost:8001', minio: 'http://localhost:9002' },
  { name: 'edge3', api: 'http://localhost:8002', minio: 'http://localhost:9004' },
];

// 取得対象のジオハッシュ
const GEOHASH_TARGETS = ['xn1vqhzy', 'dummy111'];

// アップロードする PLY サンプル
const SAMPLE_FILE = open('./sample.ply', 'b');

// 配列からランダムに 1 要素を返す
const pickOne = (arr) => arr[Math.floor(Math.random() * arr.length)];

// check を少し読みやすく包む
const assert = (res, label, pred) => check(res, { [label]: pred });

// MinIO PUT 用 URL（バケット名とオブジェクトキー各セグメントを URL エンコード）
const buildMinioPutUrl = (minioBase, bucket, objectKey) => {
  const encodedBucket = encodeURIComponent(bucket);
  const encodedPath = objectKey
    .split('/')
    .map((seg) => encodeURIComponent(seg))
    .join('/');
  return `${minioBase}/${encodedBucket}/${encodedPath}`;
};

export const options = {
  scenarios: {
    pointcloud_upload: {
      executor: 'constant-arrival-rate',
      rate: 1,
      timeUnit: '0.05s',
      duration: '1m',
      preAllocatedVUs: 50,
      maxVUs: 2000,
      exec: 'uploadScenario',
      gracefulStop: '5s',
    },

    // pointcloud_fetch: {
    //   executor: 'constant-arrival-rate',
    //   rate: 1,
    //   timeUnit: '1s',
    //   duration: '5m',
    //   preAllocatedVUs: 2,
    //   maxVUs: 6,
    //   exec: 'fetchScenario',
    // },
  },
};

/**
 * =====================================
 * アップロードシナリオ
 * =====================================
 * フロー:
 * 1) /upload/prepare で bucket と object_key を取得
 * 2) 取得した情報で MinIO に PUT
 * 3) クールダウン sleep
 * ※ 各リクエストごとに edge1〜3 からランダム選択
 */
export function uploadScenario() {
  // ユーザーIDは VU に紐づけ（1〜3 をローテーション）
  const userId = ((__VU - 1) % 3) + 1;

  // ★ リクエストごとにランダムなエッジを選ぶ
  const edge = pickOne(EDGE_TARGETS);
  // どのエッジに投げたか見たい場合は以下を有効化
  // console.log(`[upload] target=${edge.name} api=${edge.api} minio=${edge.minio}`);

  // 1) アップロード予約（prepare）
  const preparePayload = JSON.stringify({
    user_id: userId,
    lat: 34.70011159734301,
    lon: 137.73557007483018,
    geohash_level: 8,
  });

  const prepareRes = http.post(`${edge.api}/upload/prepare`, preparePayload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'prepare_upload' },
  });

  const okPrepare = assert(prepareRes, 'upload prepare succeeded', (r) => r.status === 200);
  if (!okPrepare) {
    // sleep(15);
    return;
  }

  // レスポンス JSON（安全に取り出す）
  let info;
  try {
    info = prepareRes.json();
  } catch (_e) {
    // sleep(15);
    return;
  }

  const bucket = info?.bucket;
  const objectKey = info?.object_key;
  if (typeof bucket !== 'string' || typeof objectKey !== 'string') {
    // sleep(15);
    return;
  }

  // 2) MinIO へ PUT
  const putUrl = buildMinioPutUrl(edge.minio, bucket, objectKey);
  const putRes = http.put(putUrl, SAMPLE_FILE, {
    headers: { 'Content-Type': 'application/octet-stream' },
    tags: { name: 'upload_pointcloud' },
  });
  assert(putRes, 'point cloud upload succeeded', (r) => r.status >= 200 && r.status < 300);

  // 3) クールダウン
  // sleep(15);
}

/**
 * =====================================
 * 取得シナリオ
 * =====================================
 * フロー:
 * 1) ランダム geohash を選ぶ
 * 2) ランダム edge の API に GET
 * 3) 200 or 404 を許容（未作成 geohash の可能性あり）
 */
export function fetchScenario() {
  const geohash = pickOne(GEOHASH_TARGETS);

  // ★ リクエストごとにランダムなエッジを選ぶ
  const edge = pickOne(EDGE_TARGETS);
  // console.log(`[fetch] target=${edge.name} api=${edge.api}`);

  const res = http.get(`${edge.api}/pointcloud/${geohash}`, {
    tags: { name: 'get_pointcloud' },
  });

  assert(res, 'GET pointcloud succeeded or 404', (r) => r.status === 200 || r.status === 404);

  // sleep(5);
}
