// tests/performance/http/k6_vnc_connect.js
// 获取 VNC 连接信息接口压测脚本
// 性能指标：500并发，响应时间<2秒

import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const HOST_ID = __ENV.K6_HOST_ID || '1846486359367955051';
const URL = `${HOST}/api/v1/host/vnc/connect`;

export const options = {
  // 阶段式压测：逐步增加到500并发
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
  const payload = JSON.stringify({ id: HOST_ID });
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'vnc_connect' },
    timeout: '30s',  // HTTP 请求超时时间
  };

  const res = http.post(URL, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
    'response has vnc info': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data && body.data.ip && body.data.port;
      } catch {
        return false;
      }
    },
  });

  sleep(Math.random() * 2 + 1);
}
