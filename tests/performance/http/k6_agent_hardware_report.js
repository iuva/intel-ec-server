// tests/performance/http/k6_agent_hardware_report.js
// Agent 上报硬件信息接口压测脚本
// 性能指标：500并发，响应时间<2秒（需要认证）

import http from 'k6/http';
import { check, sleep } from 'k6';

const HOST = __ENV.K6_HOST_URL || 'http://localhost:8003';
const TOKEN = __ENV.K6_AGENT_TOKEN || '';
const URL = `${HOST}/api/v1/host/agent/hardware/report`;

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
  const payload = JSON.stringify({
    name: `Agent Config ${__VU}_${__ITER}`,
    dmr_config: {
      revision: 1,
      mainboard: {
        revision: 1,
        plt_meta_data: {
          platform: 'DMR',
          label_plt_cfg: 'auto_generated',
        },
        board: {
          board_meta_data: {
            board_name: 'SHMRCDMR',
            host_name: `host-${__VU}`,
            host_ip: `10.239.168.${100 + __VU % 155}`,
          },
          baseboard: [
            {
              board_id: `board_${__VU}`,
              rework_version: '1.0',
              board_ip: `10.239.168.${100 + __VU % 155}`,
              bmc_ip: `10.239.168.${170 + __VU % 85}`,
              fru_id: `fru_${__VU}`,
            },
          ],
          lsio: {
            usb_disc_installed: true,
            network_installed: true,
            nvme_installed: false,
            keyboard_installed: true,
            mouse_installed: false,
          },
          peripheral: {
            itp_installed: true,
            usb_dbc_installed: false,
            controlbox_installed: true,
            flash_programmer_installed: true,
            display_installed: true,
            jumpers: [],
          },
        },
        misc: {
          installed_os: ['Windows', 'Linux'],
          bmc_version: '2.0.1',
          bmc_ip: `10.239.168.${170 + __VU % 85}`,
          cpld_version: '2.1.0',
        },
      },
      hsio: [],
      memory: [],
      security: {
        revision: 1,
        security: {
          Tpm: [
            {
              tpm_enable: true,
              tpm_algorithm: 'SHA256',
              tmp_family: '2.0',
              tpm_interface: 'TIS',
            },
          ],
          CoinBattery: [],
        },
      },
      soc: [],
    },
    updated_by: `agent_${__VU}@intel.com`,
    tags: ['alive', 'checked'],
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN}`,
    },
    tags: { endpoint: 'agent_hardware_report' },
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

