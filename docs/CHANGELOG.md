# 更新日志 (Changelog)

## [2025-10-29] - Agent WebSocket API 重命名

### 🔄 重大重构

#### 1. Agent WebSocket API 文件和类重命名
- **API 端点文件重命名**:
  - `websocket.py` → `agent_websocket.py`（Agent WebSocket 连接端点）
  - `websocket_management.py` → `agent_websocket_management.py`（Agent WebSocket 管理端点）
- **服务类重命名**:
  - `WebSocketManager` → `AgentWebSocketManager`（Agent WebSocket 连接管理器）
  - `get_websocket_manager()` → `get_agent_websocket_manager()`（依赖注入函数）
- **服务文件重命名**:
  - `websocket_manager.py` → `agent_websocket_manager.py`

#### 2. 路由标签更新
- 原标签：`WebSocket连接`、`WebSocket管理`
- 新标签：`Agent-WebSocket连接`、`Agent-WebSocket管理`
- **API 路由路径保持不变**，确保向后兼容

#### 3. 受影响的文件
- `app/api/v1/__init__.py` - 路由注册更新
- `app/services/__init__.py` - 服务导出更新
- `app/api/v1/endpoints/agent_websocket.py` - 导入更新
- `app/api/v1/endpoints/agent_websocket_management.py` - 导入和调用更新
- `app/services/agent_websocket_manager.py` - 类名和函数名更新

### 📝 重命名原因
1. **语义清晰化**: 明确区分 Agent WebSocket API 和浏览器插件 API
2. **职责分离**: Agent WebSocket 用于实时通信，浏览器插件 API 用于 HTTP 请求
3. **代码可维护性**: 清晰的命名使代码结构更容易理解

### 🔗 相关文档
- [Agent WebSocket API 重命名文档](./agent-websocket-api-rename.md)

---

## [2025-10-29] - 浏览器插件 API 重命名

### 🔄 重大重构

#### 1. 浏览器插件 API 文件和类重命名
- **API 端点文件重命名**:
  - `hosts.py` → `browser_hosts.py`（浏览器插件主机管理 API）
  - `vnc.py` → `browser_vnc.py`（浏览器插件 VNC 连接管理 API）
- **服务类重命名**:
  - `HostService` → `BrowserHostService`（浏览器插件主机管理服务）
  - `VNCService` → `BrowserVNCService`（浏览器插件 VNC 连接管理服务）
- **服务文件重命名**:
  - `host_service.py` → `browser_host_service.py`
  - `vnc_service.py` → `browser_vnc_service.py`

#### 2. 路由标签更新
- 原标签：`主机管理`、`VNC连接管理`
- 新标签：`浏览器插件-主机管理`、`浏览器插件-VNC连接管理`
- **API 路由路径保持不变**，确保向后兼容

#### 3. 受影响的文件
- `app/api/v1/__init__.py` - 路由注册更新
- `app/api/v1/dependencies.py` - 依赖注入更新
- `app/services/__init__.py` - 服务导出更新
- `app/services/websocket_manager.py` - 服务导入更新

### 📝 重命名原因
1. **语义清晰化**: 明确区分浏览器插件 API 和 Agent WebSocket API
2. **职责分离**: 不同客户端使用不同的接口
3. **便于维护**: 清晰的命名使代码更易理解和扩展

### ✅ 兼容性保证
- API 路由路径完全保持不变
- 响应格式完全保持不变
- 无破坏性变更，向后兼容

### 📊 代码质量
- ✅ 通过 Ruff 代码质量检查
- ✅ 通过 MyPy + Pyright 类型检查
- ✅ 无 linter 错误
- ✅ 服务重启成功

---

## [2025-10-29] - WebSocket 连接结果上报功能新增

### ✨ 新增功能

#### 1. Agent 上报连接结果消息类型
- **消息类型**: `connection_result`
- **功能**: Agent 通过 WebSocket 上报连接结果
- **业务逻辑**:
  - 查询 `host_exec_log` 表（`host_id = token中的host_id`, `host_state = 1`, `del_flag = 0`）
  - 获取最新一条记录（按 `created_at` 降序）
  - **不存在记录**: 返回错误消息 `connection_result_error`
  - **存在记录**: 更新 `host_state = 2`（已占用）并下发执行参数

#### 2. Server 下发执行参数消息类型
- **消息类型**: `execute_params`
- **功能**: Server 自动下发执行参数给 Agent
- **下发内容**:
  - `tc_id`: 测试用例ID
  - `cycle_name`: 测试周期名称
  - `user_name`: 用户名称

