-- ==========================================
-- 硬件变化测试数据 SQL
-- ==========================================
-- 用途：创建硬件变化和版本号变化的测试数据
-- 说明：
--   - diff_state: 1-版本号变化, 2-内容更改, 3-异常
--   - sync_state: 1-待同步（待审批）
--   - host_state: 5-待激活, 6-硬件改动, 7-手动停用
--   - appr_state: 0-停用, 2-存在改动（待审批状态）
--   - id: 使用雪花ID生成（高44位时间戳 + 低20位随机数）
-- ==========================================

-- ==========================================
-- 0. 创建雪花ID生成函数（可选，如果已存在可跳过）
-- ==========================================

DELIMITER $$

DROP FUNCTION IF EXISTS generate_snowflake_id$$

CREATE FUNCTION generate_snowflake_id() RETURNS BIGINT
READS SQL DATA
NOT DETERMINISTIC
BEGIN
    -- 雪花ID生成算法（简化版）
    -- 高44位：毫秒级时间戳
    -- 低20位：随机数（0-999999）
    -- 算法：timestamp << 20 | random_part
    -- 相当于：timestamp * 1048576 + random_part（1048576 = 2^20）
    
    DECLARE timestamp_ms BIGINT;
    DECLARE random_part INT;
    
    -- 获取毫秒级时间戳
    -- 使用 TIMESTAMPDIFF 获取从 1970-01-01 到现在的毫秒数（兼容性更好）
    SET timestamp_ms = FLOOR(TIMESTAMPDIFF(MICROSECOND, '1970-01-01 00:00:00', NOW(3)) / 1000);
    
    -- 如果 TIMESTAMPDIFF 不支持，可以使用：FLOOR(UNIX_TIMESTAMP(NOW(3)) * 1000)
    -- 但需要注意 MySQL 版本兼容性
    
    -- 生成随机数（0-999999）
    SET random_part = FLOOR(RAND() * 1000000);
    
    -- 组合：timestamp * 1048576 + random_part
    RETURN (timestamp_ms * 1048576) + random_part;
END$$

DELIMITER ;

-- ==========================================
-- 1. 创建测试主机（host_rec 表）
-- ==========================================

-- 场景1：硬件改动状态的主机（host_state = 6）
INSERT INTO host_rec (
    id, mg_id, mac_addr, host_ip, host_port, host_acct, host_pwd,
    host_state, appr_state, tcp_state, del_flag,
    created_time, updated_time
) VALUES
-- 主机1：版本号变化场景
(generate_snowflake_id(), 'MG001', '00:11:22:33:44:55', '192.168.1.101', 22, 'admin', '***REMOVED***',
 6, 2, 2, 0,
 NOW(), NOW()),
-- 主机2：内容更改场景
(generate_snowflake_id(), 'MG002', '00:11:22:33:44:56', '192.168.1.102', 22, 'admin', '***REMOVED***',
 6, 2, 2, 0,
 NOW(), NOW()),
-- 主机3：异常场景
(generate_snowflake_id(), 'MG003', '00:11:22:33:44:57', '192.168.1.103', 22, 'admin', '***REMOVED***',
 6, 2, 2, 0,
 NOW(), NOW()),
-- 主机4：待激活状态（host_state = 5）
(generate_snowflake_id(), 'MG004', '00:11:22:33:44:58', '192.168.1.104', 22, 'admin', '***REMOVED***',
 5, 0, 0, 0,
 NOW(), NOW()),
-- 主机5：手动停用状态（host_state = 7）
(generate_snowflake_id(), 'MG005', '00:11:22:33:44:59', '192.168.1.105', 22, 'admin', '***REMOVED***',
 7, 0, 0, 0,
 NOW(), NOW());

-- ==========================================
-- 2. 创建硬件变化记录（host_hw_rec 表）
-- ==========================================

