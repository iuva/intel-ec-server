
DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user(
    `id` BIGINT NOT NULL COMMENT '主键',
    `user_name` VARCHAR(32) COMMENT '用户名称',
    `user_account` VARCHAR(32) COMMENT '登录账号',
    `user_pwd` VARCHAR(128) COMMENT '登录密码',
    `user_avatar` VARCHAR(32) COMMENT '用户头像',
    `email` VARCHAR(32) COMMENT '邮箱',
    `state_flag` TINYINT DEFAULT 0 COMMENT '账号状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    PRIMARY KEY (`id`)
) COMMENT '管理后台用户;管理后台用户';

CREATE INDEX `ix_ct` ON sys_user (
    `created_time` ASC
);
CREATE INDEX `ix_del` ON sys_user (
    `del_flag` ASC
);

DROP TABLE IF EXISTS sys_menu;
CREATE TABLE sys_menu(
    `id` BIGINT NOT NULL COMMENT '主键',
    `parent_id` BIGINT COMMENT '父级主键',
    `menu_type` TINYINT NOT NULL COMMENT '菜单类型;{dir: 1, 目录. menu: 2, 菜单. button: 3, 按钮.}',
    `menu_perm` VARCHAR(255) COMMENT '菜单权限;菜单下所有接口url逗号拼接',
    `menu_compo_name` VARCHAR(32) COMMENT 'VUE自定义组件名称',
    `menu_title` VARCHAR(32) COMMENT '菜单标题 i18n code',
    `menu_name` VARCHAR(32) COMMENT '菜单名称支持i8n',
    `menu_path` VARCHAR(32) COMMENT '菜单路由地址',
    `menu_redirect` VARCHAR(32) COMMENT '转发地址',
    `menu_compo_path` VARCHAR(64) COMMENT '菜单组件路径目录及为LAYOUT',
    `menu_icon` VARCHAR(64) COMMENT '菜单图标',
    `menu_affix` VARCHAR(1) COMMENT '标签是否固定;{default: "", 默认空. true: "1", 固定. false: "0", 不固定.}',
    `keep_alive` VARCHAR(1) COMMENT 'KeepAlive缓存，默认为空;KeepAlive缓存，默认为空',
    `link_flag` TINYINT COMMENT '链接标识，默认为空;{no: 0, 不是链接类型菜单. yes: 1, 是链接类型菜单.}',
    `show_menu` TINYINT COMMENT '显示菜单，默认为空;{no: 0, 不显示. yes: 1, 显示.}',
    `hide_menu` TINYINT COMMENT '隐藏菜单，默认为空;{no: 0, 不隐藏. yes: 1, 隐藏.}',
    `hide_childrenin_menu` TINYINT COMMENT '显示子集菜单;{no: 0, 不显示. yes: 1, 显示.}',
    `current_active_menu` VARCHAR(64) COMMENT '当前活动菜单',
    `hide_breadcrumb` TINYINT COMMENT '动态添加路由，默认为空;{no: 0, 否. yes: 1, 是.}',
    `sort_num` INT COMMENT '排序编号',
    `data_flag` TINYINT COMMENT '状态标识;{not_use: 0, 停用. useing: 1, 使用中.}',
    `del_flag` TINYINT NOT NULL COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`)
) COMMENT '菜单表';

CREATE INDEX `ix_sys_menu_del` ON sys_menu (
    `del_flag` ASC
);
CREATE INDEX `ix_sys_menu_state` ON sys_menu (
    `data_flag` ASC
);
CREATE INDEX `ix_sys_menu_type` ON sys_menu (
    `menu_type` ASC
);
CREATE INDEX `ix_tx` ON sys_menu (
    `created_time` ASC
);

DROP TABLE IF EXISTS sys_menu_api;
CREATE TABLE sys_menu_api(
    `id` BIGINT NOT NULL COMMENT '主键',
    `menu_id` BIGINT COMMENT 'sys_menu 表主键',
    `context_path` VARCHAR(32) COMMENT '服务地址',
    `api_method` VARCHAR(32) COMMENT '接口方法',
    `api_path` VARCHAR(64) COMMENT '接口地址',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`)
) COMMENT '菜单 权限 api 地址';

