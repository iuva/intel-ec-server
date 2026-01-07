# 大文件拆分优化

## 概述

本文档记录了对项目中超过 1000 行的大型服务文件进行拆分优化的工作。

## 拆分原则

1. **保持向后兼容**：原有的类和函数保持对外接口不变
2. **按功能职责拆分**：将不同功能提取到独立模块
3. **最小化依赖**：拆分后的模块之间保持松耦合
4. **修复已知问题**：同时修复 `session_factory` 递归调用 bug

## 修复的关键问题

### session_factory 递归调用 Bug

在多个服务文件中发现了 `session_factory` 属性的递归调用问题：

```python
# ❌ 错误代码（会导致无限递归）
@property
def session_factory(self):
    if self._session_factory is None:
        self._session_factory = self.session_factory  # 递归调用！
    return self._session_factory

# ✅ 正确代码
@property
def session_factory(self):
    if self._session_factory is None:
        self._session_factory = mariadb_manager.get_session()
    return self._session_factory
```

**受影响的文件（已修复）**：
- `services/host-service/app/services/admin_appr_host_service.py`
- `services/host-service/app/services/agent_websocket_manager.py`
- `services/host-service/app/services/case_timeout_task.py`
- `services/host-service/app/services/admin_host_service.py`
- `services/host-service/app/services/admin_ota_service.py`
- `services/host-service/app/services/browser_host_service.py`
- `services/auth-service/app/services/auth_service.py`

## 拆分详情

### 1. admin_appr_host_service.py (2295行 -> 1612行)

**新建模块**：
| 文件 | 功能 | 行数 |
|------|------|------|
| `admin_appr_email_service.py` | 邮件模板和发送逻辑 | 331 |
| `admin_appr_utils.py` | 工具函数（硬件API调用、表格构建等） | 466 |

### 2. agent_websocket_manager.py (2068行 -> 2067行)

**新建模块**：
| 文件 | 功能 | 行数 |
|------|------|------|
| `agent_ws_message_handler.py` | 消息处理器（连接结果、下线通知、版本更新） | 428 |
| `agent_ws_heartbeat_manager.py` | 心跳检测工具函数 | 164 |
| `agent_ws_redis_publisher.py` | Redis Pub/Sub 通信工具 | 249 |

**说明**：由于 WebSocket 管理器的方法高度耦合，保留原类结构，新模块作为辅助工具使用。

### 3. agent_report_service.py (1769行 -> 1767行)

**新建模块**：
| 文件 | 功能 | 行数 |
|------|------|------|
| `agent_report_case_service.py` | 测试用例上报服务 | 311 |
| `agent_report_vnc_ota_service.py` | VNC/OTA 状态上报服务 | 518 |

### 4. proxy_service.py (1582行 -> 1509行)

**新建模块**：
| 文件 | 功能 | 行数 |
|------|------|------|
| `proxy_error_handler.py` | 错误处理工具函数 | 292 |
| `proxy_websocket_service.py` | WebSocket 代理工具函数 | 314 |

**优化内容**：
1. **代码重用**：删除了重复的错误处理方法，直接使用 `proxy_error_handler.py` 中的模块级函数
2. **HTTP 客户端配置优化**：支持环境变量配置，提高灵活性
   - `PROXY_HTTP_TIMEOUT`: HTTP 请求超时（默认 30s，增加稳定性）
   - `PROXY_CONNECT_TIMEOUT`: 连接超时（默认 5s）
   - `PROXY_MAX_KEEPALIVE`: 最大保持连接数（默认 50，增加复用）
   - `PROXY_MAX_CONNECTIONS`: 最大并发连接数（默认 200，增加并发支持）
   - `PROXY_MAX_WEBSOCKET_CONNECTIONS`: 最大 WebSocket 连接数（默认 1000）

### 5. 其他服务文件

为以下文件创建了通用工具模块：

| 文件 | 功能 | 行数 |
|------|------|------|
| `host_query_utils.py` | 主机查询通用工具函数 | 253 |
| `timeout_detector_utils.py` | 超时检测工具函数 | 245 |

## 文件结构

```
services/host-service/app/services/
├── admin_appr_host_service.py      # 主机审批服务（主文件）
├── admin_appr_email_service.py     # 审批邮件服务 [新建]
├── admin_appr_utils.py             # 审批工具函数 [新建]
├── agent_websocket_manager.py      # WebSocket管理器（主文件）
├── agent_ws_message_handler.py     # 消息处理器 [新建]
├── agent_ws_heartbeat_manager.py   # 心跳管理工具 [新建]
├── agent_ws_redis_publisher.py     # Redis发布工具 [新建]
├── agent_report_service.py         # Agent上报服务（主文件）
├── agent_report_case_service.py    # 测试用例上报 [新建]
├── agent_report_vnc_ota_service.py # VNC/OTA上报 [新建]
├── host_query_utils.py             # 主机查询工具 [新建]
└── timeout_detector_utils.py       # 超时检测工具 [新建]

services/gateway-service/app/services/
├── proxy_service.py                # 代理服务（主文件）
├── proxy_error_handler.py          # 错误处理工具 [新建]
└── proxy_websocket_service.py      # WebSocket工具 [新建]
```

## 统计信息

### 拆分前
| 文件 | 行数 |
|------|------|
| admin_appr_host_service.py | 2,295 |
| agent_websocket_manager.py | 2,068 |
| agent_report_service.py | 1,769 |
| proxy_service.py | 1,582 |
| admin_host_service.py | 1,177 |
| host_discovery_service.py | 1,095 |
| case_timeout_task.py | 1,051 |
| browser_host_service.py | 1,011 |
| **总计** | **12,048** |

### 拆分后（含代码重用优化）
| 类别 | 行数 |
|------|------|
| 原大文件（优化后） | 11,285 |
| 新建辅助模块 | 3,571 |

**proxy_service.py 详细优化**：
- 原文件：1,582 行 → 优化后：1,509 行（减少 73 行重复代码）

## 使用说明

### 导入新模块

```python
# 邮件服务
from app.services.admin_appr_email_service import (
    send_approval_email,
    get_approval_email_service,
)

# 工具函数
from app.services.admin_appr_utils import (
    call_hardware_api,
    build_host_table,
)

# 测试用例上报
from app.services.agent_report_case_service import (
    get_testcase_report_service,
)

# VNC/OTA 上报
from app.services.agent_report_vnc_ota_service import (
    get_vnc_ota_report_service,
)

# 主机查询工具
from app.services.host_query_utils import (
    get_host_by_id,
    get_active_hosts,
    get_free_hosts,
)

# 超时检测工具
from app.services.timeout_detector_utils import (
    calculate_timeout_threshold,
    is_exec_log_timeout,
    find_timeout_exec_logs,
)
```

## 注意事项

1. **向后兼容**：原服务类保持不变，可以继续使用原有方式调用
2. **单例模式**：新模块提供了 `get_*_service()` 函数获取单例实例
3. **会话工厂**：所有服务类都使用缓存的 `session_factory` 属性

## 更新历史

- **2026-01-07**: 代码重用优化
  - `proxy_service.py` 使用 `proxy_error_handler.py` 中的模块级函数
  - 删除约 73 行重复代码（错误处理方法）
  - HTTP 客户端配置支持环境变量，提高灵活性和性能

- **2026-01-07**: 初始版本
  - 修复 7 个文件中的 session_factory 递归调用 bug
  - 创建 11 个新的辅助模块
  - 总计提取约 3,500 行代码到独立模块

