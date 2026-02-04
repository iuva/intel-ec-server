-- ==========================================
-- 性能测试场景数据 SQL
-- ==========================================
-- 用途：为 tests/performance/scenarios 下的 k6 脚本提供必要的预置数据
-- 场景覆盖：
--   1. available_list.js: 需要大量 "Available" (host_state=0) 的主机
--   2. hardware_change.js: 需要 ID 对应 k6 VU (1-N) 的主机记录，用于 Token 验证和硬件上报
--   3. latest_version.js: 需要 sys_conf 中存在 OTA 配置
--   4. recoverable_list.js: 需要 "Offline" (host_state=4) 且可恢复的主机
--   5. websocket_status.js: 需要 ID 对应 k6 VU (1-N) 的主机记录用于 WebSocket 连接
-- ==========================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ==========================================
-- 1. OTA 配置数据 (支持 latest_version.js)
-- ==========================================
-- 确保 sys_conf 中存在 key='ota' 的记录
INSERT INTO `sys_conf` (
    `id`, `conf_key`, `conf_val`, `conf_ver`, `conf_name`, `conf_json`, 
    `state_flag`, `created_by`, `created_time`, `del_flag`
) VALUES (
    90001, 'ota', 'http://download.example.com/agent/v2.0.0.tar.gz', '2.0.0', 'Agent V2.0',
    '{"conf_url": "http://download.example.com/agent/v2.0.0.tar.gz", "conf_md5": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"}',
    0, 10001, NOW(), 0
) ON DUPLICATE KEY UPDATE `conf_ver` = VALUES(`conf_ver`);


-- ==========================================
-- 2. 批量主机数据 (支持 hardware_change.js, websocket_status.js)
-- ==========================================
-- k6 脚本使用 __VU (从1开始的虚拟用户ID) 作为 host_id
-- 我们需要生成 ID 从 1 到 200 的主机记录，覆盖常见压测并发数

DROP PROCEDURE IF EXISTS generate_perf_test_hosts;

DELIMITER $$
CREATE PROCEDURE generate_perf_test_hosts()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE max_hosts INT DEFAULT 200; -- 生成 200 台主机供压测使用
    
    WHILE i <= max_hosts DO
        INSERT INTO `host_rec` (
            `id`, `host_no`, `mg_id`, `host_ip`, `host_port`, 
            `host_acct`, `host_pwd`, `mac_addr`, `appr_state`, 
            `host_state`, `tcp_state`, `agent_ver`, `created_by`, `created_time`, `del_flag`
        ) VALUES (
            i,                                      -- ID 对应 k6 VU
            CONCAT('PERF-HOST-', LPAD(i, 4, '0')),  -- HOST-NO
            CONCAT('MG-PERF-', LPAD(i, 4, '0')),    -- MG-ID
            CONCAT('192.168.', FLOOR(i/255), '.', (i % 255)), -- IP
            22, 
            'root', 'password', 
            CONCAT('00:00:00:00:', LPAD(HEX(i), 2, '0')), -- MAC
            1, -- 已审批
            0, -- Free (默认空闲，支持 available_list)
            2, -- TCP Listen
            '1.0.0', 
            10001, NOW(), 0
        ) ON DUPLICATE KEY UPDATE `host_ip` = VALUES(`host_ip`);
        
        SET i = i + 1;
    END WHILE;
END$$
DELIMITER ;

CALL generate_perf_test_hosts();
DROP PROCEDURE IF EXISTS generate_perf_test_hosts;


-- ==========================================
-- 3. 特定状态主机 (支持 recoverable_list.js)
-- ==========================================
-- 修改部分生成的 ID (例如 150-200) 为 Offline 或其他状态
-- 这样 available_list 验证时数据量会少于总量，recoverable_list 也能查到数据

-- 设置 150-170 为 Offline (host_state=4)
UPDATE `host_rec` 
SET `host_state` = 4 
WHERE `id` BETWEEN 150 AND 170;

-- 设置 171-180 为 Occupied (host_state=2)
UPDATE `host_rec` 
SET `host_state` = 2 
WHERE `id` BETWEEN 171 AND 180;

-- 设置 181-190 为 Error/Hardware Change (host_state=6)
UPDATE `host_rec` 
SET `host_state` = 6 
WHERE `id` BETWEEN 181 AND 190;


-- ==========================================
-- 4. 辅助用户数据 (确保 created_by 引用有效)
-- ==========================================
INSERT INTO `sys_user` (
    `id`, `user_name`, `user_account`, `user_pwd`, `state_flag`, `created_time`, `del_flag`
) VALUES (
    10001, 'Perf Admin', 'perf_admin', 'placeholder', 0, NOW(), 0
) ON DUPLICATE KEY UPDATE `user_name` = VALUES(`user_name`);

SET FOREIGN_KEY_CHECKS = 1;
