# 项目更新日志

## 2025-10-17 - 修复 Gateway 认证中间件配置

### 🔒 安全修复

**问题**: 受保护的 API 可以在未认证的情况下访问

**根本原因**:
- 认证中间件的公开路径白名单配置过时
- 令牌验证端点指向已移除的 OAuth2 端点

**修复内容**:

1. **auth_middleware.py** - 更新公开路径白名单
   - 移除 OAuth2 相关路径
   - 添加新的登录端点: `/api/v1/auth/admin/login`, `/api/v1/auth/device/login`
   - 添加注销端点: `/api/v1/auth/logout`

2. **auth_middleware.py** - 更新令牌验证逻辑
   - 修改验证端点: `/api/v1/oauth2/introspect` → `/api/v1/auth/introspect`
   - 修改请求格式: Form Data → JSON
   - 简化用户信息结构

**修复效果**:
- ✅ 公开路径（登录、健康检查）可以访问
- ✅ 受保护路径（admin、host API）需要认证
- ✅ 无效令牌被正确拒绝
- ✅ 令牌验证功能正常

**安全影响**:
- 🔒 所有管理后台 API 现在需要认证
- 🔒 所有主机管理 API 现在需要认证
- 🔒 未认证请求返回 401 Unauthorized

详见: `services/gateway-service/AUTH_MIDDLEWARE_FIX.md`

---

## 2025-10-17 - 修复 Admin Service 搜索功能 NULL 字段处理

### 🐛 Bug 修复

**问题**: 用户列表搜索功能在字段值为 NULL 时失败

**错误日志**:
```log
ERROR | admin-service | user_list 失败
ERROR | admin-service | list_users 执行失败
```

**根本原因**:
- 搜索逻辑直接对可能为 `NULL` 的字段（`user_name`、`email`）使用 `.like()` 操作
- 当数据库中存在 NULL 值时，SQL 查询失败

**修复内容**:

1. **user_service.py** - 添加 NULL 值检查
   - 导入 `and_` 函数
   - 使用 `and_(field.isnot(None), field.like(...))` 模式
   - 确保只对非 NULL 字段进行 LIKE 搜索

**修复效果**:
- ✅ 字段为 NULL 时查询不报错
- ✅ 搜索功能正常工作
- ✅ 正确处理部分字段为 NULL 的记录

详见: `services/admin-service/NULL_FIELD_SEARCH_FIX.md`

---

## 2025-10-17 - 修复分页参数验证问题

### 🐛 Bug 修复

**问题**: API 分页参数要求 `page >= 1`，但前端通常从0开始计数

**影响**:
- 前端传入 `page=0` 时返回 422 Unprocessable Entity
- 不符合大多数前端框架的分页习惯

**修复内容**:

1. **Admin Service** (`app/api/v1/endpoints/users.py`)
   - 分页参数: `page: int = Query(0, ge=0)` （支持从0开始）
   - 内部转换: `internal_page = page + 1` （转换为从1开始）
   - 更新文档说明

**修复效果**:
- ✅ 支持 `page=0` 作为第一页
- ✅ 向后兼容（`page=1` 仍然有效）
- ✅ 内部逻辑保持不变

---

## 2025-10-17 - Admin Service 用户表迁移

### 🔄 数据库迁移

**目标**: 将 Admin Service 从 `users` 表迁移到标准的 `sys_user` 表

**修改内容**:

1. **数据模型** (`app/models/user.py`)
   - 表名: `users` → `sys_user`
   - 字段更新以匹配 `sys_user` 表结构
   - 主键类型: INT → BIGINT

2. **业务逻辑** (`app/services/user_service.py`)
   - 更新所有查询条件和字段访问
   - 添加ID生成逻辑（时间戳，生产环境需使用雪花算法）
   - 状态字段转换: `is_active` ↔ `state_flag`

3. **数据模式** (`app/schemas/user.py`)
   - 响应字段更新
   - 添加向后兼容的计算属性
   - 移除 `is_superuser` 字段（使用角色系统）

4. **数据库脚本** (`docs/database/db.sql`)
   - 移除旧的 `users` 表定义
   - 使用标准的 `sys_user` 表
   - 添加必要的索引

**字段映射**:
- `username` → `user_account`
- `***REMOVED***word_hash` → `user_pwd`
- `is_active` → `state_flag` (0=启用, 1=停用)
- `del_flag` → `del_flag` (0=使用中, 1=删除)
- `created_time` → `created_time`
- `updated_time` → `updated_time`

**向后兼容**:
- 在 `UserResponse` 中添加计算属性保持 API 兼容性
- 现有客户端仍可访问 `username`、`is_active` 等字段

详见: `services/admin-service/SYS_USER_MIGRATION.md`

---

