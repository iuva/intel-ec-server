import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, DEFAULT_OPTIONS } from '../utils/common.js';

export let options = DEFAULT_OPTIONS;

export default function () {
    const url = `${BASE_URL}/api/v1/host/hosts/available`;

    // 模拟不同用户的请求
    const userId = __VU; // Virtual User ID
    const payload = JSON.stringify({
        tc_id: `perf_test_${userId}`,
        cycle_name: "perf_cycle",
        user_name: `load_tester_${userId}`,
        page_size: 20,
        email: `test_user_${userId}@example.com` // 使用 email 绕过数据库查询，提高压测纯度
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const res = http.post(url, payload, params);

    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 2s': (r) => r.timings.duration < 2000,
        'has data': (r) => r.json('data.hosts') !== undefined,
    });

    // 思考时间 1s
    sleep(1);
}

export { handleSummary } from '../utils/reporter.js';