CREATE INDEX `ix_api_del` ON sys_menu_api (
    `del_flag` ASC
);
CREATE INDEX `ix_api_menu` ON sys_menu_api (
    `menu_id` ASC
);

DROP TABLE IF EXISTS sys_role;
CREATE TABLE sys_role(
    `id` BIGINT NOT NULL COMMENT '主键',
    `role_name` VARCHAR(32) COMMENT '角色名称中文',
    `role_remarks` VARCHAR(128) COMMENT '备注说明',
    `data_state` TINYINT DEFAULT 1 COMMENT '状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}',
    `order_seq` INT COMMENT '排序',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除;{useing: 0, 使用中. del: 1, 删除.}',
    `admin_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '超级管理员标识;{business_role: 0, 业务角色. super_administrator: 1, 超级管理员. mhg_role: 2, 商户角色.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`)
) COMMENT '系统--角色表';

CREATE INDEX `ix_role_del` ON sys_role (
    `del_flag` ASC
);
CREATE INDEX `ix_role_state` ON sys_role (
    `data_state` ASC
);

DROP TABLE IF EXISTS sys_role_menu;
CREATE TABLE sys_role_menu(
    `id` BIGINT NOT NULL COMMENT '主键',
    `menu_id` BIGINT COMMENT '菜单Id',
    `role_id` BIGINT COMMENT '角色id',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除;{useing: 0, 使用中. del: 1, 删除.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`)
) COMMENT '系统--角色菜单表';

CREATE INDEX `ix_rm_del` ON sys_role_menu (
    `del_flag` ASC
);
CREATE INDEX `ix_rm_rid` ON sys_role_menu (
    `role_id` ASC
);

DROP TABLE IF EXISTS sys_role_user;
CREATE TABLE sys_role_user(
    `id` BIGINT NOT NULL COMMENT '主键',
    `user_id` BIGINT COMMENT '用户Id',
    `role_id` BIGINT COMMENT '角色id',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除;{useing: 0, 使用中. del: 1, 删除.}',
    `data_state` TINYINT NOT NULL DEFAULT 1 COMMENT '状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`)
) COMMENT '系统--用户角色表';

CREATE INDEX `ix_ru_del` ON sys_role_user (
    `del_flag` ASC
);
CREATE INDEX `ix_ru_rid` ON sys_role_user (
    `role_id` ASC
);
CREATE INDEX `ix_ru_uid` ON sys_role_user (
    `user_id` ASC
);

DROP TABLE IF EXISTS host_rec;
CREATE TABLE host_rec(
    `id` BIGINT NOT NULL COMMENT '主键',
    `host_no` VARCHAR(64) COMMENT '主机主键;对应 mongo 数据库 host 主键',
    `mg_id` VARCHAR(128) COMMENT '唯一引导id',
    `host_ip` VARCHAR(32) COMMENT 'ip 地址',
    `host_port` INT COMMENT 'ip 端口',
    `host_acct` VARCHAR(32) COMMENT '主机账号',
    `host_pwd` VARCHAR(64) COMMENT '主机密码',
    `mac_addr` VARCHAR(255) COMMENT 'mac 地址',
    `appr_state` TINYINT COMMENT '审批状态;{disable: 0, 停用. enable: 1, 启用. new: 1, 新增. change: 2, 存在改动.}',
    `host_state` TINYINT COMMENT '主机状态;{free: 0, 空闲. lock: 1, 已锁定. occ: 2, 已占用. run: 3, case执行中.offline: 4, 离线. inact: 5, 待激活. hw_chg: 6, 存在潜在的硬件改动. disable: 7, 手动停用. updating: 8, 更新中.}',
    `subm_time` DATETIME COMMENT '申报时间',
    `hw_id` BIGINT COMMENT '硬件记录表主键;host_hw_rec 表主键',
    `agent_ver` VARCHAR(10) COMMENT 'agent 版本号',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    PRIMARY KEY (`id`)
) COMMENT '主机记录;host 列表，记录硬件变动信息';

