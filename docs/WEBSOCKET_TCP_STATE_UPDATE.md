# WebSocket TCP 状态更新实现文档

## 📋 功能概述

实现 WebSocket 连接生命周期中自动更新 `host_rec` 表的 `tcp_state` 字段，实时反映主机的 TCP 连接状态。

## 🎯 TCP 状态定义

| tcp_state | 状态名称 | 触发时机 | 说明 |
|-----------|----------|----------|------|
| **0** | 关闭 (close) | WebSocket 连接断开 | 主机断开连接或服务端主动关闭连接 |
| **1** | 等待 (wait) | 心跳超时 | 超过 60 秒未收到心跳，但连接未断开 |
| **2** | 监听 (lsn) | WebSocket 连接建立成功 | 主机成功建立 WebSocket 连接 |

## 🔧 实现更改

### 1. 数据库模型更新

#### `services/host-service/app/models/host_rec.py`

添加 `tcp_state` 字段：

```python
# TCP在线状态;{close: 0, 关闭. wait: 1, 等待. lsn: 2, 监听.}
tcp_state: Mapped[Optional[int]] = mapped_column(
    SmallInteger,
    nullable=True,
    index=True,
    comment="tcp在线状态;{close: 0, 关闭. wait: 1, 等待. lsn: 2, 监听.}",
)
```

**特性**:
- 字段类型: `TINYINT` (通过 `SmallInteger` 映射)
- 可空: `True` (兼容现有数据)
- 索引: `True` (优化查询性能)
- 默认值: `0` (关闭)

### 2. 服务层更新

#### `services/host-service/app/services/host_service.py`

新增 `update_tcp_state` 方法：

```python
async def update_tcp_state(self, host_id: str, tcp_state: int) -> bool:
    """更新主机TCP连接状态

    Args:
        host_id: 主机ID (支持 HostRec.id 或 mg_id)
        tcp_state: TCP状态码 (0/1/2)

    Returns:
        True: 更新成功
        False: 更新失败
    """
```

**特性**:
- 支持 `id` 和 `mg_id` 两种查询方式
- 自动验证 `tcp_state` 取值范围 (0/1/2)
- 静默失败，不影响 WebSocket 核心功能
- 详细日志记录，便于监控和故障排查

### 3. WebSocket 管理器更新

#### `services/host-service/app/services/websocket_manager.py`

在三个关键生命周期点更新 TCP 状态：

##### 连接建立时 (tcp_state = 2)

```python
async def connect(self, agent_id: str, websocket: WebSocket) -> None:
    """建立 WebSocket 连接"""
    self.active_connections[agent_id] = websocket
    
    # 发送欢迎消息
    await self._send_welcome_message(agent_id)
    
    # ✅ 更新 TCP 状态为 2 (监听/连接建立)
    await self.host_service.update_tcp_state(agent_id, tcp_state=2)
    
    # 启动心跳检测
    self.heartbeat_tasks[agent_id] = asyncio.create_task(
        self._heartbeat_monitor(agent_id)
    )
```

##### 心跳超时时 (tcp_state = 1)

```python
async def _heartbeat_monitor(self, agent_id: str) -> None:
    """心跳监控任务"""
    while True:
        await asyncio.sleep(self.heartbeat_timeout)  # 60秒
        
        if agent_id in self.heartbeat_timestamps:
            last_heartbeat_time = self.heartbeat_timestamps[agent_id]
            time_since_heartbeat = (
                datetime.now(timezone.utc) - last_heartbeat_time
            ).total_seconds()
            
            if time_since_heartbeat > self.heartbeat_timeout:
                logger.warning(f"心跳超时: {agent_id}")
                
                # ✅ 更新 TCP 状态为 1 (等待/心跳超时)
                await self.host_service.update_tcp_state(agent_id, tcp_state=1)
                
                # 发送超时警告给客户端
                timeout_msg = {
                    "type": "heartbeat_timeout_warning",
                    "message": "心跳超时警告",
                    "timeout": self.heartbeat_timeout,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await self.send_to_host(agent_id, timeout_msg)
```

##### 连接断开时 (tcp_state = 0)

