import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, DEFAULT_OPTIONS, generateToken } from '../utils/common.js';

export let options = DEFAULT_OPTIONS;

export default function () {
    const url = `${BASE_URL}/api/v1/host/agent/ota/latest`;
    const hostId = __VU;

    // 生成 Token
    const token = generateToken({ user_id: hostId, role: 'agent' });

    const params = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
    };

    const res = http.get(url, params);

    // 添加调试日志
    if (res.status !== 200) {
        console.log(`Error Status: ${res.status}`);
        console.log(`Error Body: ${res.body}`); // 看看返回了什么
    }

    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 2s': (r) => r.timings.duration < 2000,
        'has config list': (r) => r.json('data') !== undefined,
    });

    sleep(0.5); // 更高频
}

export { handleSummary } from '../utils/reporter.js';
