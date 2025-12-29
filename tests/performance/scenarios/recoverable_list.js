import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, DEFAULT_OPTIONS } from '../utils/common.js';

export let options = DEFAULT_OPTIONS;

export default function () {
    const url = `${BASE_URL}/api/v1/host/hosts/retry-vnc`;

    // 模拟不同用户的请求
    const payload = JSON.stringify({
        user_id: `user_${__VU}`
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
        'has hosts list': (r) => r.json('data.hosts') !== undefined,
    });

    sleep(1);
}

export { handleSummary } from '../utils/reporter.js';
