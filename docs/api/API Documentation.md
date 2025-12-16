---
title: API Documentation
language_tabs:
  - shell: Shell
  - http: HTTP
  - javascript: JavaScript
  - ruby: Ruby
  - python: Python
  - php: PHP
  - java: Java
  - go: Go
toc_footers: []
includes: []
search: true
code_clipboard: true
highlight_theme: darkula
headingLevel: 2
generator: "@tarslib/widdershins v4.0.30"
---

> ⚠️ **重要提示**: 本文档由工具自动生成，请勿手动编辑。
> 
> 如需更新文档内容，请修改代码中的API定义（FastAPI路由、Pydantic模型等），然后使用以下命令重新生成：
> 
> ```bash
> # 重新生成API文档
> ./scripts/generate_docs.sh
> ```
> 
> 更多信息请参考：[API参考文档](./API_REFERENCE.md)

# API Documentation

主机管理和WebSocket实时通信服务

Base URLs:

# Host-Service/浏览器插件-主机管理

<a id="opIdquery_available_hosts_api_v1_host_hosts_available_post"></a>

## POST 查询可用主机列表

POST /api/v1/host/hosts/available

查询可用的主机列表，支持游标分页

> Body 请求参数

```json
{
  "tc_id": "string",
  "cycle_name": "string",
  "user_name": "string",
  "page_size": 20,
  "last_id": "string"
}
```

### 请求参数

> **注意**: 本文档内容由工具自动生成，可能不完整。完整的API参考请查看 [API_REFERENCE.md](./API_REFERENCE.md) 或访问服务的 Swagger UI 文档。

---

**最后更新**: 自动生成  
**生成工具**: @tarslib/widdershins v4.0.30  
**完整文档**: [API_REFERENCE.md](./API_REFERENCE.md)