#### 3. 连接结果错误消息类型
- **消息类型**: `connection_result_error`
- **功能**: 当未找到待执行任务时返回错误
- **错误场景**: 用户尚未通过 VNC 上报连接结果

### 📝 业务流程

```
1. Agent 建立 WebSocket 连接
   ↓
2. Agent 发送连接结果消息 (type: connection_result)
   ↓
3. Server 查询 host_exec_log 表
   ├─ host_id = token 中的 host_id
   ├─ host_state = 1 (已锁定)
   └─ del_flag = 0
   按 created_at 降序，获取最新一条
   ↓
4. 判断查询结果
   ├─ 不存在记录 → 返回错误消息 (type: connection_result_error)
   └─ 存在记录 → ① 更新 host_state = 2 (已占用)
                  ② 下发执行参数 (type: execute_params)
```

### 📊 数据库状态流转

```
VNC 上报完成 → host_state = 1 (已锁定)
      ↓
Agent 上报连接 → host_state = 2 (已占用)
      ↓
任务执行完成 → case_state = 2 (成功) 或 3 (失败)
```

### 🛠️ 技术实现

#### 1. WebSocket 消息处理器
- **文件**: `services/host-service/app/services/websocket_manager.py`
- **新增方法**: `_handle_connection_result(agent_id, data)`
- **功能**:
  - 查询 `host_exec_log` 表
  - 更新 `host_state`
  - 下发执行参数

#### 2. 消息类型注册
- 在 `_register_default_handlers()` 中注册 `connection_result` 消息处理器
- 支持自动路由和处理

#### 3. 错误处理
- 主机ID格式验证
- 数据库查询异常处理
- 详细日志记录

### 📚 相关文档

- **API 文档**: [websocket-connection-result-api.md](websocket-connection-result-api.md)
- **示例代码**: JavaScript 和 Python 客户端完整示例
- **故障排查**: 常见问题及解决方案

### 🔗 关联更新

此功能依赖于之前更新的 VNC 连接结果上报 API：
- VNC 上报创建 `host_state = 1` 的记录
- Agent 上报更新 `host_state = 2` 的记录
- 完整的任务执行流程闭环

---

## [2025-10-29] - 上报 VNC 连接结果 API 重大更新

### ✨ 新增功能

#### 1. VNC 连接结果上报 API 增强
- **端点**: `POST /api/v1/host/vnc/report`
- **功能**: 上报 VNC 连接结果，自动管理执行日志
- **新增请求参数**:
  - `tc_id`: 执行测试ID（必填）
  - `cycle_name`: 周期名称（必填）
  - `user_name`: 用户名称（必填）

#### 2. 执行日志自动管理
- **智能处理**: 当 `connection_status = "success"` 时
  - 查询 `host_exec_log` 表（匹配 user_id、tc_id、cycle_name、user_name、host_id、del_flag=0）
  - **存在旧记录**: 先逻辑删除旧记录（`del_flag = 1`），然后新增新记录（`host_state = 1`, `case_state = 0`）
  - **不存在旧记录**: 直接新增新记录（`host_state = 1`, `case_state = 0`）
- **主机状态更新**: `host_state = 1`（已锁定）, `subm_time = 当前时间`

### 📝 业务逻辑流程

```
1. 验证主机存在性
   ↓
2. 连接状态 = success?
   ├─ YES → 查询 host_exec_log
   │         ├─ 存在旧记录 → 先逻辑删除旧记录 (del_flag=1)
   │         │                然后新增新记录 (host_state=1, case_state=0)
   │         └─ 不存在旧记录 → 直接新增新记录 (host_state=1, case_state=0)
   └─ NO → 跳过执行日志处理
   ↓
3. 更新 host_rec (host_state=1, subm_time=now)
   ↓
4. 返回成功响应
```

### ⚠️ 破坏性变更

此更新包含 **破坏性变更**，新增了 3 个必填参数：

#### 旧版本请求（不再支持）
```json
{
  "user_id": "user123",
  "host_id": "123",
  "connection_status": "success",
  "connection_time": "2025-10-29T10:00:00Z"
}
```

#### 新版本请求（必须）
```json
{
  "user_id": "user123",
  "tc_id": "test001",           // 新增：必填
  "cycle_name": "cycle_001",   // 新增：必填
  "user_name": "John Doe",     // 新增：必填
  "host_id": "123",
  "connection_status": "success",
  "connection_time": "2025-10-29T10:00:00Z"
}
```

