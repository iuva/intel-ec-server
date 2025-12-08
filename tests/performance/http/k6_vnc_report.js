// tests/performance/http/k6_vnc_report.js
// 上报 VNC 连接结果接口压测脚本
// 性能指标：500并发，响应时间<2秒

import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const HOST_ID = __ENV.K6_HOST_ID || '1846486359367955051';
const URL = `${HOST}/api/v1/host/vnc/report`;

export const options = {
  stages: [
    { duration: '1m', target: 100 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 250 },
    { duration: '2m', target: 250 },
    { duration: '1m', target: 500 },
    { duration: '5m', target: 500 },
    { duration: '1m', target: 0 },
  ],
  
  thresholds: {
    http_req_duration: [
      'p(50)<500',
      'p(95)<1500',
      'p(99)<2000',
      'max<3000',
    ],
    http_req_failed: ['rate<0.01'],
    http_reqs: ['rate>100'],
  },
};

export default function () {
  const connectionStatus = Math.random() > 0.5 ? 'success' : 'failed';
  const payload = JSON.stringify({
    user_id: `user_${__VU}`,
    tc_id: `test_case_${__VU}_${__ITER}`,
    cycle_name: 'test_cycle_001',
    user_name: `test_user_${__VU}`,
    host_id: HOST_ID,
    connection_status: connectionStatus,
    connection_time: new Date().toISOString(),
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'vnc_report' },
    timeout: '30s',  // HTTP 请求超时时间
  };

  const res = http.post(URL, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
    'response has result': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data && body.data.host_id;
      } catch {
        return false;
      }
    },
  });

  sleep(Math.random() * 2 + 1);
}

