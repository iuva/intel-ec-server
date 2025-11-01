# Shared Utils 通用工具模块

## 📋 概述

本模块提供项目中常用的通用工具类和辅助函数，所有微服务都可以复用这些工具。

## 🔧 可用工具

### 1. JSONComparator - JSON深度对比工具

**位置**: `shared/utils/json_comparator.py`

**功能**: 深度对比两个JSON对象，识别新增、删除、修改的字段

**使用场景**:
- 硬件配置变更检测
- 用户数据变更审计
- 系统配置差异分析
- 版本控制和变更管理

#### 基础使用

```python
from shared.utils.json_comparator import JSONComparator

# 创建对比器实例
comparator = JSONComparator()

# 对比两个JSON对象
previous = {
    "name": "John",
    "age": 30,
    "address": {
        "city": "Shanghai",
        "country": "China"
    },
    "tags": ["admin", "user"]
}

current = {
    "name": "John",
    "age": 31,
    "address": {
        "city": "Beijing",  # 修改
        "country": "China"
    },
    "tags": ["admin", "user", "developer"],  # 新增
    "email": "john@example.com"  # 新增字段
}

# 执行对比
diff = comparator.compare(previous, current)

# 查看差异
print(diff)
# 输出:
# {
#     "age": {"type": "modified", "previous": 30, "current": 31},
#     "address.city": {"type": "modified", "previous": "Shanghai", "current": "Beijing"},
#     "tags.length": {"type": "modified", "previous": 2, "current": 3},
#     "tags[2]": {"type": "added", "previous": None, "current": "developer"},
#     "email": {"type": "added", "previous": None, "current": "john@example.com"}
# }
```

#### 检查差异类型

```python
# 检查是否有变化
if comparator.has_changes(diff):
    print("检测到变化！")

# 获取新增字段
added_fields = comparator.get_added_fields(diff)
print(f"新增字段: {added_fields}")  # ["email", "tags[2]"]

# 获取删除字段
removed_fields = comparator.get_removed_fields(diff)
print(f"删除字段: {removed_fields}")  # []

# 获取修改字段
modified_fields = comparator.get_modified_fields(diff)
print(f"修改字段: {modified_fields}")  # ["age", "address.city", "tags.length"]
```

#### 格式化差异摘要

```python
# 生成易读的差异摘要
summary = comparator.format_diff_summary(diff)
print(summary)
# 输出:
# 差异摘要:
# - 新增字段: 2 个
# - 删除字段: 0 个
# - 修改字段: 3 个
# - 总计: 5 处差异
```

#### 在服务中使用

```python
# services/your-service/app/services/your_service.py
from shared.utils.json_comparator import JSONComparator

class YourService:
    """你的服务类"""

    def __init__(self):
        """初始化服务"""
        # 初始化JSON对比工具
        self.json_comparator = JSONComparator()

    async def detect_config_changes(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测配置变更

        Args:
            old_config: 旧配置
            new_config: 新配置

        Returns:
            变更详情
        """
        # 使用对比工具
        diff = self.json_comparator.compare(old_config, new_config)

        # 检查是否有变化
        if not self.json_comparator.has_changes(diff):
            return {"has_changes": False}

        # 分析变化类型
        return {
            "has_changes": True,
            "added": self.json_comparator.get_added_fields(diff),
            "removed": self.json_comparator.get_removed_fields(diff),
            "modified": self.json_comparator.get_modified_fields(diff),
            "summary": self.json_comparator.format_diff_summary(diff),
            "details": diff
        }
```

#### 差异对象结构

对比结果返回的差异字典格式：

```python
{
    "字段路径": {
        "type": "added" | "removed" | "modified",
        "previous": 旧值,
        "current": 新值
    }
}
```

**字段路径格式**:
- 顶层字段: `"field_name"`
- 嵌套字段: `"parent.child.grandchild"`
- 数组元素: `"array[0]"`, `"array[1]"`
- 数组长度: `"array.length"`

**差异类型**:
- `added`: 新增字段
- `removed`: 删除字段
- `modified`: 修改字段

#### 复杂嵌套示例

