import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, DEFAULT_OPTIONS } from '../utils/common.js';

export let options = DEFAULT_OPTIONS;

export default function () {
    const url = `${BASE_URL}/api/v1/agent/ota/latest`;

    const res = http.get(url);

    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 2s': (r) => r.timings.duration < 2000,
        'has config list': (r) => r.json('data') !== undefined,
    });

    sleep(0.5); // 更高频
}

export { handleSummary } from '../utils/reporter.js';