```python
async def disconnect(self, agent_id: str) -> None:
    """断开 WebSocket 连接"""
    # 取消心跳检测任务
    if agent_id in self.heartbeat_tasks:
        self.heartbeat_tasks[agent_id].cancel()
        del self.heartbeat_tasks[agent_id]
    
    # 移除连接
    if agent_id in self.active_connections:
        del self.active_connections[agent_id]
    
    # 清理心跳时间戳
    if agent_id in self.heartbeat_timestamps:
        del self.heartbeat_timestamps[agent_id]
    
    # ✅ 更新 TCP 状态为 0 (关闭/连接断开)
    await self.host_service.update_tcp_state(agent_id, tcp_state=0)
    
    # 更新主机状态为离线
    await self.host_service.update_host_status(
        agent_id, HostStatusUpdate(status="offline")
    )
```

## 🗄️ 数据库迁移

### 执行迁移脚本

```bash
# 进入项目根目录
cd /path/to/intel_ec_ms

# 执行迁移脚本
python services/host-service/migrate_add_tcp_state.py
```

### 迁移脚本功能

`services/host-service/migrate_add_tcp_state.py`:

1. **检查字段是否已存在** - 避免重复执行
2. **添加 tcp_state 字段** - 使用 `ALTER TABLE` 语句
3. **创建索引** - 优化查询性能
4. **自动回滚** - 失败时自动回滚事务

### 手动执行 SQL（可选）

如果需要手动执行，可以使用以下 SQL 语句：

```sql
-- 添加 tcp_state 字段
ALTER TABLE host_rec
ADD COLUMN tcp_state TINYINT NULL DEFAULT 0
COMMENT 'tcp在线状态;{close: 0, 关闭. wait: 1, 等待. lsn: 2, 监听.}'
AFTER appr_state;

-- 创建索引
CREATE INDEX ix_tcp_state ON host_rec (tcp_state ASC);
```

## 📊 日志示例

### 连接建立日志

```log
2025-10-29 10:00:00.123 | INFO | websocket_manager:connect:123 | WebSocket 连接已建立
    extra={
        "agent_id": "1846486359367955051",
        "total_connections": 5
    }

2025-10-29 10:00:00.125 | INFO | host_service:update_tcp_state:356 | TCP状态已更新: host_id=1846486359367955051, tcp_state=2
    extra={
        "host_id": "1846486359367955051",
        "tcp_state": 2,
        "tcp_state_name": "监听"
    }
```

### 心跳超时日志

```log
2025-10-29 10:01:05.234 | WARNING | websocket_manager:_heartbeat_monitor:423 | 心跳超时: 1846486359367955051
    extra={
        "last_heartbeat_seconds_ago": 65.2,
        "timeout_threshold": 60
    }

2025-10-29 10:01:05.236 | INFO | host_service:update_tcp_state:356 | TCP状态已更新: host_id=1846486359367955051, tcp_state=1
    extra={
        "host_id": "1846486359367955051",
        "tcp_state": 1,
        "tcp_state_name": "等待"
    }
```

### 连接断开日志

```log
2025-10-29 10:02:30.456 | INFO | host_service:update_tcp_state:356 | TCP状态已更新: host_id=1846486359367955051, tcp_state=0
    extra={
        "host_id": "1846486359367955051",
        "tcp_state": 0,
        "tcp_state_name": "关闭"
    }

2025-10-29 10:02:30.458 | INFO | websocket_manager:disconnect:157 | WebSocket 连接已断开
    extra={
        "agent_id": "1846486359367955051",
        "remaining_connections": 4
    }
```

## 🔍 监控和查询

### 查询在线主机

```sql
-- 查询所有在线主机（tcp_state = 2）
SELECT id, mg_id, host_ip, tcp_state, updated_time
FROM host_rec
WHERE tcp_state = 2 AND del_flag = 0;
```

### 查询心跳超时主机

```sql
-- 查询心跳超时但连接未断开的主机（tcp_state = 1）
SELECT id, mg_id, host_ip, tcp_state, updated_time,
       TIMESTAMPDIFF(SECOND, updated_time, NOW()) as seconds_since_last_update
FROM host_rec
WHERE tcp_state = 1 AND del_flag = 0;
```

### 查询离线主机

```sql
-- 查询离线主机（tcp_state = 0）
SELECT id, mg_id, host_ip, tcp_state, updated_time
FROM host_rec
WHERE tcp_state = 0 AND del_flag = 0;
```

