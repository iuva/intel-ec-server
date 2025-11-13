# VNC 连接信息不完整问题修复指南

## 问题原因

当调用 `/api/v1/host/vnc/connect` API 时，如果数据库中的 `host_rec` 表记录缺少 `host_ip` 或 `host_port` 字段，会触发 `VNC_INFO_INCOMPLETE` 错误。

### 检查条件

代码检查逻辑（`browser_vnc_service.py` 第 291 行）：
```python
if not host_rec.host_ip or not host_rec.host_port:
    raise BusinessError("VNC 连接信息不完整，缺少 IP 地址或端口")
```

### 触发条件

以下情况会导致错误：
- `host_ip` 为 `NULL` 或空字符串 `''`
- `host_port` 为 `NULL` 或 `0`

## 快速修复步骤

### 步骤 1: 查询数据不完整的记录

```sql
-- 查询所有缺少 VNC 连接信息的记录
SELECT 
    id,
    mg_id,
    hardware_id,
    host_ip,
    host_port,
    host_acct,
    host_state,
    appr_state
FROM intel_cw.host_rec
WHERE 
    del_flag = 0
    AND appr_state = 1
    AND (
        host_ip IS NULL 
        OR host_ip = '' 
        OR host_port IS NULL 
        OR host_port = 0
    )
ORDER BY id;
```

### 步骤 2: 自动修复（推荐）

如果硬件表（`host_hw_rec`）中有 IP 信息，可以使用以下语句自动修复：

```sql
-- 从硬件表自动提取 IP 信息并修复
UPDATE intel_cw.host_rec hr
INNER JOIN intel_cw.host_hw_rec hwr ON hr.id = hwr.host_id
SET 
    hr.host_ip = JSON_UNQUOTE(JSON_EXTRACT(hwr.hw_info, '$.dmr_config.mainboard.board.board_meta_data.host_ip')),
    hr.host_port = COALESCE(NULLIF(hr.host_port, 0), 5900),  -- 默认端口 5900
    hr.updated_time = NOW()
WHERE 
    hr.del_flag = 0
    AND hr.appr_state = 1
    AND (
        hr.host_ip IS NULL 
        OR hr.host_ip = '' 
        OR hr.host_port IS NULL 
        OR hr.host_port = 0
    )
    AND hwr.del_flag = 0
    AND hwr.sync_state = 2
    AND JSON_EXTRACT(hwr.hw_info, '$.dmr_config.mainboard.board.board_meta_data.host_ip') IS NOT NULL
    AND JSON_UNQUOTE(JSON_EXTRACT(hwr.hw_info, '$.dmr_config.mainboard.board.board_meta_data.host_ip')) != '';
```

### 步骤 3: 修复缺少端口的记录

```sql
-- 为已有 IP 但缺少端口的记录设置默认端口
UPDATE intel_cw.host_rec
SET 
    host_port = 5900,  -- VNC 默认端口
    updated_time = NOW()
WHERE 
    del_flag = 0
    AND appr_state = 1
    AND (host_port IS NULL OR host_port = 0)
    AND (host_ip IS NOT NULL AND host_ip != '');
```

### 步骤 4: 验证修复结果

```sql
-- 确认没有数据不完整的记录
SELECT COUNT(*) as incomplete_count
FROM intel_cw.host_rec
WHERE 
    del_flag = 0
    AND appr_state = 1
    AND (
        host_ip IS NULL 
        OR host_ip = '' 
        OR host_port IS NULL 
        OR host_port = 0
    );
-- 如果返回 0，说明所有记录都已修复
```

## 手动修复特定记录

如果自动修复无法处理某些记录，可以手动修复：

```sql
-- 修复特定主机记录
UPDATE intel_cw.host_rec
SET 
    host_ip = '192.168.1.100',  -- ⚠️ 请替换为实际的 IP 地址
    host_port = 5900,  -- ⚠️ 请替换为实际的端口号（VNC 默认是 5900）
    updated_time = NOW()
WHERE 
    id = 123;  -- ⚠️ 请替换为实际的主机 ID
```

## 完整 SQL 脚本

详细的 SQL 脚本请参考：`docs/database/fix_vnc_incomplete_data.sql`

