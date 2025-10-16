# 共享模块更新日志

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
