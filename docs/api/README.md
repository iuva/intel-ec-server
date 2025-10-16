# 微服务API文档汇总

**生成时间**: Wed Oct 15 19:14:34 CST 2025
**项目**: Intel EC 微服务系统
**最后更新**: 2025-10-15

## 📋 最新更新

### 🔧 API响应格式修复
- ✅ **OAuth2端点响应格式统一**: 移除外层`detail`字段，统一返回ErrorResponse格式
- ✅ **网关404响应优化**: 移除`available_endpoints`字段，避免信息泄露
- ✅ **异常处理中间件优化**: 修复日志格式化错误，确保响应格式一致性

### 📚 文档生成工具
- ✅ **自动化文档生成脚本**: `scripts/generate_docs.sh` 和 `scripts/dev_docs.sh`
- ✅ **OpenAPI规范导出**: 支持JSON格式规范下载
- ✅ **端点列表生成**: 自动生成Markdown格式的API端点文档

### 🔍 文档验证
- ✅ **响应格式验证**: 所有错误响应都符合ErrorResponse规范
- ✅ **认证流程验证**: OAuth2认证端点返回正确格式
- ✅ **网关路由验证**: 404响应不暴露内部端点信息

## 服务列表

### 网关服务 (gateway-service)

- **端口**: 8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **健康检查**: http://localhost:8000/health
- **监控指标**: http://localhost:8000/metrics

### 认证服务 (auth-service)

- **端口**: 8001
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json
- **健康检查**: http://localhost:8001/health
- **监控指标**: http://localhost:8001/metrics

### 管理服务 (admin-service)

- **端口**: 8002
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc
- **OpenAPI JSON**: http://localhost:8002/openapi.json
- **健康检查**: http://localhost:8002/health
- **监控指标**: http://localhost:8002/metrics

### 主机服务 (host-service)

- **端口**: 8003
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI JSON**: http://localhost:8003/openapi.json
- **健康检查**: http://localhost:8003/health
- **监控指标**: http://localhost:8003/metrics

## 文档文件

- `gateway-service-openapi.json` - 网关服务 OpenAPI 规范
- `gateway-service-endpoints.md` - 网关服务 端点列表
- `auth-service-openapi.json` - 认证服务 OpenAPI 规范
- `auth-service-endpoints.md` - 认证服务 端点列表
- `admin-service-openapi.json` - 管理服务 OpenAPI 规范
- `admin-service-endpoints.md` - 管理服务 端点列表
- `host-service-openapi.json` - 主机服务 OpenAPI 规范
- `host-service-endpoints.md` - 主机服务 端点列表

## 使用说明

1. 确保所有微服务正在运行
2. 在浏览器中访问对应服务的 /docs 路径查看交互式文档
3. 使用 /openapi.json 端点下载 API 规范
4. 使用生成的文档进行客户端代码生成或 API 测试

## 🔍 API响应格式验证

### 错误响应格式验证

所有API错误响应都应符合以下格式：

```json
{
  "code": 401,
  "message": "认证失败",
  "error_code": "UNAUTHORIZED",
  "details": null,
  "timestamp": "2025-10-15T10:00:00Z"
}
```

**禁止的格式**:
```json
{
  "detail": {
    "code": 401,
    "message": "认证失败"
  }
}
```

### 验证命令

#### OAuth2认证端点
```bash
# 错误的客户端凭据 - 应返回统一错误格式
curl -X POST http://localhost:8001/api/v1/oauth2/admin/token \
  -H "Authorization: Basic d3JvbmdfY2xpZW50Ondyb25nX3NlY3JldA==" \
  -d "grant_type=***REMOVED***word&username=admin&***REMOVED***word=wrong"

# 缺少必需参数 - 应返回统一错误格式
curl -X POST http://localhost:8001/api/v1/oauth2/admin/token \
  -H "Authorization: Basic YWRtaW5fY2xpZW50OmFkbWluX3NlY3JldA==" \
  -d "grant_type=***REMOVED***word"
```

#### 网关404响应
```bash
# 不存在的端点 - 不应包含available_endpoints字段
curl http://localhost:8000/api/v1/nonexistent
```

#### 认证服务404响应
```bash
# 不存在的认证端点
curl http://localhost:8001/api/v1/auth/nonexistent
```

### 验证结果

✅ **正确响应格式**: 直接返回ErrorResponse结构，无外层detail包装
✅ **网关404响应**: 只包含method和path字段，不泄露内部端点信息
✅ **OAuth2端点**: HTTP Basic认证失败时返回统一错误格式
✅ **Form参数验证**: 缺少必需Form参数时返回统一ErrorResponse格式，不再返回Pydantic验证错误

## 📋 响应格式规范

### ErrorResponse模型
- `code`: HTTP状态码 (int)
- `message`: 错误消息 (str)
- `error_code`: 错误类型编码 (str)
- `details`: 附加信息 (Optional[Dict])
- `timestamp`: 响应时间 (str)

### SuccessResponse模型
- `code`: HTTP状态码 (int, 默认200)
- `message`: 成功消息 (str, 默认"操作成功")
- `data`: 响应数据 (Any)
- `timestamp`: 响应时间 (str)
- `request_id`: 请求ID (str)