```python
# 复杂的嵌套JSON对比
previous = {
    "users": [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"}
    ],
    "settings": {
        "theme": "dark",
        "notifications": {
            "email": True,
            "sms": False
        }
    }
}

current = {
    "users": [
        {"id": 1, "name": "Alice", "role": "super_admin"},  # 修改
        {"id": 2, "name": "Bob", "role": "user"},
        {"id": 3, "name": "Charlie", "role": "user"}  # 新增
    ],
    "settings": {
        "theme": "light",  # 修改
        "notifications": {
            "email": True,
            "sms": True,  # 修改
            "push": True  # 新增
        }
    }
}

diff = comparator.compare(previous, current)

# 差异结果:
# {
#     "users.length": {"type": "modified", "previous": 2, "current": 3},
#     "users[0].role": {"type": "modified", "previous": "admin", "current": "super_admin"},
#     "users[2]": {"type": "added", "previous": None, "current": {"id": 3, "name": "Charlie", "role": "user"}},
#     "settings.theme": {"type": "modified", "previous": "dark", "current": "light"},
#     "settings.notifications.sms": {"type": "modified", "previous": False, "current": True},
#     "settings.notifications.push": {"type": "added", "previous": None, "current": True}
# }
```

### API参考

#### JSONComparator类

| 方法 | 参数 | 返回值 | 说明 |
|---|---|---|---|
| `compare(previous, current, path)` | `previous: Dict`, `current: Dict`, `path: str = ""` | `Dict[str, Any]` | 对比两个JSON对象 |
| `has_changes(diff)` | `diff: Dict` | `bool` | 检查是否存在差异 |
| `get_added_fields(diff)` | `diff: Dict` | `List[str]` | 获取新增字段列表 |
| `get_removed_fields(diff)` | `diff: Dict` | `List[str]` | 获取删除字段列表 |
| `get_modified_fields(diff)` | `diff: Dict` | `List[str]` | 获取修改字段列表 |
| `format_diff_summary(diff)` | `diff: Dict` | `str` | 格式化差异摘要 |

#### 常量

| 常量 | 值 | 说明 |
|---|---|---|
| `DIFF_TYPE_ADDED` | `"added"` | 新增字段类型 |
| `DIFF_TYPE_REMOVED` | `"removed"` | 删除字段类型 |
| `DIFF_TYPE_MODIFIED` | `"modified"` | 修改字段类型 |

## 🚀 性能考虑

### 时间复杂度
- 对比字典: O(n) 其中 n 是字段总数
- 对比数组: O(m) 其中 m 是数组长度
- 递归嵌套: O(n * d) 其中 d 是嵌套深度

### 内存使用
- 差异字典大小与变更数量成正比
- 建议对非常大的JSON（> 10MB）进行分批对比

## 📝 最佳实践

### 1. 版本控制集成

```python
async def save_config_with_diff(
    self,
    config_id: str,
    new_config: Dict[str, Any]
) -> Dict[str, Any]:
    """保存配置并记录变更"""
    # 获取旧配置
    old_config = await self.get_config(config_id)

    # 对比变更
    diff = self.json_comparator.compare(old_config, new_config)

    # 保存配置
    await self.save_config(config_id, new_config)

    # 记录变更历史
    if self.json_comparator.has_changes(diff):
        await self.save_change_history(config_id, diff)

    return {
        "config_id": config_id,
        "has_changes": self.json_comparator.has_changes(diff),
        "diff_summary": self.json_comparator.format_diff_summary(diff)
    }
```

### 2. 审计日志

```python
async def update_with_audit(
    self,
    resource_id: str,
    updates: Dict[str, Any],
    operator_id: str
) -> Dict[str, Any]:
    """更新资源并记录审计日志"""
    # 获取当前数据
    current = await self.get_resource(resource_id)

    # 应用更新
    updated = {**current, **updates}

    # 对比变更
    diff = self.json_comparator.compare(current, updated)

    # 记录审计日志
    if self.json_comparator.has_changes(diff):
        await self.log_audit(
            resource_id=resource_id,
            operator_id=operator_id,
            changes={
                "added": self.json_comparator.get_added_fields(diff),
                "removed": self.json_comparator.get_removed_fields(diff),
                "modified": self.json_comparator.get_modified_fields(diff),
                "details": diff
            }
        )

    # 保存更新
    await self.save_resource(resource_id, updated)

    return updated
```

### 3. 变更通知

```python
async def update_and_notify(
    self,
    config: Dict[str, Any],
    subscribers: List[str]
) -> None:
    """更新配置并通知订阅者"""
    # 获取旧配置
    old_config = await self.get_config()

    # 对比变更
    diff = self.json_comparator.compare(old_config, config)

    if not self.json_comparator.has_changes(diff):
        return

    # 保存新配置
    await self.save_config(config)

    # 通知订阅者
    notification = {
        "type": "config_changed",
        "summary": self.json_comparator.format_diff_summary(diff),
        "changed_fields": {
            "added": self.json_comparator.get_added_fields(diff),
            "removed": self.json_comparator.get_removed_fields(diff),
            "modified": self.json_comparator.get_modified_fields(diff)
        }
    }

    for subscriber in subscribers:
        await self.send_notification(subscriber, notification)
```