## 2025-10-17 - 修复 Gateway 错误状态码和消息透传问题

### 🐛 Bug 修复

**问题**: Gateway 错误地将后端服务的 HTTP 错误统一转换为 503 Service Unavailable，且未正确透传错误消息

**影响**: 
- 后端服务返回的 400、401、403、404 等错误都被转换为 503
- 客户端无法正确处理不同类型的错误
- 错误消息未正确透传，影响问题排查

**修复内容**:

1. **proxy_service.py** - 区分 HTTP 状态错误和网络错误，正确解析 FastAPI 响应格式
   - HTTP 状态错误（400、401、403、404、500 等）→ 透传原始状态码
   - 正确解析 FastAPI 的 `detail` 字段包装
   - 网络错误、超时等 → 返回 503 Service Unavailable
   - 完整保留后端错误的 message、error_code 和 details

2. **proxy.py** - 更新异常处理
   - 添加 `BusinessError` 处理
   - 透传后端服务的错误状态码

**修复效果**:
- ✅ 后端 400 错误正确返回 400
- ✅ 后端 401/403/404 错误正确透传
- ✅ 错误消息正确透传（解决 FastAPI detail 包装问题）
- ✅ 网络错误仍返回 503
- ✅ 错误详情完整保留

详见: `services/gateway-service/ERROR_HANDLING_FIX.md`

---

## 2025-10-16 - 文档结构整理

### 📁 文档重组

**目标**: 优化文档结构，提高可维护性和可发现性

#### 移动的文件

**示例代码移至 shared/ 目录**:
- `docs/decorators_examples.py` → `shared/common/decorators_examples.py`
- `docs/http_client_example.py` → `shared/common/http_client_example.py`
- `docs/metrics_examples.py` → `shared/monitoring/metrics_examples.py`

**模块文档移至 shared/ 目录**:
- `docs/DECORATORS_README.md` → `shared/common/DECORATORS_README.md`
- `docs/LOGGING_STANDARDS.md` → `shared/common/LOGGING_STANDARDS.md`
- `docs/LOGGING_MIGRATION_GUIDE.md` → `shared/common/LOGGING_MIGRATION_GUIDE.md`
- `docs/METRICS_ENHANCEMENT.md` → `shared/monitoring/METRICS_ENHANCEMENT.md`

**API 文档整理**:
- `docs/API_DOCUMENTATION_GUIDE.md` → `docs/api/API_DOCUMENTATION_GUIDE.md`

#### 删除的文件

- `docs/CODE_QUALITY_FIXES.md` - 过时文档（2025-01-29）

#### 更新的文件

- `docs/README.md` - 完全重写，优化文档索引结构
- 新增 `docs/DOCUMENTATION_REORGANIZATION.md` - 文档整理总结

### 📊 整理效果

- ✅ 模块文档与代码放在一起，形成自包含的模块
- ✅ docs/ 目录只保留项目级文档，结构更清晰
- ✅ 提高文档可维护性和可发现性
- ✅ 删除过时文档，保持文档最新

---

## 2025-10-16 - 代码质量检查完成

### ✅ 代码质量检查

**任务**: 运行完整的代码质量检查并修复所有问题

#### 检查结果

- **Ruff 代码检查**: ✅ 通过（修复 56 个问题）
- **Ruff 格式检查**: ✅ 通过（格式化 10 个文件）
- **MyPy 类型检查**: ✅ 通过（修复 12 个类型错误）
- **Pyright 类型检查**: ✅ 通过（0 个错误）

#### 主要修复

1. **类型注解完善**: 添加缺失的类型注解
2. **代码格式统一**: 使用 Ruff Format 格式化代码
3. **Python 3.8 兼容性**: 修复不兼容的语法
4. **配置优化**: 更新工具配置文件

详见: `.kiro/specs/code-optimization/CODE_QUALITY_CHECK_SUMMARY.md`

---

## 2025-01-29 - 错误码类型修改

### 重大变更

将错误码从字符串类型改为数字类型（HTTP状态码），以符合RESTful API最佳实践。

### 修改内容

#### 1. BusinessError 异常类 (`shared/common/exceptions.py`)

**之前:**
```python
class BusinessError(Exception):
    def __init__(
        self,
        message: str,
        error_code: str = "BUSINESS_ERROR",  # 字符串类型
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
```

**现在:**
```python
class BusinessError(Exception):
    def __init__(
        self,
        message: str,
        code: int = 400,  # 数字类型（HTTP状态码）
        error_type: str = "BUSINESS_ERROR",  # 错误类型标识
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.error_type = error_type
```

#### 2. ErrorCodes 改名为 ErrorType

