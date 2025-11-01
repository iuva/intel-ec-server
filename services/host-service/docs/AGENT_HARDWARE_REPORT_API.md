# Agent 硬件信息上报 API 使用文档

## 📋 概述

本文档介绍 Agent 硬件信息上报 API 的使用方法和业务逻辑。

## 🔗 API 端点

```
POST /api/v1/agent/hardware/report
```

## 🎯 功能说明

Agent 上报主机硬件信息，系统会自动检测硬件变更并进行相应处理：

1. **首次上报**: 直接插入硬件记录，审批状态为通过（sync_state=2）
2. **版本号变化**: 标记为版本号变化（diff_state=1），等待审批（sync_state=1）
3. **内容变化**: 标记为内容更改（diff_state=2），等待审批（sync_state=1）
4. **无变化**: 不更新记录，返回无变化状态

## 📥 请求格式

### 请求头

```http
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

### 请求体

```json
{
  "name": "Updated Agent Config",
  "dmr_config": {
    "revision": 1,
    "mainboard": {
      "revision": 1,
      "plt_meta_data": {
        "platform": "DMR",
        "label_plt_cfg": "auto_generated"
      },
      "board": {
        "board_meta_data": {
          "board_name": "SHMRCDMR",
          "host_name": "updated-host",
          "host_ip": "10.239.168.200"
        },
        "baseboard": [
          {
            "board_id": "board_001",
            "rework_version": "1.0",
            "board_ip": "10.239.168.200",
            "bmc_ip": "10.239.168.171",
            "fru_id": "fru_001"
          }
        ],
        "lsio": {
          "usb_disc_installed": true,
          "network_installed": true,
          "nvme_installed": false,
          "keyboard_installed": true,
          "mouse_installed": false
        },
        "peripheral": {
          "itp_installed": true,
          "usb_dbc_installed": false,
          "controlbox_installed": true,
          "flash_programmer_installed": true,
          "display_installed": true,
          "jumpers": []
        }
      },
      "misc": {
        "installed_os": ["Windows", "Linux"],
        "bmc_version": "2.0.1",
        "bmc_ip": "10.239.168.171",
        "cpld_version": "2.1.0"
      }
    },
    "hsio": [],
    "memory": [],
    "security": {
      "revision": 1,
      "security": {
        "Tpm": [
          {
            "tpm_enable": true,
            "tpm_algorithm": "SHA256",
            "tmp_family": "2.0",
            "tpm_interface": "TIS"
          }
        ],
        "CoinBattery": []
      }
    },
    "soc": []
  },
  "updated_by": "agent@intel.com",
  "tags": ["alive", "checked", "updated"]
}
```

### 请求参数说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `dmr_config` | Object | ✅ | DMR硬件配置（必需） |
| `dmr_config.revision` | Number | ✅ | 硬件版本号（必需） |
| `name` | String | ❌ | 配置名称（可选） |
| `updated_by` | String | ❌ | 更新者（可选） |
| `tags` | Array | ❌ | 标签列表（可选） |

**⚠️ 注意**:
- `dmr_config` 是动态JSON，具体字段根据硬件模板定义
- 硬件模板中标记为 `required` 的字段必须提供
- `dmr_config.revision` 是必传字段，用于版本号对比

## 📤 响应格式

### 成功响应（首次上报）

```json
{
  "code": 200,
  "message": "硬件信息首次上报成功",
  "data": {
    "status": "first_report",
    "hw_rec_id": 1,
    "message": "硬件信息首次上报成功"
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

### 成功响应（版本号变化）

```json
{
  "code": 200,
  "message": "硬件信息已更新，等待审批",
  "data": {
    "status": "hardware_changed",
    "diff_state": 1,
    "diff_details": {
      "previous_revision": 0,
      "current_revision": 1
    },
    "hw_rec_id": 2,
    "message": "硬件信息已更新，等待审批"
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

### 成功响应（内容变化）

```json
{
  "code": 200,
  "message": "硬件信息已更新，等待审批",
  "data": {
    "status": "hardware_changed",
    "diff_state": 2,
    "diff_details": {
      "mainboard.board.board_meta_data.host_ip": {
        "type": "modified",
        "previous": "10.239.168.100",
        "current": "10.239.168.200"
      },
      "mainboard.misc.bmc_version": {
        "type": "modified",
        "previous": "2.0.0",
        "current": "2.0.1"
      }
    },
    "hw_rec_id": 3,
    "message": "硬件信息已更新，等待审批"
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

### 成功响应（无变化）

```json
{
  "code": 200,
  "message": "硬件信息无变化",
  "data": {
    "status": "no_change",
    "message": "硬件信息无变化"
  },
  "timestamp": "2025-01-30T10:00:00Z"
}
```

### 错误响应（缺少必填字段）

```json
{
  "code": 400,
  "message": "dmr_config 是必传字段",
  "error_code": "MISSING_DMR_CONFIG",
  "details": null,
  "timestamp": "2025-01-30T10:00:00Z"
}
```

### 错误响应（硬件模板未找到）

```json
{
  "code": 500,
  "message": "未找到硬件模板配置",
  "error_code": "HARDWARE_TEMPLATE_NOT_FOUND",
  "details": null,
  "timestamp": "2025-01-30T10:00:00Z"
}
```

## 📊 响应状态说明

| status | diff_state | sync_state | 说明 |
|---|---|---|---|
| `first_report` | - | 2 | 首次上报，直接通过 |
| `hardware_changed` | 1 | 1 | 版本号变化，等待审批 |
| `hardware_changed` | 2 | 1 | 内容变化，等待审批 |
| `no_change` | - | - | 无变化，不更新记录 |

### diff_state 枚举值

| 值 | 说明 |
|---|---|
| 1 | 版本号变化 |
| 2 | 内容更改 |
| 3 | 异常 |

### sync_state 枚举值

| 值 | 说明 |
|---|---|
| 0 | 空状态 |
| 1 | 待同步 |
| 2 | 通过 |
| 3 | 异常 |

## 🔄 业务流程

```
Agent 上报硬件信息
    │
    ├──→ 1. 验证 dmr_config 和 revision 必填
    │
    ├──→ 2. 从 sys_conf 表获取硬件模板（conf_key='hw_temp'）
    │
    ├──→ 3. 验证硬件信息必填字段（基于模板）
    │
    ├──→ 4. 获取当前生效的硬件记录（host_hw_rec 表）
    │
    ├──→ 5. 对比硬件信息
    │       ├─ 首次上报 → 插入记录（sync_state=2）
    │       ├─ 版本号变化 → diff_state=1, sync_state=1
    │       ├─ 内容变化 → diff_state=2, sync_state=1
    │       └─ 无变化 → 返回
    │
    └──→ 6. 更新数据库记录
            ├─ host_rec: appr_state=2, host_state=6
            └─ host_hw_rec: 插入新记录
```

## 🗄️ 数据库表结构

### sys_conf 表

```sql
CREATE TABLE sys_conf (
    id BIGINT NOT NULL COMMENT '主键',
    conf_key VARCHAR(32) COMMENT '配置 key',
    conf_val VARCHAR(255) COMMENT '配置值',
    conf_ver VARCHAR(32) COMMENT '配置版本号',
    conf_name VARCHAR(32) COMMENT '配置名称',
    conf_json JSON COMMENT '配置 json',
    state_flag TINYINT DEFAULT 0 COMMENT '状态',
    -- ...其他字段
    PRIMARY KEY (id)
) COMMENT '系统配置表';
```

### host_hw_rec 表

```sql
CREATE TABLE host_hw_rec (
    id BIGINT NOT NULL COMMENT '主键',
    hardware_id VARCHAR(64) COMMENT 'mongodb 主键',
    host_id BIGINT COMMENT '主机主键',
    hw_info JSON COMMENT '硬件信息',
    hw_ver VARCHAR(32) COMMENT '硬件版本号',
    diff_state TINYINT COMMENT '参数状态',
    sync_state TINYINT DEFAULT 0 COMMENT '同步状态',
    appr_time DATETIME COMMENT '审批时间',
    appr_by BIGINT COMMENT '审批人',
    -- ...其他字段
    PRIMARY KEY (id)
) COMMENT '主机硬件记录';
```

### host_rec 表

```sql
CREATE TABLE host_rec (
    id BIGINT NOT NULL COMMENT '主键',
    host_no VARCHAR(64) COMMENT '主机主键',
    appr_state TINYINT COMMENT '审批状态',
    host_state TINYINT COMMENT '主机状态',
    -- ...其他字段
    PRIMARY KEY (id)
) COMMENT '主机记录';
```

## 💡 使用示例

### Python (requests)

```python
import requests
import json

url = "http://localhost:8003/api/v1/agent/hardware/report"

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer <your_jwt_token>"
}

data = {
    "name": "My Agent Config",
    "dmr_config": {
        "revision": 1,
        "mainboard": {
            # ...硬件配置
        }
    },
    "updated_by": "agent@intel.com",
    "tags": ["alive", "checked"]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    print(f"Status: {result['data']['status']}")
    print(f"Message: {result['message']}")
else:
    error = response.json()
    print(f"Error: {error['message']}")
```

### cURL

```bash
curl -X POST http://localhost:8003/api/v1/agent/hardware/report \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{
    "name": "My Agent Config",
    "dmr_config": {
      "revision": 1,
      "mainboard": {
        "revision": 1,
        "plt_meta_data": {
          "platform": "DMR"
        }
      }
    }
  }'
```

## ⚠️ 注意事项

1. **必填字段验证**: 硬件模板中标记为 `required` 的字段必须提供，否则会返回 400 错误
2. **版本号对比**: 系统会自动对比 `dmr_config.revision` 字段，判断是否有版本号变化
3. **深度内容对比**: 系统会递归对比整个 `dmr_config` JSON，找出所有差异字段
4. **主机状态更新**: 硬件变更会自动更新 `host_rec` 表的 `appr_state=2` 和 `host_state=6`
5. **审批流程**: 硬件变更后需要管理员审批，审批通过后 `sync_state` 会更新为 2

## 📚 相关文档

- [微服务架构设计规范](mdc:.cursor/rules/microservice-architecture.mdc)
- [API设计规范](mdc:.cursor/rules/api-design-standards.mdc)
- [SQLAlchemy异步ORM规范](mdc:.cursor/rules/mariadb-database.mdc)

## 🔧 故障排查

### 问题1: 硬件模板未找到

**错误信息**: `未找到硬件模板配置`

**解决方案**: 
1. 检查 `sys_conf` 表是否存在 `conf_key='hw_temp'` 的记录
2. 确认记录的 `state_flag=0` 且 `del_flag=0`
3. 确认 `conf_json` 字段包含有效的硬件模板JSON

### 问题2: 缺少必填字段

**错误信息**: `缺少必填字段: mainboard.board.board_meta_data.host_ip`

**解决方案**:
1. 检查硬件模板，找到值为 `required` 的字段
2. 确保上报的 `dmr_config` 中包含所有必填字段

### 问题3: 数据库更新失败

**错误信息**: `更新硬件记录失败`

**解决方案**:
1. 检查数据库连接是否正常
2. 确认 `host_rec` 和 `host_hw_rec` 表结构正确
3. 查看服务日志获取详细错误信息

---

**最后更新**: 2025-01-30
**API版本**: v1
**服务**: host-service