## 🔗 相关文档

- [Agent硬件上报API文档](../../services/host-service/docs/AGENT_HARDWARE_REPORT_API.md)
- [雪花ID迁移文档](../../docs/SNOWFLAKE_ID_MIGRATION.md)
- [项目README](../../README.md)

## 📊 使用统计

### 当前使用位置

- `services/host-service/app/services/agent_hardware_service.py` - Agent硬件变更检测

### 计划集成

- [ ] 用户配置变更检测
- [ ] 系统设置审计
- [ ] 数据同步差异分析

## 🛠️ 新增工具类

### 2. TokenExtractor - Token 提取和验证工具

**位置**: `shared/utils/token_extractor.py`

**功能**: 从 HTTP Request 中提取 JWT token 并调用 auth-service 验证

**使用场景**:
- HTTP API 认证依赖注入
- Agent/设备认证
- 用户认证
- Token 有效性验证

#### 基础使用

```python
from shared.utils.token_extractor import get_token_extractor

# 获取提取器实例
extractor = get_token_extractor()

# 方式1：从 Request 中提取 token
token = extractor.extract_token_from_request(request)

# 方式2：验证 token
is_valid, payload = await extractor.verify_token(token)
if is_valid:
    user_id = payload["user_id"]
    username = payload["username"]

# 方式3：一步到位（提取 + 验证）
is_valid, user_info = await extractor.extract_and_verify(request)
if is_valid:
    host_id = user_info["user_id"]
```

#### 在依赖注入中使用

```python
from fastapi import Request, HTTPException, Depends
from shared.utils.token_extractor import get_token_extractor
from typing import Dict, Any

async def get_current_agent(request: Request) -> Dict[str, Any]:
    """获取当前 Agent 信息（依赖注入）"""
    extractor = get_token_extractor()
    is_valid, user_info = await extractor.extract_and_verify(request)
    
    if not is_valid or not user_info:
        raise HTTPException(status_code=401, detail="认证失败")
    
    return {
        "host_id": user_info["user_id"],
        "username": user_info["username"],
        "user_type": user_info["user_type"],
    }

# 在 API 端点中使用
@router.post("/hardware/report")
async def report_hardware(
    agent_info: Dict[str, Any] = Depends(get_current_agent)
):
    host_id = agent_info["host_id"]
    # ... 业务逻辑
```

#### Token 提取方式

TokenExtractor 支持以下 token 提取方式（按优先级）：

1. **Authorization 头**（推荐）:
   ```http
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

2. **查询参数**（兼容性）:
   ```
   GET /api/v1/resource?token=eyJhbGciOiJIUzI1NiIs...
   ```

3. **自定义头**（兼容性）:
   ```http
   X-Token: eyJhbGciOiJIUzI1NiIs...
   ```

#### API 参考

| 方法 | 参数 | 返回值 | 说明 |
|---|---|---|---|
| `extract_token_from_request(request)` | `request: Request` | `Optional[str]` | 从 HTTP Request 中提取 token |
| `verify_token(token, timeout)` | `token: str, timeout: float=10.0` | `Tuple[bool, Optional[Dict]]` | 调用 auth-service 验证 token |
| `extract_and_verify(request)` | `request: Request` | `Tuple[bool, Optional[Dict]]` | 提取并验证 token（一步到位） |

#### 返回的用户信息结构

```python
{
    "user_id": "123",          # 用户/设备ID
    "username": "agent_001",   # 用户名
    "user_type": "device",     # 用户类型（"user", "device", "admin"）
    "permissions": [...],      # 权限列表
    "roles": [...],            # 角色列表
    "mg_id": "456",           # 管理组ID（如果有）
}
```

#### 使用场景对比

| 场景 | 使用方法 | 说明 |
|---|---|---|
| **FastAPI 依赖注入** | `get_current_agent()` | 推荐方式，自动验证和提取 |
| **手动验证** | `extractor.extract_and_verify()` | 需要自定义验证逻辑时 |
| **仅提取 token** | `extractor.extract_token_from_request()` | 需要手动处理 token 时 |
| **仅验证 token** | `extractor.verify_token()` | 已有 token，只需验证 |

### 3. TemplateValidator - 模板字段验证器

**位置**: `shared/utils/template_validator.py`

**功能**: 递归验证数据是否符合模板定义的必填字段要求

**使用场景**:
- Agent硬件信息格式验证
- API请求数据验证
- 配置文件验证

#### 基础使用

```python
from shared.utils.template_validator import TemplateValidator

