import { check } from 'k6';
import encoding from 'k6/encoding';
import crypto from 'k6/crypto';

// 基础配置
export const BASE_URL = 'http://localhost:8000'; // 请根据实际环境修改

// 默认负载配置
export const DEFAULT_OPTIONS = {
    scenarios: {
        ramp_up_scenario: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 500 }, // Ramp-up to 500
                { duration: '3m', target: 500 },  // Stay at 500
                { duration: '30s', target: 0 },   // Ramp-down
            ],
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<2000'], // P95 < 2s
        http_req_failed: ['rate<0.01'],    // Error rate < 1%
    },
};

// 工具函数：生成简单的 Mock JWT (无签名验证或弱验证场景)
// 真实场景请使用有效的 Secret 签名
export function generateToken(payload) {
    const alg = 'HS256';
    const header = JSON.stringify({ typ: 'JWT', alg: alg });
    const payloadStr = JSON.stringify(payload);

    // Base64Url 编码
    const b64Header = encoding.b64encode(header, 'url');
    const b64Payload = encoding.b64encode(payloadStr, 'url');

    // 签名 (Mock Secret)
    const secret = 'your-256-bit-secret';
    const signature = crypto.hmac('sha256', secret, `${b64Header}.${b64Payload}`, 'hex');

    return `${b64Header}.${b64Payload}.${signature}`;
}

export function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function getRandomItem(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}
