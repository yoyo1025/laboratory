import http from 'k6/http';
import { check, sleep } from 'k6';

const API_BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';
const MINIO_BASE_URL = (__ENV.MINIO_BASE_URL || 'http://localhost:9000').replace(/\/$/, '');
const SAMPLE_FILE = open('./sample.ply', 'b');
const GEOHASH_TARGETS = ['xn1vqhzy', 'duummy111'];

export const options = {
  scenarios: {
    pointcloud_upload: {
      executor: 'constant-vus',
      vus: 3,
      duration: '5m',
      exec: 'uploadScenario',
    },
    pointcloud_fetch: {
      executor: 'constant-arrival-rate',
      rate: 1,
      timeUnit: '5s',
      duration: '5m',
      preAllocatedVUs: 2,
      maxVUs: 6,
      exec: 'fetchScenario',
    },
  },
};

export function uploadScenario() {
  const userId = ((__VU - 1) % 3) + 1;

  const preparePayload = JSON.stringify({
    user_id: userId,
    lat: 34.70011159734301,
    lon: 137.73557007483018,
    geohash_level: 8,
  });

  const prepareRes = http.post(`${API_BASE_URL}/upload/prepare`, preparePayload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'prepare_upload' },
  });

  const prepareOk = check(prepareRes, {
    'upload prepare succeeded': (r) => r.status === 200,
  });

  if (!prepareOk) {
    sleep(15);
    return;
  }

  let responseJson;
  try {
    responseJson = prepareRes.json();
  } catch (err) {
    sleep(15);
    return;
  }

  const bucket = responseJson.bucket;
  const objectKey = responseJson.object_key;

  if (typeof bucket !== 'string' || typeof objectKey !== 'string') {
    sleep(15);
    return;
  }

  const encodedPath = objectKey
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');

  const putUrl = `${MINIO_BASE_URL}/${encodeURIComponent(bucket)}/${encodedPath}`;

  const putRes = http.put(putUrl, SAMPLE_FILE, {
    headers: { 'Content-Type': 'application/octet-stream' },
    tags: { name: 'upload_pointcloud' },
  });

  check(putRes, {
    'point cloud upload succeeded': (r) => r.status >= 200 && r.status < 300,
  });

  sleep(15);
}

export function fetchScenario() {
  const geohash = GEOHASH_TARGETS[Math.floor(Math.random() * GEOHASH_TARGETS.length)];
  const res = http.get(`${API_BASE_URL}/pointcloud/${geohash}`, {
    tags: { name: 'get_pointcloud' },
  });

  check(res, {
    'GET pointcloud succeeded or 404': (r) => [200, 404].includes(r.status),
  });

  sleep(5);
}