import { check } from 'k6';
import encoding from 'k6/encoding';
import crypto from 'k6/crypto';

// 基础配置
export const BASE_URL = 'http://localhost:8000'; // 请根据实际环境修改

// 可配置的最大并发数 (默认 100)
const MAX_VUS = __ENV.MAX_VUS ? parseInt(__ENV.MAX_VUS) : 100;

export const DEFAULT_OPTIONS = {
    scenarios: {
        ramp_up_scenario: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: MAX_VUS }, // Setup: Ramp-up to MAX_VUS
                { duration: '1m', target: MAX_VUS },  // Run: Stay at MAX_VUS
                { duration: '30s', target: 0 },       // Teardown: Ramp-down
            ],
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<3000'], // P95 < 3s
        http_req_failed: ['rate<0.01'],    // Error rate < 1%
    },
};

// 工具函数：生成简单的 Mock JWT
// 真实场景请使用有效的 Secret 签名
export function generateToken(payload) {
    const alg = 'HS256';
    const header = JSON.stringify({ typ: 'JWT', alg: alg });

    // 自动添加过期时间 (exp) 和签发时间 (iat)，防止 Token 因缺失字段或过期被拒
    const now = Math.floor(Date.now() / 1000);
    const fullPayload = Object.assign({
        exp: now + 3600, // 1小时后过期
        iat: now,
        type: 'access',   // 添加 token 类型

        // ✅ 补全后端鉴权所需的关键字段
        sub: String(payload.user_id || payload.id || ''), // 标准 Subject 字段
        id: payload.user_id || payload.id                 // 某些中间件需要的 id 字段
    }, payload);

    const payloadStr = JSON.stringify(fullPayload);

    // Base64Url 编码
    const b64Header = encoding.b64encode(header, 'url');
    const b64Payload = encoding.b64encode(payloadStr, 'url');

    // 签名 (使用环境变量中的 Secret，或者默认开发环境 Secret)
    // ⚠️ 必须与 .env.local 中的 JWT_SECRET_KEY 一致
    const secret = __ENV.JWT_SECRET_KEY || 'q5W19H3LbGcAmjNqjvZE91I7yNYWmzvD';

    // ⚠️ 关键修正：JWT 签名必须是 Base64Url 编码，而不是 Hex
    // k6 crypto.hmac 如果输出 base64，需要手动转换为 base64url (替换 +/, 去掉 =)
    // 或者部分版本支持 'base64url', 为兼容性我们手动处理
    const signatureBase64 = crypto.hmac('sha256', secret, `${b64Header}.${b64Payload}`, 'base64');
    const signature = signatureBase64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

    return `${b64Header}.${b64Payload}.${signature}`;
}

export function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function getRandomItem(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}