### 🔄 响应消息优化

响应消息现在包含执行日志操作信息：
- `"VNC连接结果上报成功，主机已锁定"` - 连接失败或未处理日志
- `"VNC连接结果上报成功，主机已锁定，执行日志已deleted"` - 逻辑删除已存在日志
- `"VNC连接结果上报成功，主机已锁定，执行日志已created"` - 新增执行日志

### 📝 文档更新

#### 1. API 更新文档
- **[docs/api/vnc-report-api-update.md](./api/vnc-report-api-update.md)**: 完整的更新说明
  - 新增参数详细说明
  - 业务逻辑流程图
  - 使用场景示例（首次上报、重复上报、连接失败）
  - 向后兼容性和迁移指南

### 🔧 技术实现

#### 1. 数据库操作
- 使用 SQLAlchemy 异步 ORM
- 事务支持确保数据一致性
- 逻辑删除设计，数据可恢复
- 查询条件：
  ```sql
  SELECT * FROM host_exec_log
  WHERE user_id = :user_id
    AND tc_id = :tc_id
    AND cycle_name = :cycle_name
    AND user_name = :user_name
    AND host_id = :host_id
    AND del_flag = 0
  ```

#### 2. 代码质量
- 遵循项目编码规范
- 通过 Ruff + MyPy + Pyright 检查
- 完整的类型注解
- 结构化日志记录

### 📊 日志增强

新增日志字段：
```json
{
  "operation": "report_vnc_connection",
  "user_id": "user123",
  "tc_id": "test001",
  "cycle_name": "cycle_001",
  "user_name": "John Doe",
  "host_id": "123",
  "connection_status": "success",
  "exec_log_action": "created"  // null | "deleted" | "created"
}
```

### 🔐 安全考虑

1. **认证验证**: 需要有效的 JWT Token
2. **数据验证**: 所有必填字段进行验证
3. **主机ID验证**: 验证格式和存在性
4. **事务支持**: 确保数据一致性
5. **日志审计**: 详细记录所有操作

### 🎯 适用场景

- **场景1**: 首次 VNC 连接成功 → 新增执行日志
- **场景2**: 重复 VNC 连接成功 → 逻辑删除旧日志
- **场景3**: VNC 连接失败 → 仅更新主机状态

### 📦 相关文件

- `services/host-service/app/api/v1/endpoints/vnc.py` - API 端点定义
- `services/host-service/app/services/vnc_service.py` - 业务逻辑实现
- `services/host-service/app/schemas/host.py` - 请求/响应模型
- `services/host-service/app/models/host_exec_log.py` - 执行日志模型

---

## [2025-10-29] - 新增释放主机 API（逻辑删除）

### ✨ 新增功能

#### 1. 释放主机 API
- **端点**: `POST /api/v1/host/hosts/release`
- **功能**: 逻辑删除指定用户的主机执行日志记录（设置 `del_flag = 1`），释放主机资源
- **业务逻辑**:
  - 逻辑删除 `host_exec_log` 表中的记录（UPDATE `del_flag = 1`）
  - 条件: `user_id = 入参的 user_id` AND `host_id IN (host_list)` AND `del_flag = 0`
  - 返回实际更新的记录数

#### 2. 新增数据模型
- **`ReleaseHostsRequest`**: 释放主机请求模型
  - `user_id`: 用户ID
  - `host_list`: 主机ID列表（支持批量）
- **`ReleaseHostsResponse`**: 释放主机响应模型
  - `updated_count`: 实际更新的记录数（逻辑删除）
  - `user_id`: 用户ID
  - `host_list`: 主机ID列表

#### 3. 新增服务方法
- **`HostService.release_hosts()`**: 实现释放主机业务逻辑
  - 支持批量逻辑删除
  - 主机ID格式验证
  - 完整的错误处理和日志记录
  - 软删除设计，数据可恢复

### 📝 文档更新

#### 1. API 文档
- **[docs/api/release-hosts-api.md](./api/release-hosts-api.md)**: 完整的 API 使用文档
  - 请求参数说明
  - 响应格式说明
  - 使用场景示例
  - 安全和性能考虑
  - 测试步骤

#### 2. 测试脚本
- **[scripts/test_release_hosts_api.sh](../scripts/test_release_hosts_api.sh)**: API 测试脚本
  - 自动获取 JWT Token
  - 支持批量释放主机
  - 格式化输出结果
  - 支持自定义参数

