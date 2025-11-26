import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const URL = `${HOST}/api/v1/host/vnc/connect`;
const HOST_ID = __ENV.K6_HOST_ID || '1846486359367955051';

export const options = {
  vus: 50,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<400'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const payload = JSON.stringify({ id: HOST_ID });
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.post(URL, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