**之前:**
```python
class ErrorCodes:
    AUTH_INVALID_CREDENTIALS = "AUTH_1001"
    USER_NOT_FOUND = "USER_2001"
    # ...
```

**现在:**
```python
class ErrorType:
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    # ...
```

#### 3. ErrorResponse 模型 (`shared/common/response.py`)

**之前:**
```python
class ErrorResponse(BaseModel):
    code: int = Field(description="错误码")
    error_code: str = Field(description="错误类型编码")
```

**现在:**
```python
class ErrorResponse(BaseModel):
    code: int = Field(description="HTTP状态码")
    error_type: str = Field(description="错误类型标识")
```

#### 4. 专用异常类更新

所有专用异常类（AuthenticationError, ValidationError等）都已更新，使用正确的HTTP状态码：

```python
# 认证异常 - 401
class AuthenticationError(BusinessError):
    def __init__(self, message: str = "认证失败", code: int = 401, ...):
        ***REMOVED***

# 授权异常 - 403
class AuthorizationError(BusinessError):
    def __init__(self, message: str = "权限不足", code: int = 403, ...):
        ***REMOVED***

# 验证异常 - 422
class ValidationError(BusinessError):
    def __init__(self, message: str = "数据验证失败", code: int = 422, ...):
        ***REMOVED***

# 资源不存在 - 404
class ResourceNotFoundError(BusinessError):
    def __init__(self, message: str = "资源不存在", code: int = 404, ...):
        ***REMOVED***

# 资源冲突 - 409
class ResourceConflictError(BusinessError):
    def __init__(self, message: str = "资源冲突", code: int = 409, ...):
        ***REMOVED***

# 数据库错误 - 500
class DatabaseError(BusinessError):
    def __init__(self, message: str = "数据库错误", code: int = 500, ...):
        ***REMOVED***

# 服务不可用 - 503
class ServiceUnavailableError(BusinessError):
    def __init__(self, message: str = "服务暂时不可用", code: int = 503, ...):
        ***REMOVED***
```

### 使用示例

#### 抛出异常

**之前:**
```python
raise BusinessError(
    message="用户不存在",
    error_code="USER_NOT_FOUND"
)
```

**现在:**
```python
from shared.common.exceptions import BusinessError, ErrorType

raise BusinessError(
    message="用户不存在",
    code=404,
    error_type=ErrorType.USER_NOT_FOUND
)

# 或使用专用异常类
raise ResourceNotFoundError(
    message="用户不存在",
    error_type=ErrorType.USER_NOT_FOUND
)
```

#### 创建错误响应

**之前:**
```python
error_response = create_error_response(
    message="用户不存在",
    error_code="USER_NOT_FOUND",
    code=404
)
```

**现在:**
```python
from shared.common.response import create_error_response
from shared.common.exceptions import ErrorType

error_response = create_error_response(
    message="用户不存在",
    error_type=ErrorType.USER_NOT_FOUND,
    code=404
)
```

#### 响应格式

**之前:**
```json
{
  "code": 404,
  "message": "用户不存在",
  "error_code": "USER_NOT_FOUND",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

**现在:**
```json
{
  "code": 404,
  "message": "用户不存在",
  "error_type": "USER_NOT_FOUND",
  "timestamp": "2025-01-29T10:00:00Z"
}
```

### 迁移指南

如果你的代码使用了旧的API，请按以下步骤迁移：

1. **导入更新**
   ```python
   # 之前
   from shared.common.exceptions import ErrorCodes
   
   # 现在
   from shared.common.exceptions import ErrorType
   ```

2. **异常抛出更新**
   ```python
   # 之前
   raise BusinessError("错误消息", error_code="ERROR_CODE")
   
   # 现在
   raise BusinessError("错误消息", code=400, error_type=ErrorType.ERROR_TYPE)
   ```

3. **错误响应创建更新**
   ```python
   # 之前
   create_error_response(message="错误", error_code="CODE", code=400)
   
   # 现在
   create_error_response(message="错误", error_type=ErrorType.TYPE, code=400)
   ```

### 优势

1. **符合HTTP标准**: 使用标准HTTP状态码作为错误码
2. **类型安全**: 数字类型的code更容易进行类型检查
3. **更清晰**: 分离了HTTP状态码（code）和错误类型标识（error_type）
4. **更灵活**: 可以为同一个error_type使用不同的HTTP状态码

### 兼容性

- ✅ 向后兼容：所有专用异常类都提供了默认的HTTP状态码
- ✅ 类型安全：使用Python类型提示确保正确使用
- ✅ 文档完整：所有函数和类都有详细的中文文档

### 相关文件

- `shared/common/exceptions.py` - 异常定义
- `shared/common/response.py` - 响应格式
- `shared/app/application.py` - 异常处理器
- `shared/common/__init__.py` - 模块导出