-- 场景1：版本号变化（diff_state = 1）
-- 主机1：有多条硬件记录，最新一条是版本号变化
SET @host_id_mg001 = (SELECT id FROM host_rec WHERE mg_id = 'MG001' LIMIT 1);

INSERT INTO host_hw_rec (
    id, host_id, hardware_id, hw_ver, hw_info,
    diff_state, sync_state, del_flag,
    created_time, updated_time
) VALUES
-- 主机1的第一条记录（旧版本，已同步）
(generate_snowflake_id(), @host_id_mg001,
 'HW001', 'v1.0.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i7-9700K', 'cores', 8),
     'memory', JSON_OBJECT('total', '16GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'SSD', 'capacity', '512GB')
 ),
 NULL, 2, 0,  -- sync_state = 2（已通过）
 DATE_SUB(NOW(), INTERVAL 30 DAY), DATE_SUB(NOW(), INTERVAL 30 DAY)),
-- 主机1的第二条记录（版本号变化，待审批）
(generate_snowflake_id(), @host_id_mg001,
 'HW001', 'v1.1.0',  -- 版本号从 v1.0.0 变为 v1.1.0
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i7-9700K', 'cores', 8),
     'memory', JSON_OBJECT('total', '16GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'SSD', 'capacity', '512GB')
 ),
 1, 1, 0,  -- diff_state = 1（版本号变化）, sync_state = 1（待同步）
 NOW(), NOW());

-- 场景2：内容更改（diff_state = 2）
-- 主机2：有多条硬件记录，最新一条是内容更改
SET @host_id_mg002 = (SELECT id FROM host_rec WHERE mg_id = 'MG002' LIMIT 1);

INSERT INTO host_hw_rec (
    id, host_id, hardware_id, hw_ver, hw_info,
    diff_state, sync_state, del_flag,
    created_time, updated_time
) VALUES
-- 主机2的第一条记录（旧内容，已同步）
(generate_snowflake_id(), @host_id_mg002,
 'HW002', 'v2.0.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i5-8400', 'cores', 6),
     'memory', JSON_OBJECT('total', '8GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'HDD', 'capacity', '1TB')
 ),
 NULL, 2, 0,  -- sync_state = 2（已通过）
 DATE_SUB(NOW(), INTERVAL 20 DAY), DATE_SUB(NOW(), INTERVAL 20 DAY)),
-- 主机2的第二条记录（内容更改，待审批）
(generate_snowflake_id(), @host_id_mg002,
 'HW002', 'v2.0.0',  -- 版本号相同，但内容变化
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i7-10700K', 'cores', 8),  -- CPU 型号变化
     'memory', JSON_OBJECT('total', '16GB', 'type', 'DDR4'),  -- 内存容量变化
     'storage', JSON_OBJECT('type', 'SSD', 'capacity', '1TB')  -- 存储类型变化
 ),
 2, 1, 0,  -- diff_state = 2（内容更改）, sync_state = 1（待同步）
 NOW(), NOW());

-- 场景3：异常（diff_state = 3）
-- 主机3：硬件上报异常
SET @host_id_mg003 = (SELECT id FROM host_rec WHERE mg_id = 'MG003' LIMIT 1);

INSERT INTO host_hw_rec (
    id, host_id, hardware_id, hw_ver, hw_info,
    diff_state, sync_state, del_flag,
    created_time, updated_time
) VALUES
-- 主机3的第一条记录（正常，已同步）
(generate_snowflake_id(), @host_id_mg003,
 'HW003', 'v3.0.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'AMD Ryzen 7 3700X', 'cores', 8),
     'memory', JSON_OBJECT('total', '32GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'NVMe SSD', 'capacity', '1TB')
 ),
 NULL, 2, 0,  -- sync_state = 2（已通过）
 DATE_SUB(NOW(), INTERVAL 15 DAY), DATE_SUB(NOW(), INTERVAL 15 DAY)),
