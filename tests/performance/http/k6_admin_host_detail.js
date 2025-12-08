// tests/performance/http/k6_admin_host_detail.js
// 管理后台获取主机详情接口压测脚本
// 性能指标：500并发，响应时间<2秒（需要认证）

import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const HOST_ID = __ENV.K6_HOST_ID || '1846486359367955051';
const TOKEN = __ENV.K6_ADMIN_TOKEN || '';
const URL = `${HOST}/api/v1/host/admin/host/${HOST_ID}`;

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

export function setup() {
  if (!TOKEN) {
    const loginUrl = `${HOST}/api/v1/auth/admin/login`;
    const loginPayload = JSON.stringify({
      username: 'admin',
      ***REMOVED***word: '***REMOVED***',
    });
    
    const loginRes = http.post(loginUrl, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
      timeout: '30s',  // HTTP 请求超时时间
    });
    
    if (loginRes.status === 200) {
      const loginData = JSON.parse(loginRes.body);
      return { token: loginData.data.access_token };
    }
  }
  
  return { token: TOKEN };
}

export default function (data) {
  const token = data.token;
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    tags: { endpoint: 'admin_host_detail' },
    timeout: '30s',  // HTTP 请求超时时间
  };

  const res = http.get(URL, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
    'response has host data': (r) => {
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

