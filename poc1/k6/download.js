import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    pointcloud_fetch: {
      executor: 'constant-arrival-rate',
      rate: 1,
      timeUnit: '0.0125s',
      duration: '3m',
      preAllocatedVUs: 50,
      maxVUs: 2000,
      gracefulStop: '5s',
    },
  },
};

const TARGETS = [
  // edge1
  'http://localhost:8000/pointcloud/bbbbbbbb',
  'http://localhost:8000/pointcloud/bbbbbbbb',
  'http://localhost:8000/pointcloud/aaaaaaaa',
  // edge2
  'http://localhost:8001/pointcloud/cccccccc',
  'http://localhost:8001/pointcloud/cccccccc',
  'http://localhost:8001/pointcloud/aaaaaaaa',
  // edge3
  'http://localhost:8002/pointcloud/dddddddd',
  'http://localhost:8002/pointcloud/dddddddd',
  'http://localhost:8002/pointcloud/aaaaaaaa',
];

export default function downloadScenario() {
  const target = TARGETS[Math.floor(Math.random() * TARGETS.length)];
  const res = http.get(target, { tags: { name: 'get_pointcloud' } });

  check(res, {
    'GET pointcloud succeeded or 404': (r) => [200, 404].includes(r.status),
  });

  sleep(5);
}
