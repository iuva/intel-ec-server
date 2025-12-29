import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { BASE_URL, DEFAULT_OPTIONS } from '../utils/common.js';

export let options = DEFAULT_OPTIONS;

export default function () {
    const hostId = String(__VU); // 使用 VU ID 作为 Host ID
    
    // WebSocket 连接 URL
    // 方式1（通过网关）: 使用 ?host_id=xxx（网关已验证 token）
    // 方式2（直接连接）: 使用 ?token=xxx 或请求头 Authorization: Bearer xxx
    // 注意: BASE_URL 指向网关时使用方式1，指向 host-service 时使用方式2
    const wsUrl = BASE_URL.replace('http', 'ws') + `/api/v1/host/ws/host?host_id=${hostId}`;

    const params = {
        tags: { my_tag: 'websocket_test' },
    };

    const res = ws.connect(wsUrl, params, function (socket) {
        socket.on('open', function open() {
            // 每秒发送一次状态更新
            socket.setInterval(function timeout() {
                const updatedStatus = Math.random() > 0.5 ? 'busy' : 'online';
                socket.send(JSON.stringify({
                    type: 'status_update',
                    agent_id: hostId,
                    status: updatedStatus,
                    details: null
                }));
            }, 1000);
        });

        socket.on('message', function (message) {
            const msg = JSON.parse(message);
            check(msg, {
                'is type status_update_ack': (m) => m.type === 'status_update_ack',
            });
        });

        socket.on('close', () => console.log('disconnected'));

        // 保持连接 10 秒
        socket.setTimeout(function () {
            socket.close();
        }, 10000);
    });

    check(res, { 'status is 101': (r) => r && r.status === 101 });
    sleep(1);
}

export { handleSummary } from '../utils/reporter.js';
