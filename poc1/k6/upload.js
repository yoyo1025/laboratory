import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    pointcloud_fetch: {
      executor: 'constant-arrival-rate',
      rate: 1,
      timeUnit: '5s',
      duration: '5m',
      preAllocatedVUs: 2,
      maxVUs: 5,
    },
  },
};

const TARGETS = [
  'http://localhost:8000/pointcloud/xn1vqhzy',
  'http://localhost:8000/pointcloud/duummy111',
];

export default function () {
  const target = TARGETS[Math.floor(Math.random() * TARGETS.length)];
  const res = http.get(target, { tags: { name: 'get_pointcloud' } });

  check(res, {
    'GET pointcloud succeeded or 404': (r) => [200, 404].includes(r.status),
  });

  sleep(5);
}
