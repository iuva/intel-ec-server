// tests/performance/http/k6_agent_testcase_report.js
// Agent 上报测试用例结果接口压测脚本
// 性能指标：500并发，响应时间<2秒（需要认证）

import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const TOKEN = __ENV.K6_AGENT_TOKEN || '';
const URL = `${HOST}/api/v1/host/agent/testcase/report`;

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
  const states = [0, 1, 2, 3]; // 0-空闲 1-启动 2-成功 3-失败
  const state = states[Math.floor(Math.random() * states.length)];
  
  const payload = JSON.stringify({
    tc_id: `test_case_${__VU}_${__ITER}`,
    state: state,
    result_msg: state === 2 ? 'Test ***REMOVED***ed' : state === 3 ? 'Test failed' : 'Test running',
    log_url: state === 2 || state === 3 ? `http://logs.example.com/test_${__VU}_${__ITER}.log` : null,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN}`,
    },
    tags: { endpoint: 'agent_testcase_report' },
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

