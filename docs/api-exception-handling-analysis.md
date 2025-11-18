# API 异常处理统一性分析报告

## 📊 当前状态

### ✅ 已统一的方面

1. **错误响应格式统一**
   - 所有异常都使用 `ErrorResponse` 格式
   - 包含字段：`code`, `message`, `error_code`, `details`, `timestamp`, `request_id`, `locale`

2. **装饰器使用**
   - 大部分端点使用了 `@handle_api_errors` 装饰器
   - `@handle_api_errors` 自动将 `BusinessError` 转换为 `HTTPException`，并使用 `ErrorResponse` 格式

3. **全局异常处理器**
   - FastAPI 应用注册了全局异常处理器
   - 中间件提供了最后的异常处理防线

4. **成功响应格式统一**
   - 所有端点均返回 `Result[T]` 泛型响应
   - 成功响应字段固定为：`code`, `message`, `data`, `timestamp`, `locale`
   - `data` 必须承载所有业务数据，外层不再嵌套 `detail` 或其他结构

### ⚠️ 需要统一的问题

#### 1. `auth-service` 端点缺少 `@handle_api_errors` 装饰器

**问题**：
- `services/auth-service/app/api/v1/endpoints/auth.py` 中的所有端点都没有使用 `@handle_api_errors` 装饰器
- 手动处理异常，导致代码重复

**影响**：
- 代码重复
- 维护成本高
- 异常处理逻辑不一致

**解决方案**：
- 为所有端点添加 `@handle_api_errors` 装饰器
- 移除手动的异常处理代码
- 确保 `auth_service` 中的 `BusinessError` 设置了正确的 `http_status_code`

#### 2. `agent_report.py` 存在重复的异常处理

**问题**：
- `services/host-service/app/api/v1/endpoints/agent_report.py` 中的端点使用了 `@handle_api_errors` 装饰器
- 但函数内部还有手动的异常处理（`except BusinessError` 和 `except Exception`）

**影响**：
- 异常被处理两次（装饰器和手动处理）
- 可能导致日志重复记录
- 代码冗余

**解决方案**：
- 移除函数内部的异常处理代码
- 只依赖 `@handle_api_errors` 装饰器

#### 3. `auth_service` 中的认证错误缺少 `http_status_code`

**问题**：
- `auth_service.admin_login` 中抛出的 `AUTH_INVALID_CREDENTIALS` 错误没有设置 `http_status_code`
- 默认使用 400，但应该是 401

**影响**：
- HTTP 状态码不正确
- 客户端无法正确识别认证失败

**解决方案**：
- 在 `auth_service` 中为认证错误设置 `http_status_code=401`

## 🔧 修复建议

### 修复 1: 统一 `auth-service` 异常处理

1. 修复 `auth_service` 中的 `BusinessError`，添加 `http_status_code=401`：

```python
# services/auth-service/app/services/auth_service.py
raise BusinessError(
    message="用户名或密码错误",
    error_code="AUTH_INVALID_CREDENTIALS",
    http_status_code=401,  # ✅ 添加
)
```

2. 为 `auth.py` 的所有端点添加 `@handle_api_errors` 装饰器
3. 移除手动的异常处理代码

### 修复 2: 移除 `agent_report.py` 中的重复异常处理

移除函数内部的 `try-except` 块，只保留业务逻辑。

## 📋 检查清单

- [ ] 所有端点都使用 `@handle_api_errors` 装饰器
- [ ] 所有 `BusinessError` 都设置了正确的 `http_status_code`
- [ ] 没有重复的异常处理代码
- [ ] 所有异常都通过 `ErrorResponse` 格式返回
- [ ] 认证错误使用 401 状态码
- [ ] 授权错误使用 403 状态码
- [ ] 验证错误使用 422 状态码
- [ ] 系统错误使用 500 状态码

## 🎯 统一后的异常处理流程

```
1. 服务层抛出 BusinessError
   ↓
2. @handle_api_errors 装饰器捕获
   ↓
3. 转换为 HTTPException，使用 ErrorResponse 格式
   ↓
4. FastAPI 全局异常处理器处理
   ↓
5. 返回统一的错误响应
```

## 🧱 通用响应规则（更新）

1. **成功响应**：统一使用 `Result[T]`，`data` 字段承载实际业务数据，禁止再包装 `detail`。
2. **错误响应**：统一使用 `ErrorResponse`，字段包含 `code`, `message`, `error_code`, `details`, `timestamp`, `request_id`, `locale`。
3. **装饰器**：所有需要统一处理的端点必须使用 `@handle_api_errors`，避免函数内重复 `try/except`。
4. **状态码约定**：
   - 认证失败：401
   - 授权失败：403
   - 请求数据错误：400
   - 数据验证失败：422
   - 服务器错误：500
5. **多语言**：`message` 优先使用 `message_key` + `locale`，确保日志和响应均支持中英文。

## 📝 示例代码

### ✅ 正确的异常处理方式

```python
@router.post("/login", response_model=Result[LoginResponse])
@handle_api_errors  # ✅ 使用装饰器
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    locale: str = Depends(get_locale),
) -> Result[LoginResponse]:
    # ✅ 直接调用服务，不需要 try-except
    login_response = await auth_service.admin_login(login_data)
    
    return Result(
        code=200,
        message=t("success.login", locale=locale, default="登录成功"),
        data=login_response,
        locale=locale,
    )
```

### ❌ 错误的异常处理方式

```python
@router.post("/login", response_model=Result[LoginResponse])
@handle_api_errors  # ✅ 有装饰器
async def login(...):
    try:
        # 业务逻辑
        ...
    except BusinessError as e:  # ❌ 重复处理
        raise HTTPException(...)
    except Exception as e:  # ❌ 重复处理
        raise HTTPException(...)
```

