-- ==========================================
-- 业务场景测试数据 SQL
-- ==========================================
-- 用途：创建用于演示和测试业务流程的数据，包括用户、主机、执行日志等。
-- 说明：
--   - 确保在导入此数据前已初始化基本 Schema
--   - ID 使用固定的大整数以确保可重复性
-- ==========================================

-- ==========================================
-- 0. 辅助函数与设置
-- ==========================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ==========================================
-- 1. 认证服务数据 (Auth Service)
-- ==========================================
-- 表：sys_user

-- 1.1 管理员用户 (admin)
-- 密码通常是加密的，这里假设使用 bcrypt 或类似哈希 (示例: $2b$12$...)
-- 为方便测试，这里使用占位符，实际使用时需替换为真实哈希
INSERT INTO `sys_user` (
    `id`, `user_name`, `user_account`, `user_pwd`, 
    `user_avatar`, `email`, `state_flag`, `created_by`, `created_time`, `del_flag`
) VALUES (
    10001, '系统管理员', 'admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWrn96pzvP/z.X.X.X.X.X', 
    'https://example.com/avatar/admin.png', 'admin@example.com', 0, 0, NOW(), 0
) ON DUPLICATE KEY UPDATE `user_name` = VALUES(`user_name`);

-- 1.2 操作员用户 (operator)
INSERT INTO `sys_user` (
    `id`, `user_name`, `user_account`, `user_pwd`, 
    `user_avatar`, `email`, `state_flag`, `created_by`, `created_time`, `del_flag`
) VALUES (
    10002, '运维操作员', 'operator', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWrn96pzvP/z.X.X.X.X.X', 
    'https://example.com/avatar/op.png', 'operator@example.com', 0, 10001, NOW(), 0
) ON DUPLICATE KEY UPDATE `user_name` = VALUES(`user_name`);

-- 1.3 只读用户 (viewer)
INSERT INTO `sys_user` (
    `id`, `user_name`, `user_account`, `user_pwd`, 
    `user_avatar`, `email`, `state_flag`, `created_by`, `created_time`, `del_flag`
) VALUES (
    10003, '访客用户', 'viewer', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWrn96pzvP/z.X.X.X.X.X', 
    NULL, 'viewer@example.com', 0, 10001, NOW(), 0
) ON DUPLICATE KEY UPDATE `user_name` = VALUES(`user_name`);


-- ==========================================
-- 2. 主机服务数据 (Host Service)
-- ==========================================
-- 表：host_rec

-- 2.1 在线空闲主机 (Free)
INSERT INTO `host_rec` (
    `id`, `host_no`, `mg_id`, `host_ip`, `host_port`, 
    `host_acct`, `host_pwd`, `mac_addr`, `appr_state`, 
    `host_state`, `tcp_state`, `agent_ver`, `created_by`, `created_time`, `del_flag`
) VALUES (
    20001, 'HOST-001-FREE', 'MG-UUID-0001', '192.168.10.101', 22, 
    'root', 'encrypted_pwd', 'AA:BB:CC:DD:EE:01', 1, 
    0, 2, 'v1.0.0', 10001, NOW(), 0
) ON DUPLICATE KEY UPDATE `host_ip` = VALUES(`host_ip`);

-- 2.2 占用中主机 (Occupied/Running)
INSERT INTO `host_rec` (
    `id`, `host_no`, `mg_id`, `host_ip`, `host_port`, 
    `host_acct`, `host_pwd`, `mac_addr`, `appr_state`, 
    `host_state`, `tcp_state`, `agent_ver`, `created_by`, `created_time`, `del_flag`
) VALUES (
    20002, 'HOST-002-BUSY', 'MG-UUID-0002', '192.168.10.102', 22, 
    'root', 'encrypted_pwd', 'AA:BB:CC:DD:EE:02', 1, 
    3, 2, 'v1.0.0', 10001, NOW(), 0
) ON DUPLICATE KEY UPDATE `host_ip` = VALUES(`host_ip`);

-- 2.3 离线主机 (Offline)
INSERT INTO `host_rec` (
    `id`, `host_no`, `mg_id`, `host_ip`, `host_port`, 
    `host_acct`, `host_pwd`, `mac_addr`, `appr_state`, 
    `host_state`, `tcp_state`, `agent_ver`, `created_by`, `created_time`, `del_flag`
) VALUES (
    20003, 'HOST-003-OFFLINE', 'MG-UUID-0003', '192.168.10.103', 22, 
    'root', 'encrypted_pwd', 'AA:BB:CC:DD:EE:03', 1, 
    4, 0, 'v0.9.9', 10001, NOW(), 0
) ON DUPLICATE KEY UPDATE `host_ip` = VALUES(`host_ip`);

