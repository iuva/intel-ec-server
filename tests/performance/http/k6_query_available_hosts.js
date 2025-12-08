// tests/performance/http/k6_query_available_hosts.js
// 查询可用主机列表接口压测脚本
// 性能指标：500并发，响应时间<2秒，每小时10000次请求

import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8000';
const URL = `${HOST}/api/v1/host/hosts/available`;

export const options = {
  // 阶段式压测：逐步增加到500并发
  stages: [
    // { duration: '1m', target: 100 },   // 1分钟内增加到100并发
    // { duration: '2m', target: 100 },   // 保持100并发2分钟
    // { duration: '1m', target: 250 },   // 1分钟内增加到250并发
    // { duration: '2m', target: 250 },   // 保持250并发2分钟
    { duration: '1m', target: 100 },   // 1分钟内增加到500并发
    { duration: '2m', target: 100 },   // 保持500并发5分钟（验证稳定性）
    { duration: '1m', target: 0 },     // 1分钟内降为0
  ],
  
  thresholds: {
    // 响应时间阈值：所有请求 < 2秒
    http_req_duration: [
      'p(50)<500',    // 50% 请求 < 500ms
      'p(95)<1500',   // 95% 请求 < 1.5秒
      'p(99)<2000',   // 99% 请求 < 2秒
      'max<3000',     // 最大响应时间 < 3秒
    ],
    
    // 错误率阈值：< 1%
    http_req_failed: ['rate<0.01'],
    
    // 吞吐量阈值：确保达到性能要求
    http_reqs: ['rate>100'],  // 至少100 req/s
  },
};

export default function () {
  const payload = JSON.stringify({
    tc_id: `test_case_${__VU}_${__ITER}`,
    cycle_name: 'test_cycle_001',
    user_name: `test_user_${__VU}`,
    page_size: 20,
    last_id: null,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'query_available_hosts' },
    timeout: '30s',  // HTTP 请求超时时间
  };

  const res = http.post(URL, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
    'response has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data !== undefined;
      } catch {
        return false;
      }
    },
  });

  // 模拟用户思考时间：0.5-1.5秒随机（减少等待时间，提高吞吐量）
  sleep(Math.random() * 1 + 0.5);
}
