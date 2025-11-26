import http from 'k6/http';
import exec from 'k6/execution';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const TOKEN = __ENV.K6_ADMIN_TOKEN || '';

export const options = {
  scenarios: {
    browser_api: {
      executor: 'ramping-arrival-rate',
      startRate: 20,
      timeUnit: '1s',
      stages: [
        { target: 100, duration: '1m' },
        { target: 200, duration: '2m' },
        { target: 50, duration: '30s' },
      ],
      exec: 'browserApi',
    },
    admin_api: {
      executor: 'constant-arrival-rate',
      rate: 30,
      timeUnit: '1s',
      duration: '3m',
      preAllocatedVUs: 20,
      exec: 'adminApi',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
  },
};

export function browserApi() {
  const url = `${HOST}/api/v1/host/hosts/available`;
  const payload = JSON.stringify({
    tc_id: `case-${exec.instance.iterationInTest}`,
    cycle_name: 'cycle-mixed',
    user_name: 'stress_user',
    page_size: 20,
  });
  const res = http.post(url, payload, { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}

export function adminApi() {
  const url = `${HOST}/api/v1/host/admin/host/list?page=1&page_size=20`;
  const headers = { 'Content-Type': 'application/json' };
  if (TOKEN) {
    headers.Authorization = `Bearer ${TOKEN}`;
  }
  const res = http.get(url, { headers });
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
