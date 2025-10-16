-- OAuth 2.0 相关表创建脚本
-- 用于初始化auth-service的OAuth2功能

-- 创建oauth_clients表
DROP TABLE IF EXISTS oauth_clients;
CREATE TABLE oauth_clients (
    -- 主键
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',

    -- 客户端基本信息
    client_id VARCHAR(255) NOT NULL UNIQUE COMMENT '客户端ID',
    client_secret_hash VARCHAR(255) NOT NULL COMMENT '客户端密钥哈希',
    client_name VARCHAR(255) NULL COMMENT '客户端名称',

    -- 客户端类型
    client_type VARCHAR(50) NOT NULL DEFAULT 'confidential' COMMENT '客户端类型 (confidential/public)',

    -- OAuth 2.0配置
    grant_types JSON NULL COMMENT '支持的授权类型',
    response_types JSON NULL COMMENT '支持的响应类型',
    redirect_uris JSON NULL COMMENT '重定向URI',
    scope VARCHAR(255) NOT NULL DEFAULT 'read write' COMMENT '授权范围',

    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否激活',

    -- 时间字段
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_oauth_clients_client_id (client_id) COMMENT '客户端ID索引',
    INDEX idx_oauth_clients_active (is_active) COMMENT '激活状态索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OAuth 2.0客户端表';

-- 创建设备表（如果不存在）
DROP TABLE IF EXISTS devices;
CREATE TABLE devices (
    -- 主键
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',

    -- 设备基本信息
    device_id VARCHAR(255) NOT NULL UNIQUE COMMENT '设备ID',
    device_secret_hash VARCHAR(255) NOT NULL COMMENT '设备密钥哈希',
    device_type VARCHAR(100) DEFAULT 'iot' COMMENT '设备类型',

    -- 权限配置
    permissions JSON DEFAULT ('["device"]') COMMENT '设备权限列表',

    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否激活',
    last_seen DATETIME NULL COMMENT '最后在线时间',

    -- 扩展信息
    metadata JSON DEFAULT ('{}') COMMENT '设备元数据',

    -- 时间字段
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_devices_device_id (device_id) COMMENT '设备ID索引',
    INDEX idx_devices_type (device_type) COMMENT '设备类型索引',
    INDEX idx_devices_active (is_active) COMMENT '激活状态索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备表';

-- 插入默认的OAuth客户端
INSERT INTO oauth_clients (
    client_id,
    client_secret_hash,
    client_name,
    client_type,
    grant_types,
    response_types,
    redirect_uris,
    scope,
    is_active
) VALUES
-- 管理后台客户端
(
    'admin_client',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeCtRnO7', -- 对应 'admin_secret'
    '管理后台客户端',
    'confidential',
    JSON_ARRAY('***REMOVED***word', 'refresh_token'),
    JSON_ARRAY('code'),
    JSON_ARRAY('http://localhost:8000/callback'),
    'admin',
    TRUE
),
-- 设备客户端
(
    'device_client',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeCtRnO7', -- 对应 'device_secret'
    '设备客户端',
    'confidential',
    JSON_ARRAY('client_credentials'),
    JSON_ARRAY('token'),
    JSON_ARRAY('http://localhost:8000/device/callback'),
    'device',
    TRUE
),
-- API客户端
(
    'api_client',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeCtRnO7', -- 对应 'api_secret'
    'API客户端',
    'confidential',
    JSON_ARRAY('client_credentials'),
    JSON_ARRAY('token'),
    JSON_ARRAY('http://localhost:8000/api/callback'),
    'read write',
    TRUE
);

-- 插入测试设备
INSERT INTO devices (
    device_id,
    device_secret_hash,
    device_type,
    permissions,
    is_active,
    metadata
) VALUES
(
    'device001',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeCtRnO7', -- 对应 'device_secret'
    'iot_sensor',
    JSON_ARRAY('device', 'read'),
    TRUE,
    JSON_OBJECT('location', 'room_101', 'model', 'sensor_v1')
),
(
    'device002',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeCtRnO7', -- 对应 'device_secret'
    'iot_actuator',
    JSON_ARRAY('device', 'write'),
    TRUE,
    JSON_OBJECT('location', 'room_102', 'model', 'actuator_v1')
);