### 统计 TCP 状态分布

```sql
-- 统计各 TCP 状态的主机数量
SELECT
    tcp_state,
    CASE tcp_state
        WHEN 0 THEN '关闭'
        WHEN 1 THEN '等待'
        WHEN 2 THEN '监听'
        ELSE '未知'
    END as state_name,
    COUNT(*) as host_count
FROM host_rec
WHERE del_flag = 0
GROUP BY tcp_state;
```

## 🚨 故障排查

### 1. TCP 状态未更新

**问题**: WebSocket 连接建立但 `tcp_state` 仍为 0

**排查步骤**:
1. 检查日志中是否有 `update_tcp_state` 的 `INFO` 日志
2. 检查 `host_id` 是否存在于 `host_rec` 表
3. 检查数据库连接是否正常

**解决方案**:
```bash
# 查看 Host Service 日志
docker-compose logs host-service | grep "TCP状态"

# 检查数据库连接
docker-compose exec mysql mysql -uroot -proot -e "SELECT COUNT(*) FROM intel_cw_db.host_rec WHERE tcp_state IS NOT NULL;"
```

### 2. host_id 类型不匹配

**问题**: `host_id` 是字符串但数据库 `id` 字段是 `BIGINT`

**排查步骤**:
1. 检查日志中是否有 "无效的 tcp_state 值" 或类型转换错误
2. 确认 `host_id` 是否是有效的整数字符串或 `mg_id`

**解决方案**:
```python
# update_tcp_state 方法已支持两种查询方式：
# 1. 通过 id (整数)
# 2. 通过 mg_id (字符串)

# 如果 host_id 是 mg_id，会自动查询对应的 id
```

### 3. 心跳超时状态持续

**问题**: `tcp_state` 长时间保持为 1（等待）

**排查步骤**:
1. 检查客户端是否正常发送心跳
2. 检查心跳间隔是否 < 60 秒
3. 查看是否有网络延迟或丢包

**解决方案**:
```bash
# 检查心跳日志
docker-compose logs host-service | grep "heartbeat"

# 手动重置 TCP 状态
mysql -uroot -proot intel_cw_db -e "UPDATE host_rec SET tcp_state=2 WHERE id={host_id};"
```

## ✅ 测试验证

### 1. 连接建立测试

```bash
# 建立 WebSocket 连接
wscat -c "ws://localhost:8000/api/v1/ws/host" \
  -H "Authorization: Bearer {your_token}"

# 查询 TCP 状态（应为 2）
mysql -uroot -proot intel_cw_db -e "SELECT id, mg_id, tcp_state FROM host_rec WHERE mg_id='{your_mg_id}';"
```

### 2. 心跳超时测试

```bash
# 建立连接后停止发送心跳，等待 60 秒

# 查询 TCP 状态（应为 1）
mysql -uroot -proot intel_cw_db -e "SELECT id, mg_id, tcp_state, updated_time FROM host_rec WHERE mg_id='{your_mg_id}';"
```

### 3. 连接断开测试

```bash
# 主动断开 WebSocket 连接
# Ctrl+C 或发送断开消息

# 查询 TCP 状态（应为 0）
mysql -uroot -proot intel_cw_db -e "SELECT id, mg_id, tcp_state FROM host_rec WHERE mg_id='{your_mg_id}';"
```

## 📋 部署检查清单

- [ ] 数据库迁移脚本已成功执行
- [ ] `host_rec` 表已添加 `tcp_state` 字段
- [ ] `ix_tcp_state` 索引已创建
- [ ] Host Service 重启后正常运行
- [ ] WebSocket 连接建立时 `tcp_state = 2`
- [ ] 心跳超时时 `tcp_state = 1`
- [ ] 连接断开时 `tcp_state = 0`
- [ ] 日志中能看到 TCP 状态更新记录

## 🔗 相关文件

- `services/host-service/app/models/host_rec.py` - 数据模型定义
- `services/host-service/app/services/host_service.py` - TCP 状态更新逻辑
- `services/host-service/app/services/websocket_manager.py` - WebSocket 生命周期管理
- `services/host-service/migrate_add_tcp_state.py` - 数据库迁移脚本

---

**最后更新**: 2025-10-29
**功能版本**: v1.0.0
**状态**: ✅ 已实现并测试

