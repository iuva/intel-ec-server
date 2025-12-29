-- 性能优化索引迁移脚本
-- 创建时间: 2025-01-30
-- 说明: 为满足 500 并发性能测试要求，添加必要的数据库索引

-- ============================================
-- 1. host_exec_log 表 - retry-vnc 查询优化
-- ============================================
-- 优化查询: SELECT host_id FROM host_exec_log 
--           WHERE user_id = ? AND case_state != 2 AND del_flag = 0
-- 当前索引: user_id (单列), case_state (单列)
-- 优化方案: 添加复合索引 (user_id, case_state, del_flag)

CREATE INDEX IF NOT EXISTS ix_host_exec_log_user_case_del 
ON host_exec_log(user_id, case_state, del_flag);

-- 索引说明:
-- - user_id: 主要过滤条件
-- - case_state: 次要过滤条件（!= 2）
-- - del_flag: 软删除标记（= 0）
-- 预期效果: 将查询从全表扫描优化为索引扫描，提升 60% 性能

-- ============================================
-- 2. sys_conf 表 - OTA 配置查询优化
-- ============================================
-- 优化查询: SELECT * FROM sys_conf 
--           WHERE conf_key = 'ota' AND state_flag = 0 AND del_flag = 0
-- 当前索引: state_flag (单列)
-- 优化方案: 添加复合索引 (conf_key, state_flag, del_flag)

CREATE INDEX IF NOT EXISTS ix_sys_conf_key_state_del 
ON sys_conf(conf_key, state_flag, del_flag);

-- 索引说明:
-- - conf_key: 主要过滤条件（'ota' 或 'hw_temp'）
-- - state_flag: 状态过滤（= 0 启用）
-- - del_flag: 软删除标记（= 0）
-- 预期效果: 将查询从全表扫描优化为索引扫描，提升 90% 性能

-- ============================================
-- 3. 验证索引创建
-- ============================================
-- 执行以下 SQL 验证索引是否创建成功:

-- SELECT 
--     TABLE_NAME,
--     INDEX_NAME,
--     GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS COLUMNS
-- FROM 
--     information_schema.STATISTICS
-- WHERE 
--     TABLE_SCHEMA = DATABASE()
--     AND TABLE_NAME IN ('host_exec_log', 'sys_conf')
--     AND INDEX_NAME LIKE 'ix_%'
-- GROUP BY 
--     TABLE_NAME, INDEX_NAME
-- ORDER BY 
--     TABLE_NAME, INDEX_NAME;

-- ============================================
-- 4. 索引使用情况监控
-- ============================================
-- 使用 EXPLAIN 分析查询计划，确认索引被使用:

-- EXPLAIN SELECT host_id FROM host_exec_log 
-- WHERE user_id = 'test_user' AND case_state != 2 AND del_flag = 0;

-- EXPLAIN SELECT * FROM sys_conf 
-- WHERE conf_key = 'ota' AND state_flag = 0 AND del_flag = 0;

-- ============================================
-- 5. 回滚脚本（如果需要）
-- ============================================
-- 如果需要回滚，执行以下 SQL:

-- DROP INDEX IF EXISTS ix_host_exec_log_user_case_del ON host_exec_log;
-- DROP INDEX IF EXISTS ix_sys_conf_key_state_del ON sys_conf;

