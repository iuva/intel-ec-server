# 接口文档访问指南

## 🎯 微服务文档端点

### Gateway Service (端口 8000)
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Auth Service (端口 8001)
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

### Admin Service (端口 8002)
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc
- **OpenAPI JSON**: http://localhost:8002/openapi.json

### Host Service (端口 8003)
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI JSON**: http://localhost:8003/openapi.json

## 🚀 启动服务并访问文档

### 1. 启动单个服务
```bash
# 启动网关服务
cd services/gateway-service && python -m app.main

# 启动认证服务
cd services/auth-service && python -m app.main

# 启动管理服务
cd services/admin-service && python -m app.main

# 启动主机服务
cd services/host-service && python -m app.main
```

### 2. 启动所有服务 (Docker Compose)
```bash
# 在项目根目录
docker-compose up -d gateway-service auth-service admin-service host-service
```

### 3. 访问文档
启动服务后，在浏览器中访问相应端口的 /docs 路径即可查看 Swagger UI 文档。

## 📋 文档特性

### 自动生成特性
- ✅ 基于 FastAPI 自动生成
- ✅ 实时同步代码变更
- ✅ 包含请求/响应示例
- ✅ 支持在线测试接口

### 统一格式
- ✅ 标准 OpenAPI 3.0 规范
- ✅ 统一的响应格式
- ✅ 错误响应文档化

### 安全特性
- ✅ JWT 认证集成
- ✅ 权限检查说明
- ✅ 请求头示例

## 🛠️ 生成静态文档

### 1. 使用脚本生成
```bash
# 生成所有服务的 OpenAPI 规范
./scripts/generate_docs.sh
```

### 2. 手动生成
```bash
# 获取服务的 OpenAPI JSON
curl http://localhost:8001/openapi.json > auth-service-api.json
curl http://localhost:8002/openapi.json > admin-service-api.json

# 使用 Swagger Codegen 生成客户端代码
# JavaScript 客户端
swagger-codegen generate -i auth-service-api.json -l javascript -o client-js

# Python 客户端  
swagger-codegen generate -i auth-service-api.json -l python -o client-py

# TypeScript 客户端
swagger-codegen generate -i auth-service-api.json -l typescript-angular -o client-ts
```

## 📚 文档维护规范

### 端点文档要求
- ✅ 中文描述（函数docstring）
- ✅ 参数类型和描述
- ✅ 响应格式说明
- ✅ 错误情况说明
- ✅ 使用示例

### 版本管理
- ✅ API 版本控制（v1）
- ✅ 向后兼容性保证
- ✅ 版本变更日志

### 更新流程
1. 修改代码中的 docstring
2. 更新响应模型的 Field 描述
3. 重启服务验证文档
4. 提交代码时包含文档更新

## 🔍 故障排查

### 文档无法访问
1. 检查服务是否正常启动
2. 确认端口配置正确
3. 查看服务日志中的错误信息

### 文档内容不完整
1. 检查所有端点的 docstring
2. 验证响应模型的 Field 描述
3. 确认路由正确注册

### 认证问题
1. 某些端点可能需要认证
2. 使用 JWT token 进行测试
3. 检查认证中间件配置

---

**更新时间**: 2025-10-15
**适用版本**: FastAPI + OpenAPI 3.0
