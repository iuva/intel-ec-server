// tests/performance/http/windows/k6_load_test_windows.js
// Windows 平台 k6 压测脚本

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 自定义指标
const errorRate = new Rate('errors');
const customTrend = new Trend('custom_response_time');

// Windows 环境变量读取
const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const TOKEN = __ENV.K6_ADMIN_TOKEN || '';

export const options = {
  // Windows 系统建议降低并发数（文件描述符限制）
  stages: [
    { duration: '2m', target: 30 },    // 逐步增加到30并发
    { duration: '5m', target: 30 },    // 保持30并发5分钟
    { duration: '2m', target: 50 },    // 增加到50并发
    { duration: '5m', target: 50 },    // 保持50并发5分钟
    { duration: '2m', target: 0 },     // 降为0
  ],
  
  thresholds: {
    http_req_duration: [
      'p(50)<200',   // 50% 请求 < 200ms
      'p(95)<500',   // 95% 请求 < 500ms
      'p(99)<1000',  // 99% 请求 < 1000ms
    ],
    http_req_failed: ['rate<0.01'],    // 错误率 < 1%
    http_reqs: ['rate>50'],            // 请求速率 > 50 req/s
    errors: ['rate<0.01'],             // 自定义错误率 < 1%
  },
  
  tags: {
    test_type: 'load_test',
    service: 'host-service',
    platform: 'windows',
    environment: __ENV.K6_ENV || 'local',
  },
};

export function setup() {
  // 压测前准备：获取token、准备数据等
  const loginUrl = `${HOST}/api/v1/auth/admin/login`;
  const loginPayload = JSON.stringify({
    username: 'admin',
    password: 'admin123',
  });
  
  const loginRes = http.post(loginUrl, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: '30s',  // HTTP 请求超时时间
  });
  
  if (loginRes.status === 200) {
    const loginData = JSON.parse(loginRes.body);
    return { token: loginData.data.access_token };
  }
  
  return { token: TOKEN };
}

export default function (data) {
  const token = data.token;
  
  // 场景1：查询可用主机列表
  const queryUrl = `${HOST}/api/v1/host/hosts/available`;
  const queryPayload = JSON.stringify({
    tc_id: `test_case_${__VU}_${__ITER}`,
    cycle_name: 'test_cycle',
    user_name: 'test_user',
    page_size: 20,
  });
  
  const queryRes = http.post(queryUrl, queryPayload, {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { endpoint: 'query_available_hosts' },
    timeout: '30s',  // HTTP 请求超时时间
  });
  
  const querySuccess = check(queryRes, {
    '查询状态码200': (r) => r.status === 200,
    '查询响应时间<500ms': (r) => r.timings.duration < 500,
    '响应包含data字段': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data !== undefined;
      } catch {
        return false;
      }
    },
  });
  
  errorRate.add(!querySuccess);
  customTrend.add(queryRes.timings.duration);
  
  sleep(1);
  
  // 场景2：获取VNC连接信息（需要认证）
  if (token) {
    const vncUrl = `${HOST}/api/v1/host/vnc/connect`;
    const vncPayload = JSON.stringify({
      id: '1846486359367955051',
    });
    
    const vncRes = http.post(vncUrl, vncPayload, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      tags: { endpoint: 'get_vnc_connection' },
      timeout: '30s',  // HTTP 请求超时时间
    });
    
    check(vncRes, {
      'VNC状态码200': (r) => r.status === 200,
    });
  }
  
  sleep(1);
}

export function teardown(data) {
  // 压测后清理
  console.log('压测完成，开始清理...');
}

