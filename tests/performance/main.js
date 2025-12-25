import availableList from './scenarios/available_list.js';
import recoverableList from './scenarios/recoverable_list.js';
import websocketStatus from './scenarios/websocket_status.js';
import hardwareChange from './scenarios/hardware_change.js';
import latestVersion from './scenarios/latest_version.js';
import { handleSummary } from './utils/reporter.js';

export { handleSummary };

export const options = {
    scenarios: {
        available_list: {
            executor: 'ramping-vus',
            exec: 'runAvailableList',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 100 },
                { duration: '1m', target: 100 },
                { duration: '30s', target: 0 },
            ],
            startTime: '0s',
        },
        recoverable_list: {
            executor: 'ramping-vus',
            exec: 'runRecoverableList',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 100 },
                { duration: '1m', target: 100 },
                { duration: '30s', target: 0 },
            ],
            startTime: '2m',
        },
        // WebSocket 场景通常独立运行，因为 k6 ws 模块限制
        // 这里仅作为示例包含 HTTP 场景
        hardware_change: {
            executor: 'ramping-vus',
            exec: 'runHardwareChange',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 50 },
                { duration: '1m', target: 50 },
                { duration: '30s', target: 0 },
            ],
            startTime: '4m',
        },
        latest_version: {
            executor: 'ramping-vus',
            exec: 'runLatestVersion',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 200 },
                { duration: '1m', target: 200 },
                { duration: '30s', target: 0 },
            ],
            startTime: '0s',
        },
    },
};

export function runAvailableList() { availableList(); }
export function runRecoverableList() { recoverableList(); }
export function runHardwareChange() { hardwareChange(); }
export function runLatestVersion() { latestVersion(); }
