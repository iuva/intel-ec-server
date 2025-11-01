-- Case 超时检测定时任务配置初始化 SQL
-- 执行此 SQL 来初始化 case_timeout 配置

-- 插入 case_timeout 配置（如果不存在则插入，存在则更新）
INSERT INTO sys_conf (conf_key, conf_val, conf_name, state_flag, del_flag, created_time, updated_time)
VALUES ('case_timeout', '30', 'Case超时时间(分钟)', 0, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    conf_val = '30',
    conf_name = 'Case超时时间(分钟)',
    state_flag = 0,
    del_flag = 0,
    updated_time = NOW();

-- 验证配置是否正确
SELECT 
    id,
    conf_key,
    conf_val,
    conf_name,
    state_flag,
    del_flag,
    created_time,
    updated_time
FROM sys_conf 
WHERE conf_key = 'case_timeout' 
  AND del_flag = 0 
  AND state_flag = 0;

-- 配置说明：
-- - conf_key: 必须为 'case_timeout'
-- - conf_val: 超时时间（分钟），字符串类型的整数，例如 '30' 表示 30 分钟
-- - conf_name: 配置名称
-- - state_flag: 必须为 0（启用状态）
-- - del_flag: 必须为 0（未删除）