-- 主机3的第二条记录（异常，待审批）
(generate_snowflake_id(), @host_id_mg003,
 'HW003', 'v3.0.0',
 JSON_OBJECT(
     'error', 'Hardware detection failed',
     'cpu', NULL,
     'memory', NULL,
     'storage', NULL
 ),
 3, 1, 0,  -- diff_state = 3（异常）, sync_state = 1（待同步）
 NOW(), NOW());

-- 场景4：版本号变化（diff_state = 1）- 主机4
SET @host_id_mg004 = (SELECT id FROM host_rec WHERE mg_id = 'MG004' LIMIT 1);

INSERT INTO host_hw_rec (
    id, host_id, hardware_id, hw_ver, hw_info,
    diff_state, sync_state, del_flag,
    created_time, updated_time
) VALUES
(generate_snowflake_id(), @host_id_mg004,
 'HW004', 'v4.1.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i9-10900K', 'cores', 10),
     'memory', JSON_OBJECT('total', '64GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'NVMe SSD', 'capacity', '2TB')
 ),
 1, 1, 0,  -- diff_state = 1（版本号变化）, sync_state = 1（待同步）
 NOW(), NOW());

-- 场景5：内容更改（diff_state = 2）- 主机5
SET @host_id_mg005 = (SELECT id FROM host_rec WHERE mg_id = 'MG005' LIMIT 1);

INSERT INTO host_hw_rec (
    id, host_id, hardware_id, hw_ver, hw_info,
    diff_state, sync_state, del_flag,
    created_time, updated_time
) VALUES
(generate_snowflake_id(), @host_id_mg005,
 'HW005', 'v5.0.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'AMD Ryzen 9 5900X', 'cores', 12),
     'memory', JSON_OBJECT('total', '32GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'NVMe SSD', 'capacity', '2TB'),
     'gpu', JSON_OBJECT('model', 'NVIDIA RTX 3080', 'memory', '10GB')  -- 新增 GPU 信息
 ),
 2, 1, 0,  -- diff_state = 2（内容更改）, sync_state = 1（待同步）
 NOW(), NOW());

-- ==========================================
-- 3. 创建多个硬件记录的场景（同一主机有多条记录）
-- ==========================================

-- 主机6：有多条硬件记录，用于测试列表查询
INSERT INTO host_rec (
    id, mg_id, mac_addr, host_ip, host_port, host_acct, host_pwd,
    host_state, appr_state, tcp_state, del_flag,
    created_time, updated_time
) VALUES
(generate_snowflake_id(), 'MG006', '00:11:22:33:44:60', '192.168.1.106', 22, 'admin', '***REMOVED***',
 6, 2, 2, 0,
 NOW(), NOW());

-- 主机6的多条硬件记录
SET @host_id_mg006 = (SELECT id FROM host_rec WHERE mg_id = 'MG006' LIMIT 1);

INSERT INTO host_hw_rec (
    id, host_id, hardware_id, hw_ver, hw_info,
    diff_state, sync_state, del_flag,
    created_time, updated_time
) VALUES
-- 第一条：旧记录（已同步）
(generate_snowflake_id(), @host_id_mg006,
 'HW006', 'v6.0.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i5-10400', 'cores', 6),
     'memory', JSON_OBJECT('total', '16GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'SSD', 'capacity', '512GB')
 ),
 NULL, 2, 0,  -- sync_state = 2（已通过）
 DATE_SUB(NOW(), INTERVAL 10 DAY), DATE_SUB(NOW(), INTERVAL 10 DAY)),
-- 第二条：版本号变化（待审批）
(generate_snowflake_id(), @host_id_mg006,
 'HW006', 'v6.1.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i5-10400', 'cores', 6),
     'memory', JSON_OBJECT('total', '16GB', 'type', 'DDR4'),
     'storage', JSON_OBJECT('type', 'SSD', 'capacity', '512GB')
 ),
 1, 1, 0,  -- diff_state = 1（版本号变化）, sync_state = 1（待同步）
 DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY)),