### 🔧 技术实现

#### 1. 数据库操作
- 使用 SQLAlchemy `update()` 语句（逻辑删除）
- 支持 `IN` 操作符批量更新
- 利用已有索引（`user_id`、`host_id`、`del_flag`）
- 事务支持确保数据一致性
- 软删除设计，数据可恢复

#### 2. 代码质量
- 遵循项目编码规范
- 通过 Ruff + MyPy + Pyright 检查
- 完整的类型注解
- 结构化日志记录

### 📊 使用示例

#### 请求示例
```bash
curl -X POST "http://localhost:8000/api/v1/host/hosts/release" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "adb1852278641262sdf097",
    "host_list": [
        "1852278641262084097",
        "1852278641262084098"
    ]
  }'
```

#### 响应示例
```json
{
  "updated_count": 5,
  "user_id": "adb1852278641262sdf097",
  "host_list": [
    "1852278641262084097",
    "1852278641262084098"
  ]
}
```

### 🔐 安全考虑

1. **权限验证**: 需要有效的 JWT Token
2. **用户隔离**: 只更新指定用户的记录
3. **参数验证**: 验证主机ID格式
4. **日志审计**: 详细记录删除操作
5. **数据恢复**: 软删除支持误操作恢复

### 📦 相关文件

#### 新增文件
- `docs/api/release-hosts-api.md` - API 文档
- `scripts/test_release_hosts_api.sh` - 测试脚本

#### 修改文件
- `services/host-service/app/schemas/host.py` - 添加请求/响应模型
- `services/host-service/app/services/host_service.py` - 添加业务逻辑
- `services/host-service/app/api/v1/endpoints/hosts.py` - 添加 API 端点

### ✅ 测试验证

#### 1. 代码质量检查
```bash
# 通过 Ruff 检查
ruff check services/host-service/

# 无 linter 错误
```

#### 2. 服务启动测试
```bash
# Host-Service 成功重启
docker-compose restart host-service

# 服务正常运行
```

#### 3. API 功能测试
```bash
# 运行测试脚本
./scripts/test_release_hosts_api.sh

# 预期结果：返回删除的记录数
```

### 🔄 与其他 API 的关系

- **与重试 VNC 列表 API**: 释放主机后，该主机将不再出现在重试列表中
- **与查询可用主机 API**: 释放主机不影响主机的可用状态，只删除执行记录

---

## [2025-10-29] - 新增重试 VNC 列表 API

### ✨ 新增功能

#### 1. 重试 VNC 列表查询 API
- **端点**: `POST /api/v1/host/hosts/retry-vnc`
- **功能**: 查询指定用户所有未成功的 VNC 连接主机列表
- **业务逻辑**:
  - 查询 `host_exec_log` 表中 `case_state != 2` 的记录
  - 关联 `host_rec` 表获取主机详细信息
  - 返回 `host_id`、`host_ip` 和 `user_name`（主机账号）

#### 2. 新增数据模型
- **`HostExecLog`**: 主机执行日志模型
  - 对应数据库表 `host_exec_log`
  - 包含执行用户、测试用例ID、周期名称等字段
  - 支持 case 执行状态跟踪
- **`GetRetryVNCListRequest`**: 获取重试 VNC 列表请求模型
- **`RetryVNCHostInfo`**: 重试 VNC 主机信息模型
- **`RetryVNCListResponse`**: 重试 VNC 列表响应模型

#### 3. 新增服务方法
- **`HostService.get_retry_vnc_list()`**: 实现重试 VNC 列表查询逻辑
  - 支持多表关联查询
  - 自动去重处理
  - 完整的错误处理和日志记录

### 📝 文档更新

#### 1. API 文档
- **[docs/api/retry-vnc-api.md](./api/retry-vnc-api.md)**: 完整的 API 使用文档
  - 请求参数说明
  - 响应格式说明
  - 使用场景示例
  - 数据库查询逻辑
  - 测试步骤

#### 2. 测试脚本
- **[scripts/test_retry_vnc_api.sh](../scripts/test_retry_vnc_api.sh)**: API 测试脚本
  - 自动获取 JWT Token
  - 调用重试 VNC 列表 API
  - 格式化输出结果
  - 支持自定义参数

### 🔧 技术实现

#### 1. 数据库查询优化
- 使用 SQLAlchemy 异步 ORM
- 利用已有索引（`user_id`、`case_state`、`del_flag`）
- `DISTINCT` 去重避免重复记录
- 防止 NULL 值导致的数据问题