# 创建验证器实例
validator = TemplateValidator()

# 定义模板（"required" 标记必填字段）
template = {
    "name": "required",
    "email": "required",
    "age": "optional",
    "address": {
        "city": "required",
        "street": "optional"
    }
}

# 验证数据
data = {
    "name": "John",
    "age": 30,
    "address": {
        "city": "Beijing"
    }
}

try:
    validator.validate_required_fields(data, template)
    print("验证通过")
except BusinessError as e:
    print(f"验证失败: {e.message}")
    # 输出: 验证失败: 缺少必填字段: email
```

#### 在服务中使用

```python
class AgentHardwareService:
    """Agent硬件信息上报服务"""

    def __init__(self):
        """初始化服务"""
        # 初始化模板验证器
        self.template_validator = TemplateValidator()

    async def validate_hardware_data(
        self, 
        hardware_data: Dict[str, Any], 
        template: Dict[str, Any]
    ) -> None:
        """验证硬件数据格式"""
        # 使用验证器
        self.template_validator.validate_required_fields(hardware_data, template)
```

**API参考**:

| 方法 | 参数 | 返回值 | 说明 |
|---|---|---|---|
| `validate_required_fields(data, template)` | `data: Dict`, `template: Dict` | `None` | 验证数据中的必填字段，失败抛出BusinessError |

### 3. PaginationParams & PaginationResponse - 分页工具类

**位置**: `shared/utils/pagination.py`

**功能**: 提供统一的分页参数处理和分页响应格式

**使用场景**:
- 用户列表分页查询
- 数据列表分页显示
- 游标分页（避免并发状态污染）

#### 传统分页

```python
from shared.utils.pagination import PaginationParams, PaginationResponse

# 分页参数
params = PaginationParams(page=2, page_size=20)
print(params.offset)  # 输出: 20
print(params.limit)   # 输出: 20

# 分页响应
response = PaginationResponse(page=2, page_size=20, total=55)
print(response.total_pages)  # 输出: 3
print(response.has_next)     # 输出: True
print(response.has_prev)     # 输出: True
```

#### 游标分页

```python
from shared.utils.pagination import CursorPaginationParams, CursorPaginationResponse

# 游标分页参数
params = CursorPaginationParams(page_size=20, last_id=100)

# 游标分页响应
response = CursorPaginationResponse(
    page_size=20,
    total=15,
    has_next=False,
    last_id=115
)
```

#### 在服务中使用

```python
class UserService:
    """用户管理服务"""

    async def list_users(
        self, 
        page: int = 1, 
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取用户列表（分页）"""
        # 创建分页参数
        pagination = PaginationParams(page=page, page_size=page_size)
        
        # 使用offset和limit进行查询
        stmt = select(User).offset(pagination.offset).limit(pagination.limit)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        # 获取总数
        total = await self.count_users()
        
        # 创建分页响应
        response = PaginationResponse(
            page=page, 
            page_size=page_size, 
            total=total
        )
        
        return {
            "users": users,
            "pagination": {
                "page": response.page,
                "page_size": response.page_size,
                "total": response.total,
                "total_pages": response.total_pages,
                "has_next": response.has_next,
                "has_prev": response.has_prev
            }
        }
```

**API参考**:

#### PaginationParams类

| 属性/方法 | 类型 | 说明 |
|---|---|---|
| `page` | `int` | 页码（从1开始） |
| `page_size` | `int` | 每页大小（1-100） |
| `offset` | `property → int` | 数据库查询偏移量 |
| `limit` | `property → int` | 每页数量 |

#### PaginationResponse类

| 属性/方法 | 类型 | 说明 |
|---|---|---|
| `page` | `int` | 当前页码 |
| `page_size` | `int` | 每页大小 |
| `total` | `int` | 总记录数 |
| `total_pages` | `property → int` | 总页数 |
| `has_next` | `property → bool` | 是否有下一页 |
| `has_prev` | `property → bool` | 是否有上一页 |

## 📈 代码复用效果

通过使用共享工具类，我们实现了：

- ✅ **代码行数减少**: 200+ 行重复代码被移除
- ✅ **维护成本降低**: 修改逻辑只需更新工具类
- ✅ **一致性保障**: 统一的业务逻辑实现
- ✅ **测试覆盖**: 工具类更容易编写单元测试

---

**最后更新**: 2025-10-15
**版本**: 1.3.0
**维护者**: AI Assistant