-- 第三条：内容更改（待审批）- 最新记录
(generate_snowflake_id(), @host_id_mg006,
 'HW006', 'v6.1.0',
 JSON_OBJECT(
     'cpu', JSON_OBJECT('model', 'Intel Core i7-10700', 'cores', 8),  -- CPU 变化
     'memory', JSON_OBJECT('total', '32GB', 'type', 'DDR4'),  -- 内存变化
     'storage', JSON_OBJECT('type', 'NVMe SSD', 'capacity', '1TB')  -- 存储变化
 ),
 2, 1, 0,  -- diff_state = 2（内容更改）, sync_state = 1（待同步）
 NOW(), NOW());

-- ==========================================
-- 4. 验证查询
-- ==========================================

-- 查询待审批主机列表（应该包含 host_state > 4 且 < 8，appr_state != 1 的主机）
SELECT 
    hr.id AS host_id,
    hr.mg_id,
    hr.mac_addr,
    hr.host_state,
    hr.appr_state,
    hwr.diff_state,
    hwr.sync_state,
    hwr.hw_ver,
    hwr.created_time AS hw_created_time
FROM host_rec hr
LEFT JOIN (
    SELECT 
        host_id,
        diff_state,
        sync_state,
        hw_ver,
        created_time,
        ROW_NUMBER() OVER (PARTITION BY host_id ORDER BY created_time DESC) AS rn
    FROM host_hw_rec
    WHERE sync_state = 1 AND del_flag = 0
) hwr ON hr.id = hwr.host_id AND hwr.rn = 1
WHERE hr.host_state > 4 
  AND hr.host_state < 8
  AND hr.appr_state != 1
  AND hr.del_flag = 0
ORDER BY hr.created_time DESC;

-- 查询每个主机的最新硬件记录（sync_state = 1）
SELECT 
    hr.id AS host_id,
    hr.mg_id,
    hwr.id AS hw_rec_id,
    hwr.hw_ver,
    hwr.diff_state,
    hwr.sync_state,
    hwr.created_time
FROM host_rec hr
INNER JOIN host_hw_rec hwr ON hr.id = hwr.host_id
WHERE hwr.sync_state = 1
  AND hwr.del_flag = 0
  AND hr.del_flag = 0
ORDER BY hr.id, hwr.created_time DESC;

-- ==========================================
-- 5. 清理测试数据（可选）
-- ==========================================

-- 如果需要清理测试数据，执行以下 SQL：
-- DELETE FROM host_hw_rec WHERE hardware_id IN ('HW001', 'HW002', 'HW003', 'HW004', 'HW005', 'HW006');
-- DELETE FROM host_rec WHERE mg_id IN ('MG001', 'MG002', 'MG003', 'MG004', 'MG005', 'MG006');

-- ==========================================
-- 6. 备选方案：如果函数创建失败，使用内联表达式
-- ==========================================
-- 如果 generate_snowflake_id() 函数创建失败，可以将所有 generate_snowflake_id() 替换为：
-- (FLOOR(TIMESTAMPDIFF(MICROSECOND, '1970-01-01 00:00:00', NOW(3)) / 1000) * 1048576) + FLOOR(RAND() * 1000000)
--
-- 或者使用更简单的版本（如果 TIMESTAMPDIFF 不支持）：
-- (FLOOR(UNIX_TIMESTAMP(NOW(3)) * 1000) * 1048576) + FLOOR(RAND() * 1000000)
--
-- 示例：
-- INSERT INTO host_rec (id, mg_id, ...) VALUES
-- ((FLOOR(TIMESTAMPDIFF(MICROSECOND, '1970-01-01 00:00:00', NOW(3)) / 1000) * 1048576) + FLOOR(RAND() * 1000000),
--  'MG001', ...);