#### 2. 代码质量
- 遵循项目编码规范
- 通过 Ruff + MyPy + Pyright 检查
- 完整的类型注解
- 结构化日志记录

### 📊 数据库结构

#### host_exec_log 表
```sql
CREATE TABLE host_exec_log(
    `id` BIGINT NOT NULL COMMENT '主键',
    `host_id` BIGINT COMMENT '主机主键;host_rec 表主键',
    `user_id` VARCHAR(64) COMMENT '执行用户',
    `tc_id` VARCHAR(64) COMMENT '执行测试 id',
    `cycle_name` VARCHAR(128) COMMENT '周期名称',
    `user_name` VARCHAR(32) COMMENT '用户名称',
    `case_state` TINYINT DEFAULT 0 COMMENT 'case 执行状态;0-空闲 1-启动 2-成功 3-失败',
    -- 其他字段...
    PRIMARY KEY (`id`)
)
```

### 🔍 查询逻辑

#### case_state 状态说明
| 值 | 状态 | 说明 | 是否包含在重试列表 |
|---|------|------|--------------------|
| 0 | free | 空闲 | ✅ 是 |
| 1 | start | 启动 | ✅ 是 |
| 2 | success | 成功 | ❌ 否（排除） |
| 3 | failed | 失败 | ✅ 是 |

### 🎯 使用示例

#### 请求示例
```bash
curl -X POST "http://localhost:8000/api/v1/host/hosts/retry-vnc" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1852278641262084097"}'
```

#### 响应示例
```json
{
  "hosts": [
    {
      "host_id": 1846486359367955051,
      "host_ip": "192.168.1.100",
      "user_name": "admin"
    }
  ],
  "total": 1
}
```

### 📦 相关文件

#### 新增文件
- `services/host-service/app/models/host_exec_log.py` - 执行日志模型
- `docs/api/retry-vnc-api.md` - API 文档
- `scripts/test_retry_vnc_api.sh` - 测试脚本

#### 修改文件
- `services/host-service/app/schemas/host.py` - 添加请求/响应模型
- `services/host-service/app/services/host_service.py` - 添加业务逻辑
- `services/host-service/app/api/v1/endpoints/hosts.py` - 添加 API 端点

### ✅ 测试验证

#### 1. 代码质量检查
```bash
# 通过 Ruff 检查
ruff check services/host-service/

# 通过 MyPy 类型检查
mypy services/host-service/

# 无 linter 错误
```

#### 2. 服务启动测试
```bash
# Host-Service 成功重启
docker-compose restart host-service

# 服务正常运行
docker-compose logs host-service | grep "启动成功"
```

#### 3. API 功能测试
```bash
# 运行测试脚本
./scripts/test_retry_vnc_api.sh

# 预期结果：返回重试主机列表或空列表
```

### 🔄 下一步优化建议

1. **性能优化**
   - 添加分页支持（如果返回结果过多）
   - 考虑添加缓存机制
   - 优化数据库查询（如需要）

2. **功能增强**
   - 添加按时间范围过滤
   - 支持按 case_state 精确筛选
   - 添加排序功能（按失败时间、主机ID等）

3. **监控和告警**
   - 添加 API 调用监控指标
   - 统计重试率和成功率
   - 失败次数告警

### 📝 注意事项

1. **数据一致性**: 确保 `host_exec_log` 表正确记录执行状态
2. **性能考虑**: 大量数据时建议添加分页
3. **权限控制**: 确保用户只能查询自己的执行记录
4. **数据清理**: 定期清理过期的执行日志

---

## 之前的更新

### [2025-10-29] - 修复 TCP 状态更新失败问题

#### 🐛 Bug 修复
- 修复 `update_tcp_state` 方法中手动设置 `updated_time` 与 SQLAlchemy `onupdate=func.now()` 冲突的问题
- 增强错误日志，添加 `error_type` 和 `error_message` 字段
- 添加 `rowcount == 0` 的警告日志

### [2025-10-29] - 修复 WebSocket 路由问题

#### 🐛 Bug 修复
- 修复 Gateway 转发 WebSocket 时路径构建错误
- 修复 Host-Service API 路由前缀配置
- 确保 HTTP 和 WebSocket 转发逻辑一致

---

## 版本历史

### v1.0.0 - 初始版本
- 基础微服务架构
- 认证授权系统
- WebSocket 实时通信
- 监控和追踪系统