-- 2.4 待审批/新接入主机 (New/Pending)
INSERT INTO `host_rec` (
    `id`, `host_no`, `mg_id`, `host_ip`, `host_port`, 
    `host_acct`, `host_pwd`, `mac_addr`, `appr_state`, 
    `host_state`, `tcp_state`, `agent_ver`, `created_by`, `created_time`, `del_flag`
) VALUES (
    20004, 'HOST-004-NEW', 'MG-UUID-0004', '192.168.10.104', 22, 
    'root', 'encrypted_pwd', 'AA:BB:CC:DD:EE:04', 2, 
    5, 2, 'v1.0.0', 10001, NOW(), 0
) ON DUPLICATE KEY UPDATE `host_ip` = VALUES(`host_ip`);


-- ==========================================
-- 3. 执行日志数据 (Host Exec Log)
-- ==========================================
-- 表：host_exec_log

-- 3.1 成功执行记录 (Success) - 关联 BUSY 主机
INSERT INTO `host_exec_log` (
    `id`, `host_id`, `user_id`, `tc_id`, `cycle_name`, `user_name`, 
    `err_msg`, `begin_time`, `end_time`, `host_state`, `case_state`, 
    `result_msg`, `log_url`, `created_by`, `updated_by`, `created_time`, `del_flag`
) VALUES (
    30001, 20002, 'operator', 'TC-LOGIN-001', 'Daily-Check-20250101', '运维操作员',
    NULL, DATE_SUB(NOW(), INTERVAL 1 HOUR), DATE_SUB(NOW(), INTERVAL 30 MINUTE), 2, 2,
    'Login successful', 'http://logs.example.com/30001.log', 10002, 10002, NOW(), 0
);

-- 3.2 正在执行记录 (Running) - 关联 BUSY 主机
INSERT INTO `host_exec_log` (
    `id`, `host_id`, `user_id`, `tc_id`, `cycle_name`, `user_name`, 
    `err_msg`, `begin_time`, `end_time`, `host_state`, `case_state`, 
    `result_msg`, `log_url`, `created_by`, `updated_by`, `created_time`, `del_flag`
) VALUES (
    30002, 20002, 'admin', 'TC-PERF-001', 'Perf-Test-Q1', '系统管理员',
    NULL, NOW(), NULL, 3, 1,
    NULL, 'http://logs.example.com/live/30002.log', 10001, 10001, NOW(), 0
);

-- 3.3 失败执行记录 (Failed - Timeout) - 关联 FREE 主机 (历史记录)
INSERT INTO `host_exec_log` (
    `id`, `host_id`, `user_id`, `tc_id`, `cycle_name`, `user_name`, 
    `err_msg`, `begin_time`, `end_time`, `host_state`, `case_state`, 
    `result_msg`, `log_url`, `created_by`, `updated_by`, `created_time`, `del_flag`
) VALUES (
    30003, 20001, 'viewer', 'TC-VIEW-001', 'Smoke-Test', '访客用户',
    '{"code": 504, "message": "Connection Timeout"}', DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 23 HOUR), 0, 3,
    'Execution Timed Out', 'http://logs.example.com/30003.log', 10003, 10003, NOW(), 0
);

-- 3.4 失败执行记录 (Failed - Error) - 关联 OFFLINE 主机
INSERT INTO `host_exec_log` (
    `id`, `host_id`, `user_id`, `tc_id`, `cycle_name`, `user_name`, 
    `err_msg`, `begin_time`, `end_time`, `host_state`, `case_state`, 
    `result_msg`, `log_url`, `created_by`, `updated_by`, `created_time`, `del_flag`
) VALUES (
    30004, 20003, 'admin', 'TC-REBOOT-001', 'Maintenance', '系统管理员',
    '{"code": 500, "message": "Host Unreachable"}', DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), 4, 3,
    'Host Offline', NULL, 10001, 10001, NOW(), 0
);

SET FOREIGN_KEY_CHECKS = 1;

-- ==========================================
-- 结束
-- ==========================================
