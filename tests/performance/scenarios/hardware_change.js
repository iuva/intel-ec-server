import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, DEFAULT_OPTIONS, generateToken } from '../utils/common.js';

export let options = DEFAULT_OPTIONS;

// 模拟的大型 DMR 配置
const mockDmrConfig = {
    revision: 1,
    mainboard: {
        revision: 1,
        board: {
            board_meta_data: {
                board_name: "SHMRCDMR",
                host_name: "load-test-host",
            },
            baseboard: Array(10).fill({
                board_id: "board_xxx",
                fru_id: "fru_xxx"
            })
        },
        misc: {
            installed_os: ["Windows", "Linux"],
            bmc_version: "2.0.1",
        }
    },
    memory: Array(20).fill({ type: "DDR5", size: "32GB" }), // 模拟大量内存条
    security: {
        revision: 1,
        security: {
            Tpm: [{ tpm_enable: true }]
        }
    }
};

export default function () {
    const url = `${BASE_URL}/api/v1/agent/hardware/report`;
    const hostId = __VU;

    // 生成 Token
    const token = generateToken({ user_id: hostId, role: 'agent' });

    const payload = JSON.stringify({
        name: `Load Test Agent ${hostId}`,
        dmr_config: mockDmrConfig,
        updated_by: `agent_${hostId}`,
        tags: ["load_test"],
        type: 0
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
    };

    const res = http.post(url, payload, params);

    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 2s': (r) => r.timings.duration < 2000,
    });

    sleep(1);
}

export { handleSummary } from '../utils/reporter.js';