CREATE INDEX `ix_host` ON host_rec (
    `host_no` ASC
);
CREATE INDEX `ix_mg` ON host_rec (
    `mg_id` ASC
);
CREATE INDEX `ix_as` ON host_rec (
    `appr_state` ASC
);
CREATE INDEX `ix_mac` ON host_rec (
    `mac_addr` ASC
);
CREATE INDEX `ix_del` ON host_rec (
    `del_flag` ASC
);
CREATE INDEX `ix_st` ON host_rec (
    `subm_time` ASC
);

DROP TABLE IF EXISTS host_exec_log;
CREATE TABLE host_exec_log(
    `id` BIGINT NOT NULL COMMENT '主键',
    `host_id` BIGINT COMMENT '主机主键;host_rec 表主键',
    `user_id` VARCHAR(64) COMMENT '执行用户',
    `tc_id` VARCHAR(64) COMMENT '执行测试 id',
    `cycle_name` VARCHAR(128) COMMENT '周期名称',
    `user_name` VARCHAR(32) COMMENT '用户名称',
    `err_msg` JSON COMMENT '异常信息',
    `begin_time` DATETIME COMMENT '开始时间',
    `end_time` DATETIME COMMENT '结束时间',
    `host_state` TINYINT COMMENT '主机状态;{free: 0, 空闲. lock: 1, 已锁定. occ: 2, 已占用. run: 3, case执行中.offline: 4, 离线.}',
    `case_state` TINYINT DEFAULT 0 COMMENT 'case 执行状态;{free: 0, 空闲. start: 1, 启动. success: 2, 成功. failed: 3, 失败.}',
    `result_msg` VARCHAR(255) COMMENT '执行结果',
    `log_url` VARCHAR(512) COMMENT '执行日志 log 地址',
    `created_by` BIGINT COMMENT '创建人',
    `exec_rmk` VARCHAR(255) COMMENT '备注信息',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    PRIMARY KEY (`id`)
) COMMENT '主机执行日志';

CREATE INDEX `ix_host` ON host_exec_log (
    `host_id` ASC
);
CREATE INDEX `ix_hs` ON host_exec_log (
    `host_state` ASC
);
CREATE INDEX `ix_ct` ON host_exec_log (
    `created_time` ASC
);
CREATE INDEX `ix_del` ON host_exec_log (
    `del_flag` ASC
);
CREATE INDEX `ix_user` ON host_exec_log (
    `user_id` ASC
);

DROP TABLE IF EXISTS host_hw_rec;
CREATE TABLE host_hw_rec(
    `id` BIGINT NOT NULL COMMENT '主键',
    `hardware_id` VARCHAR(64) COMMENT 'mongodb 主键;mongo db 硬件 id',
    `host_id` BIGINT COMMENT '主机主键;host_rec 表主键',
    `hw_info` JSON COMMENT '硬件信息;mongo db 数据格式',
    `hw_tmp_ver` VARCHAR(32) COMMENT '硬件版本号',
    `diff_state` TINYINT COMMENT '参数状态;{ver_diff: 1, 版本号变化. item_diff: 2, 内容更改. failed: 3, 异常.}',
    `sync_state` TINYINT DEFAULT 0 COMMENT '同步状态;{empty: 0 空状态. wait: 1, 待同步. success: 2, 通过. failed: 3, 异常.}',
    `appr_time` DATETIME COMMENT '审批时间',
    `appr_by` BIGINT COMMENT '审批人',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    PRIMARY KEY (`id`)
) COMMENT '主机硬件记录;记录主机硬件变动信息';

CREATE INDEX `ix_host` ON host_hw_rec (
    `host_id` ASC
);
CREATE INDEX `ix_ct` ON host_hw_rec (
    `created_time` ASC
);
CREATE INDEX `ix_del` ON host_hw_rec (
    `del_flag` ASC
);

DROP TABLE IF EXISTS sys_conf;
CREATE TABLE sys_conf(
    `id` BIGINT NOT NULL COMMENT '主键',
    `conf_key` VARCHAR(32) COMMENT '配置 key',
    `conf_val` VARCHAR(255) COMMENT '配置值',
    `conf_ver` VARCHAR(32) COMMENT '配置版本号',
    `conf_name` VARCHAR(32) COMMENT '配置名称',
    `conf_json` JSON COMMENT '配置 json',
    `state_flag` TINYINT DEFAULT 0 COMMENT '状态;{enable_flag: 0, 启用. disable_flag: 1, 停用.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    PRIMARY KEY (`id`)
) COMMENT '系统配置表';

CREATE INDEX `ix_state` ON sys_conf (
    `state_flag` ASC
);
CREATE INDEX `ix_ct` ON sys_conf (
    `created_time` ASC
);
CREATE INDEX `ix_del` ON sys_conf (
    `del_flag` ASC
);

DROP TABLE IF EXISTS host_upd;
CREATE TABLE host_upd(
    `id` BIGINT NOT NULL COMMENT '主键',
    `host_id` BIGINT COMMENT '主机主键;host_rec 表主键',
    `app_key` VARCHAR(32) COMMENT '应用 key',
    `app_name` VARCHAR(32) COMMENT '应用名称',
    `app_ver` VARCHAR(32) COMMENT '应用版本号',
    `app_state` TINYTEXT DEFAULT 0 COMMENT '更新状态;{pre-upd: 0, 预更新. updating: 1, 更新中. success: 2, 成功. failed: 3, 失败.}',
    `created_by` BIGINT COMMENT '创建人',
    `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_by` BIGINT COMMENT '更新人',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `del_flag` TINYINT NOT NULL DEFAULT 0 COMMENT '删除标识;{useing: 0, 使用中. del: 1, 删除.}',
    PRIMARY KEY (`id`)
) COMMENT '主机升级记录';


-- 创建 user_sessions 表
CREATE TABLE IF NOT EXISTS user_sessions (
    -- 主键
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    
    -- 关联字段 - 支持多种实体类型
    entity_id INT NOT NULL COMMENT '实体ID（管理后台用户ID或设备ID）',
    entity_type VARCHAR(50) NOT NULL COMMENT '实体类型（admin_user或device）',
    
    -- 会话字段
    session_id VARCHAR(255) NOT NULL UNIQUE COMMENT '会话ID',
    access_token TEXT NOT NULL COMMENT '访问令牌',
    refresh_token TEXT NOT NULL COMMENT '刷新令牌',
    
    -- 客户端信息
    client_ip VARCHAR(45) NULL COMMENT '客户端IP',
    user_agent TEXT NULL COMMENT '用户代理',
    
    -- 过期时间
    expires_at DATETIME NOT NULL COMMENT '过期时间',
    
    -- 时间字段
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 软删除标识
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已删除',
    
    -- 索引定义
    INDEX idx_entity (entity_id, entity_type) COMMENT '实体复合索引',
    INDEX idx_session_id (session_id) COMMENT '会话ID索引',
    INDEX idx_expires_at (expires_at) COMMENT '过期时间索引',
    INDEX idx_is_deleted (is_deleted) COMMENT '删除状态索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';

-- 单独的实体类型索引（如果需要单独查询）
CREATE INDEX idx_entity_type ON user_sessions (entity_type) COMMENT '实体类型索引';
