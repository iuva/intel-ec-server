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

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[QueryAvailableHostsRequest](#schemaqueryavailablehostsrequest)| 是 | QueryAvailableHostsRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_rec_id": "string",
        "hardware_id": "string",
        "user_name": "string",
        "host_ip": "string",
        "appr_state": 0,
        "host_state": 0
      }
    ],
    "total": 0,
    "page_size": 0,
    "has_next": true,
    "last_id": "string"
  },
  "timestamp": "string",
  "locale": "string"
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数无效",
  "error_code": "INVALID_PARAMS"
}
```

> 405 Response

```json
{
  "code": 405,
  "message": "此接口仅支持 POST 方法，请使用 POST 请求",
  "error_code": "METHOD_NOT_ALLOWED"
}
```

> 503 Response

```json
{
  "code": 503,
  "message": "硬件接口调用失败，请稍后重试",
  "error_code": "HARDWARE_API_ERROR"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_AvailableHostsListResponse_](#schemaresult_availablehostslistresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|405|[Method Not Allowed](https://tools.ietf.org/html/rfc7231#section-6.5.5)|HTTP 方法不允许|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|
|503|[Service Unavailable](https://tools.ietf.org/html/rfc7231#section-6.6.4)|外部服务不可用|Inline|

### 返回数据结构

状态码 **200**

*Result[AvailableHostsListResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[AvailableHostsListResponse](#schemaavailablehostslistresponse)|true|none|AvailableHostsListResponse|响应数据|
|»» hosts|[[AvailableHostInfo](#schemaavailablehostinfo)]|true|none|Hosts|可用主机列表|
|»»» AvailableHostInfo|[AvailableHostInfo](#schemaavailablehostinfo)|false|none|AvailableHostInfo|可用主机信息|
|»»»» host_rec_id|string|true|none|Host Rec Id|主机记录ID (host_rec.id)|
|»»»» hardware_id|string|true|none|Hardware Id|硬件ID|
|»»»» user_name|string|true|none|User Name|用户名 (host_acct)|
|»»»» host_ip|string|true|none|Host Ip|主机IP|
|»»»» appr_state|integer|true|none|Appr State|审批状态|
|»»»» host_state|integer|true|none|Host State|主机状态|
|»» total|integer|true|none|Total|本次查询发现的可用主机总数|
|»» page_size|integer|true|none|Page Size|每页大小|
|»» has_next|boolean|true|none|Has Next|是否有下一页|
|»» last_id|any|false|none|Last Id|当前页最后一条记录的 id，用于请求下一页|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdget_retry_vnc_list_api_v1_host_hosts_retry_vnc_post"></a>

## POST 获取重试 VNC 列表

POST /api/v1/host/hosts/retry-vnc

查询需要重试的 VNC 连接列表（case_state != 2 的主机）

> Body 请求参数

```json
{
  "user_id": "string"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[Body_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post](#schemabody_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post)| 是 | Body_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_id": "string",
        "host_ip": "string",
        "user_name": "string"
      }
    ],
    "total": 0
  },
  "timestamp": "string",
  "locale": "string"
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "请求参数无效",
  "error_code": "INVALID_PARAMS"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_RetryVNCListResponse_](#schemaresult_retryvnclistresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **200**

*Result[RetryVNCListResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[RetryVNCListResponse](#schemaretryvnclistresponse)|true|none|RetryVNCListResponse|响应数据|
|»» hosts|[[RetryVNCHostInfo](#schemaretryvnchostinfo)]|true|none|Hosts|重试 VNC 主机列表|
|»»» RetryVNCHostInfo|[RetryVNCHostInfo](#schemaretryvnchostinfo)|false|none|RetryVNCHostInfo|重试 VNC 主机信息|
|»»»» host_id|string|true|none|Host Id|主机ID (host_rec.id)|
|»»»» host_ip|string|true|none|Host Ip|主机IP|
|»»»» user_name|string|true|none|User Name|主机账号 (host_acct)|
|»» total|integer|true|none|Total|主机总数|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdrelease_hosts_api_v1_host_hosts_release_post"></a>

## POST 释放主机

POST /api/v1/host/hosts/release

逻辑删除指定用户的主机执行日志记录（设置 del_flag = 1）

> Body 请求参数

```json
{
  "user_id": "string",
  "host_list": [
    "string"
  ]
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[ReleaseHostsRequest](#schemareleasehostsrequest)| 是 | ReleaseHostsRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "主机释放成功",
  "data": {
    "updated_count": 3,
    "user_id": "user123",
    "host_list": [
      "host1",
      "host2",
      "host3"
    ]
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "主机ID格式无效",
  "error_code": "INVALID_HOST_ID"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|释放成功|[Result_ReleaseHostsResponse_](#schemaresult_releasehostsresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **200**

*Result[ReleaseHostsResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[ReleaseHostsResponse](#schemareleasehostsresponse)|true|none|ReleaseHostsResponse|响应数据|
|»» updated_count|integer|true|none|Updated Count|更新的记录数（逻辑删除）|
|»» user_id|string|true|none|User Id|用户ID|
|»» host_list|[string]|true|none|Host List|主机ID列表|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

# Host-Service/浏览器插件-VNC连接管理

<a id="opIdreport_vnc_connection_api_v1_host_vnc_report_post"></a>

## POST 上报 VNC 连接结果

POST /api/v1/host/vnc/report

处理浏览器插件上报的 VNC 连接结果，更新主机状态并管理执行日志

> Body 请求参数

```json
{
  "user_id": "string",
  "tc_id": "string",
  "cycle_name": "string",
  "user_name": "string",
  "host_id": "string",
  "connection_status": "string",
  "connection_time": "2019-08-24T14:15:22Z"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[VNCConnectionReport](#schemavncconnectionreport)| 是 | VNCConnectionReport|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "VNC连接结果上报成功",
  "data": {
    "host_id": "123",
    "connection_status": "success",
    "connection_time": "2025-10-15T10:00:00Z"
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "主机不存在: 123",
  "error_code": "HOST_NOT_FOUND"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|上报成功|[Result_VNCConnectionResponse_](#schemaresult_vncconnectionresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|主机不存在或请求数据无效|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **200**

*Result[VNCConnectionResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[VNCConnectionResponse](#schemavncconnectionresponse)|true|none|VNCConnectionResponse|响应数据|
|»» host_id|string|true|none|Host Id|主机ID|
|»» connection_status|string|true|none|Connection Status|连接状态|
|»» connection_time|string(date-time)|true|none|Connection Time|连接时间|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdget_vnc_connection_api_v1_host_vnc_connect_post"></a>

## POST 获取 VNC 连接信息

POST /api/v1/host/vnc/connect

获取指定主机的 VNC 连接参数，用于建立 VNC 连接

> Body 请求参数

```json
{
  "id": "string"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[GetVNCConnectionRequest](#schemagetvncconnectionrequest)| 是 | GetVNCConnectionRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "ip": "192.168.101.118",
    "port": "5900",
    "username": "neusoft",
    "***REMOVED***word": "***REMOVED***"
  }
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "主机ID格式无效",
  "error_code": "INVALID_HOST_ID"
}
```

> 404 Response

```json
{
  "code": 53001,
  "message": "主机不存在或未启用",
  "error_code": "HOST_NOT_FOUND"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|获取成功|[Result_VNCConnectionInfo_](#schemaresult_vncconnectioninfo_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求数据无效或 VNC 信息不完整|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|主机不存在或未启用|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **200**

*Result[VNCConnectionInfo]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[VNCConnectionInfo](#schemavncconnectioninfo)|true|none|VNCConnectionInfo|响应数据|
|»» ip|string|true|none|Ip|VNC服务器IP地址|
|»» port|string|true|none|Port|VNC服务端口|
|»» username|string|true|none|Username|连接用户名|
|»» ***REMOVED***word|string|true|none|Password|连接密码|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

# Host-Service/Agent-硬件信息上报

<a id="opIdreport_hardware_api_v1_host_agent_hardware_report_post"></a>

## POST 上报硬件信息

POST /api/v1/host/agent/hardware/report

Agent 上报主机硬件信息，系统会自动检测硬件变更。

    ## 功能说明
    1. 接收 Agent 上报的硬件信息（动态 JSON）
    2. 验证硬件信息必填字段（基于硬件模板）
    3. 对比硬件版本号和内容变化
    4. 根据对比结果更新数据库记录

    ## 认证要求
    - 需要在 Authorization 头中提供有效的 JWT token
    - Token 格式：`Bearer <token>`
    - Token 中的 user_id 字段将作为 host_id 使用

    ## 请求参数
    - `dmr_config`: DMR硬件配置（必需），必须包含 `revision` 字段
    - `name`: 配置名称（可选）
    - `updated_by`: 更新者（可选）
    - `tags`: 标签列表（可选）

    ## 业务逻辑
    1. **首次上报**: 直接插入硬件记录，审批状态为通过
    2. **版本号变化**: 标记为版本号变化（diff_state=1），等待审批
    3. **内容变化**: 标记为内容更改（diff_state=2），等待审批
    4. **无变化**: 不更新记录，返回无变化状态

    ## 注意事项
    - `dmr_config.revision` 是必传字段
    - 硬件模板中标记为 `required` 的字段必须提供
    - 硬件变更会触发主机状态更新（appr_state=2, host_state=6）

> Body 请求参数

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
        "installed_os": [
          "Windows",
          "Linux"
        ],
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
  "tags": [
    "alive",
    "checked",
    "updated"
  ]
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|object| 是 | Hardware Data|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "status": "string",
    "hw_rec_id": 0,
    "diff_state": 0,
    "diff_details": {},
    "message": "string"
  },
  "timestamp": "string",
  "locale": "string"
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "dmr_config 是必传字段",
  "error_code": "MISSING_DMR_CONFIG",
  "timestamp": "2025-01-30T10:00:00Z"
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "缺少有效的认证令牌",
  "error_code": "UNAUTHORIZED",
  "timestamp": "2025-01-30T10:00:00Z"
}
```

> 500 Response

```json
{
  "code": 500,
  "message": "硬件信息上报处理失败",
  "error_code": "HARDWARE_REPORT_FAILED",
  "timestamp": "2025-01-30T10:00:00Z"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|上报成功|[Result_HardwareReportResponse_](#schemaresult_hardwarereportresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|认证失败|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|服务器内部错误|Inline|

### 返回数据结构

状态码 **200**

*Result[HardwareReportResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[HardwareReportResponse](#schemahardwarereportresponse)|true|none|HardwareReportResponse|响应数据|
|»» status|string|true|none|Status|状态 (first_report/hardware_changed/no_change)|
|»» hw_rec_id|any|false|none|Hw Rec Id|硬件记录ID|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|integer|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» diff_state|any|false|none|Diff State|差异状态 (1-版本号变化, 2-内容更改)|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|integer|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» diff_details|any|false|none|Diff Details|差异详情|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|object|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» message|string|true|none|Message|响应消息|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdreport_testcase_result_api_v1_host_agent_testcase_report_post"></a>

## POST 上报测试用例执行结果

POST /api/v1/host/agent/testcase/report

Agent 上报测试用例执行结果，系统会更新执行日志记录。

    ## 功能说明
    1. 接收 Agent 上报的测试用例执行结果
    2. 从 JWT token 中提取 host_id
    3. 根据 host_id 和 tc_id 查询最新的执行日志记录
    4. 更新执行状态、结果消息和日志URL

    ## 认证要求
    - 需要在 Authorization 头中提供有效的 JWT token
    - Token 格式：`Bearer <token>`
    - Token 中的 user_id 字段将作为 host_id 使用

    ## 请求参数
    - `tc_id`: 测试用例ID（必需）
    - `state`: 执行状态（必需）；0-空闲 1-启动 2-成功 3-失败
    - `result_msg`: 结果消息（可选）
    - `log_url`: 日志文件URL（可选）

    ## 业务逻辑
    1. 根据 host_id 和 tc_id 查询 host_exec_log 表最新一条记录
    2. 更新 case_state、result_msg 和 log_url 字段
    3. 返回更新结果

    ## 注意事项
    - tc_id 是必传字段
    - state 必须在 0-3 范围内
    - 如果未找到对应的执行日志记录，返回404错误

> Body 请求参数

```json
{
  "log_url": "https://www.aaa.com/xxxx.log",
  "result_msg": "{\"code\":\"200\",\"msg\":\"ok\"}",
  "state": 2,
  "tc_id": "absdf1234"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[TestCaseReportRequest](#schematestcasereportrequest)| 是 | TestCaseReportRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "host_id": "string",
    "tc_id": "string",
    "case_state": 0,
    "result_msg": "string",
    "log_url": "string",
    "updated": true
  },
  "timestamp": "string",
  "locale": "string"
}
```

> 请求参数错误或业务逻辑错误（包括：请求参数验证失败、未找到执行日志记录等）

```json
{
  "code": 400,
  "message": "请求参数验证失败",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-10-30T10:00:00Z"
}
```

```json
{
  "code": 53012,
  "message": "未找到主机的测试用例执行记录",
  "error_code": "EXEC_LOG_NOT_FOUND",
  "timestamp": "2025-10-30T10:00:00Z"
}
```

> 401 Response

```json
{
  "code": 401,
  "message": "缺少有效的认证令牌",
  "error_code": "UNAUTHORIZED",
  "timestamp": "2025-10-30T10:00:00Z"
}
```

> 500 Response

```json
{
  "code": 500,
  "message": "测试用例结果上报处理失败",
  "error_code": "TESTCASE_REPORT_FAILED",
  "timestamp": "2025-10-30T10:00:00Z"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|上报成功|[Result_TestCaseReportResponse_](#schemaresult_testcasereportresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误或业务逻辑错误（包括：请求参数验证失败、未找到执行日志记录等）|Inline|
|401|[Unauthorized](https://tools.ietf.org/html/rfc7235#section-3.1)|认证失败|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|服务器内部错误|Inline|

### 返回数据结构

状态码 **200**

*Result[TestCaseReportResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[TestCaseReportResponse](#schematestcasereportresponse)|true|none|TestCaseReportResponse|响应数据|
|»» host_id|string|true|none|Host Id|主机ID|
|»» tc_id|string|true|none|Tc Id|测试用例ID|
|»» case_state|integer|true|none|Case State|case执行状态;0-空闲 1-启动 2-成功 3-失败|
|»» result_msg|any|false|none|Result Msg|结果消息|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» log_url|any|false|none|Log Url|日志文件URL|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» updated|boolean|true|none|Updated|是否成功更新|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdget_latest_ota_configs_api_v1_host_agent_ota_latest_get"></a>

## GET 获取最新 OTA 配置信息

GET /api/v1/host/agent/ota/latest

Agent 获取 OTA 版本配置信息。

    ## 功能说明
    1. 查询 `sys_conf` 表中 `conf_key = "ota"` 的有效配置
    2. 返回按更新时间倒序排列的配置列表

    ## 响应说明
    - `conf_name`: 配置名称
    - `conf_ver`: 配置版本号
    - `conf_url`: OTA 包下载地址
    - `conf_md5`: OTA 包 MD5 校验值

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": [
    {
      "conf_name": "string",
      "conf_ver": "string",
      "conf_url": "string",
      "conf_md5": "string"
    }
  ],
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[Result_List_OtaConfigItem__](#schemaresult_list_otaconfigitem__)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

# Host-Service/Agent-WebSocket管理

<a id="opIdget_active_hosts_api_v1_host_ws_hosts_get"></a>

## GET Get Active Hosts

GET /api/v1/host/ws/hosts

获取所有活跃连接的 Host ID

Returns:
    活跃 Host 列表和总数

Example:
    ```
GET /api/v1/ws/hosts
    ```

Response:
    ```json
    {
        "code": 200,
        "message": "获取活跃Host成功",
        "data": {
            "hosts": ["1846486359367955051", "1846486359367955052"],
            "count": 2
        }
    }
    ```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
null
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdget_host_status_api_v1_host_ws_status__host_id__get"></a>

## GET Get Host Status

GET /api/v1/host/ws/status/{host_id}

检查 Host 连接状态

Args:
    host_id: Host ID

Returns:
    连接状态信息

Example:
    ```
GET /api/v1/ws/status/1846486359367955051
    ```

Response:
    ```json
    {
        "code": 200,
        "message": "获取Host状态成功",
        "data": {
            "host_id": "1846486359367955051",
            "connected": true
        }
    }
    ```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|host_id|path|string| 是 | Host Id|主机ID（host_rec.id）|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
null
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdsend_message_to_host_api_v1_host_ws_send__host_id__post"></a>

## POST Send Message To Host

POST /api/v1/host/ws/send/{host_id}

发送消息给指定 Host

Args:
    host_id: 目标 Host ID
    message: 消息内容（必须包含 type 字段）

Returns:
    发送结果

Raises:
    BusinessError: 消息格式错误（缺少 type 字段）

Example:
    ```
POST /api/v1/ws/send/1846486359367955051
    {
        "type": "command",
        "command_id": "cmd_123",
        "command": "restart",
        "args": {"service": "nginx"}
    }
    ```

Response:
    ```json
    {
        "code": 200,
        "message": "消息发送成功",
        "data": {
            "host_id": "1846486359367955051",
            "success": true
        }
    }
    ```

> Body 请求参数

```json
{}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|host_id|path|string| 是 | Host Id|主机ID（host_rec.id）|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|object| 是 | Message|none|

> 返回示例

> 200 Response

```json
null
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdsend_message_to_hosts_api_v1_host_ws_send_to_hosts_post"></a>

## POST Send Message To Hosts

POST /api/v1/host/ws/send-to-hosts

发送消息给指定的多个 Hosts（多播）

Args:
    host_ids: 目标 Host ID 列表
    message: 消息内容（必须包含 type 字段）

Returns:
    发送结果统计

Raises:
    BusinessError: 消息格式错误（缺少 type 字段）

Example:
    ```
POST /api/v1/ws/send-to-hosts
    {
        "host_ids": ["1846486359367955051", "1846486359367955052"],
        "message": {
            "type": "notification",
            "message": "系统维护通知",
            "data": {"maintenance_time": "2025-10-28 22:00:00"}
        }
    }
    ```

Response:
    ```json
    {
        "code": 200,
        "message": "消息发送完成 (2/2成功)",
        "data": {
            "target_count": 2,
            "success_count": 2,
            "failed_count": 0
        }
    }
    ```

> Body 请求参数

```json
{
  "host_ids": [
    "string"
  ],
  "message": {}
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[Body_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post](#schemabody_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post)| 是 | Body_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post|none|

> 返回示例

> 200 Response

```json
null
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdbroadcast_message_api_v1_host_ws_broadcast_post"></a>

## POST Broadcast Message

POST /api/v1/host/ws/broadcast

广播消息给所有连接的 Hosts

Args:
    message: 消息内容（必须包含 type 字段）
    exclude_host_id: 排除的 Host ID（可选）

Returns:
    广播结果统计

Raises:
    BusinessError: 消息格式错误（缺少 type 字段）

Example:
    ```
POST /api/v1/ws/broadcast?exclude_host_id=1846486359367955051
    {
        "type": "notification",
        "message": "系统更新通知",
        "data": {"version": "2.0.0"}
    }
    ```

Response:
    ```json
    {
        "code": 200,
        "message": "广播完成 (99/100成功)",
        "data": {
            "total_count": 100,
            "success_count": 99,
            "failed_count": 1
        }
    }
    ```

> Body 请求参数

```json
{}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|exclude_host_id|query|string| 否 | Exclude Host Id|排除的Host ID|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|object| 是 | Message|none|

> 返回示例

> 200 Response

```json
null
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdnotify_host_offline_api_v1_host_ws_notify_offline__host_id__post"></a>

## POST Notify Host Offline

POST /api/v1/host/ws/notify-offline/{host_id}

通知指定 Host 下线

服务端主动通知 Agent 其 Host 已下线，Agent 收到后会：

1. 查询 host_exec_log 表的最新一条记录（del_flag=0）
2. 更新 host_state 为 4（离线状态）

Args:
    host_id: 目标 Host ID
    reason: 下线原因（可选）

Returns:
    通知发送结果

Raises:
    BusinessError: Host 未连接

Example:
    ```
POST /api/v1/ws/notify-offline/1846486359367955051?reason=系统维护
    ```

Response:
    ```json
    {
        "code": 200,
        "message": "Host下线通知已发送",
        "data": {
            "host_id": "1846486359367955051",
            "success": true,
            "reason": "系统维护"
        }
    }
    ```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|host_id|path|string| 是 | Host Id|主机ID（host_rec.id）|
|reason|query|string| 否 | Reason|下线原因|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
null
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

# Host-Service/管理后台-可用主机管理

<a id="opIdlist_hosts_api_v1_host_admin_host_list_get"></a>

## GET 查询可用 host 主机列表

GET /api/v1/host/admin/host/list

分页查询可用主机列表，支持多种搜索条件

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|page|query|integer| 否 | Page|none|
|page_size|query|integer| 否 | Page Size|none|
|mac|query|any| 否 | Mac|none|
|username|query|any| 否 | Username|none|
|host_state|query|any| 否 | Host State|none|
|mg_id|query|any| 否 | Mg Id|none|
|use_by|query|any| 否 | Use By|none|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_id": "string",
        "username": "string",
        "mg_id": "string",
        "mac": "string",
        "use_by": "string",
        "host_state": 0,
        "appr_state": 0
      }
    ],
    "total": 0,
    "page": 0,
    "page_size": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_AdminHostListResponse_](#schemaresult_adminhostlistresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIddelete_host_api_v1_host_admin_host__host_id__delete"></a>

## DELETE 删除主机

DELETE /api/v1/host/admin/host/{host_id}

逻辑删除主机（设置 del_flag=1），并通知外部API

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|host_id|path|integer| 是 | Host Id|主机ID（host_rec.id）|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "主机删除成功",
  "data": {
    "id": "123"
  }
}
```

> 删除失败（业务错误）

```json
{
  "code": 53001,
  "message": "主机不存在或已删除（ID: 123）",
  "error_code": "HOST_NOT_FOUND"
}
```

```json
{
  "code": 53002,
  "message": "主机删除失败，记录可能已被删除（ID: 123）",
  "error_code": "HOST_DELETE_FAILED"
}
```

```json
{
  "code": 53003,
  "message": "主机删除失败：外部API通知失败（ID: 123）",
  "error_code": "HOST_DELETE_EXTERNAL_API_FAILED"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|删除成功|[SuccessResponse](#schemasuccessresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|删除失败（业务错误）|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIddisable_host_api_v1_host_admin_host_disable_put"></a>

## PUT 停用主机

PUT /api/v1/host/admin/host/disable

停用主机（设置 appr_state=0）

> Body 请求参数

```json
{
  "host_id": 1
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AdminHostDisableRequest](#schemaadminhostdisablerequest)| 是 | AdminHostDisableRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "主机停用成功",
  "data": {
    "id": "123",
    "appr_state": 0,
    "host_state": 7
  }
}
```

> 停用失败（业务错误）

```json
{
  "code": 53001,
  "message": "主机不存在或已删除（ID: 123）",
  "error_code": "HOST_NOT_FOUND"
}
```

```json
{
  "code": 53004,
  "message": "主机停用失败，记录可能已被删除（ID: 123）",
  "error_code": "HOST_DISABLE_FAILED"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|停用成功|[SuccessResponse](#schemasuccessresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|停用失败（业务错误）|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdforce_offline_host_api_v1_host_admin_host_force_offline_post"></a>

## POST 强制下线主机

POST /api/v1/host/admin/host/force-offline

强制下线主机（设置 host_state=4），并通知WebSocket

> Body 请求参数

```json
{
  "host_id": 1
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AdminHostForceOfflineRequest](#schemaadminhostforceofflinerequest)| 是 | AdminHostForceOfflineRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "主机强制下线成功",
  "data": {
    "id": "123",
    "host_state": 4,
    "websocket_notified": true
  }
}
```

> 强制下线失败（业务错误）

```json
{
  "code": 53001,
  "message": "主机不存在或已删除（ID: 123）",
  "error_code": "HOST_NOT_FOUND"
}
```

```json
{
  "code": 53005,
  "message": "主机强制下线失败，记录可能已被删除（ID: 123）",
  "error_code": "HOST_FORCE_OFFLINE_FAILED"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|强制下线成功|[SuccessResponse](#schemasuccessresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|强制下线失败（业务错误）|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdget_host_detail_api_v1_host_admin_host_detail_get"></a>

## GET 查询主机详情

GET /api/v1/host/admin/host/detail

查询可用主机的详细信息（主体信息）

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|host_id|query|integer| 是 | Host Id|none|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "查询主机详情成功",
  "data": {
    "mg_id": "machine-guid-123",
    "mac": "00:11:22:33:44:55",
    "ip": "192.168.1.100",
    "username": "admin",
    "***REMOVED***word": "***REMOVED***",
    "port": 5900,
    "hw_info": {
      "cpu": "Intel i7",
      "memory": "16GB"
    },
    "appr_time": "2025-01-15T10:00:00Z"
  }
}
```

> 400 Response

```json
{
  "code": 53001,
  "message": "主机不存在或已删除（ID: 123）",
  "error_code": "HOST_NOT_FOUND"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_AdminHostDetailResponse_](#schemaresult_adminhostdetailresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|查询失败（业务错误）|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **200**

*Result[AdminHostDetailResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[AdminHostDetailResponse](#schemaadminhostdetailresponse)|true|none|AdminHostDetailResponse|响应数据|
|»» mg_id|any|false|none|Mg Id|唯一引导ID（host_rec 表 mg_id）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» mac|any|false|none|Mac|MAC地址（host_rec 表 mac_addr）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» ip|any|false|none|Ip|IP地址（host_rec 表 host_ip）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» username|any|false|none|Username|主机账号（host_rec 表 host_acct）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» ***REMOVED***word|any|false|none|Password|主机密码（host_rec 表 host_pwd，已解密）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» port|any|false|none|Port|端口（host_rec 表 host_port）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|integer|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» hw_list|[[AdminHostHwDetailInfo](#schemaadminhosthwdetailinfo)]|false|none|Hw List|硬件信息列表（host_hw_rec 表 sync_state=2 的记录，按 updated_time 倒序）|
|»»» AdminHostHwDetailInfo|[AdminHostHwDetailInfo](#schemaadminhosthwdetailinfo)|false|none|AdminHostHwDetailInfo|管理后台主机硬件详情信息响应模式|
|»»»» hw_info|any|false|none|Hw Info|硬件信息（host_hw_rec 表 hw_info）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|object|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» appr_time|any|false|none|Appr Time|审批时间（host_hw_rec 表 appr_time）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string(date-time)|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdupdate_host_***REMOVED***word_api_v1_host_admin_host_***REMOVED***word_put"></a>

## PUT 修改主机密码

PUT /api/v1/host/admin/host/***REMOVED***word

修改主机密码（AES加密后存储）

> Body 请求参数

```json
{
  "host_id": 1,
  "***REMOVED***word": "string"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AdminHostUpdatePasswordRequest](#schemaadminhostupdate***REMOVED***wordrequest)| 是 | AdminHostUpdatePasswordRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "主机密码修改成功",
  "data": {
    "id": "123"
  }
}
```

> 密码修改失败（业务错误）

```json
{
  "code": 53001,
  "message": "主机不存在或已删除（ID: 123）",
  "error_code": "HOST_NOT_FOUND"
}
```

```json
{
  "code": 53006,
  "message": "主机密码修改失败，记录可能已被删除（ID: 123）",
  "error_code": "HOST_PASSWORD_UPDATE_FAILED"
}
```

```json
{
  "code": 53007,
  "message": "密码加密失败（ID: 123）",
  "error_code": "PASSWORD_ENCRYPT_FAILED"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|密码修改成功|[SuccessResponse](#schemasuccessresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|密码修改失败（业务错误）|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdlist_host_exec_logs_api_v1_host_admin_host_exec_logs_get"></a>

## GET 查询主机执行日志列表

GET /api/v1/host/admin/host/exec-logs

分页查询主机执行日志列表（按创建时间倒序）

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|host_id|query|integer| 是 | Host Id|none|
|page|query|integer| 否 | Page|none|
|page_size|query|integer| 否 | Page Size|none|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "查询执行日志成功",
  "data": {
    "logs": [
      {
        "exec_date": "2025-01-15",
        "exec_time": "01:30:45",
        "tc_id": "test_case_001",
        "use_by": "user123",
        "case_state": 2,
        "result_msg": "执行成功",
        "log_url": "http://example.com/logs/123.log"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

> 400 Response

```json
{
  "code": 53001,
  "message": "主机不存在或已删除（ID: 123）",
  "error_code": "HOST_NOT_FOUND"
}
```

> 422 Response

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_AdminHostExecLogListResponse_](#schemaresult_adminhostexecloglistresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|查询失败（业务错误）|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **200**

*Result[AdminHostExecLogListResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[AdminHostExecLogListResponse](#schemaadminhostexecloglistresponse)|true|none|AdminHostExecLogListResponse|响应数据|
|»» logs|[[AdminHostExecLogInfo](#schemaadminhostexecloginfo)]|false|none|Logs|执行日志列表|
|»»» AdminHostExecLogInfo|[AdminHostExecLogInfo](#schemaadminhostexecloginfo)|false|none|AdminHostExecLogInfo|管理后台主机执行日志信息响应模式|
|»»»» log_id|any|false|none|Log Id|执行日志ID（host_exec_log 表 id）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» exec_date|any|false|none|Exec Date|执行日期（格式：%Y-%m-%d）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» exec_time|any|false|none|Exec Time|执行时长（格式：%H:%M:%S）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» tc_id|any|false|none|Tc Id|执行测试ID（host_exec_log 表 tc_id）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» use_by|any|false|none|Use By|使用人（host_exec_log 表 user_name）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» case_state|any|false|none|Case State|执行状态（0-空闲, 1-启动, 2-成功, 3-失败）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|integer|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» result_msg|any|false|none|Result Msg|执行结果（host_exec_log 表 result_msg）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» log_url|any|false|none|Log Url|执行日志地址（host_exec_log 表 log_url）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» total|integer|true|none|Total|总记录数|
|»» page|integer|true|none|Page|当前页码|
|»» page_size|integer|true|none|Page Size|每页大小|
|»» total_pages|integer|true|none|Total Pages|总页数|
|»» has_next|boolean|true|none|Has Next|是否有下一页|
|»» has_prev|boolean|true|none|Has Prev|是否有上一页|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

# Host-Service/管理后台-待审批主机管理

<a id="opIdlist_appr_hosts_api_v1_host_admin_appr_host_list_get"></a>

## GET 查询待审批 host 主机列表

GET /api/v1/host/admin/appr-host/list

分页查询待审批主机列表，支持多种搜索条件

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|page|query|integer| 否 | Page|none|
|page_size|query|integer| 否 | Page Size|none|
|mac|query|any| 否 | Mac|none|
|mg_id|query|any| 否 | Mg Id|none|
|host_state|query|any| 否 | Host State|none|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_id": "string",
        "mg_id": "string",
        "mac_addr": "string",
        "host_state": 0,
        "subm_time": "2019-08-24T14:15:22Z",
        "diff_state": 0
      }
    ],
    "total": 0,
    "page": 0,
    "page_size": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_AdminApprHostListResponse_](#schemaresult_adminapprhostlistresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIdget_appr_host_detail_api_v1_host_admin_appr_host_detail_get"></a>

## GET 查询待审批 host 主机详情

GET /api/v1/host/admin/appr-host/detail

查询待审批主机的详细信息

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|host_id|query|integer| 是 | Host Id|none|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "mg_id": "string",
    "mac": "string",
    "ip": "string",
    "username": "string",
    "***REMOVED***word": "string",
    "port": 0,
    "host_state": 0,
    "hw_list": [
      {
        "created_time": "2019-08-24T14:15:22Z",
        "hw_info": {}
      }
    ]
  },
  "timestamp": "string",
  "locale": "string"
}
```

> 400 Response

```json
{
  "code": 53001,
  "message": "主机不存在或已删除（ID: 123）",
  "error_code": "HOST_NOT_FOUND"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_AdminApprHostDetailResponse_](#schemaresult_adminapprhostdetailresponse_)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|查询失败（业务错误）|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **200**

*Result[AdminApprHostDetailResponse]*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|false|none|Code|响应码|
|» message|string|false|none|Message|响应消息|
|» data|[AdminApprHostDetailResponse](#schemaadminapprhostdetailresponse)|true|none|AdminApprHostDetailResponse|响应数据|
|»» mg_id|any|false|none|Mg Id|唯一引导ID（host_rec 表 mg_id）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» mac|any|false|none|Mac|MAC地址（host_rec 表 mac_addr）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» ip|any|false|none|Ip|IP地址（host_rec 表 host_ip）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» username|any|false|none|Username|主机账号（host_rec 表 host_acct）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» ***REMOVED***word|any|false|none|Password|主机密码（host_rec 表 host_pwd，已解密）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» port|any|false|none|Port|端口（host_rec 表 host_port）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|integer|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» host_state|any|false|none|Host State|主机状态（host_rec 表 host_state；0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, 5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|integer|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» hw_list|[[AdminApprHostHwInfo](#schemaadminapprhosthwinfo)]|false|none|Hw List|硬件信息列表（host_hw_rec 表 sync_state=1 的记录，按 created_time 倒序）|
|»»» AdminApprHostHwInfo|[AdminApprHostHwInfo](#schemaadminapprhosthwinfo)|false|none|AdminApprHostHwInfo|管理后台待审批主机硬件信息响应模式|
|»»»» created_time|any|false|none|Created Time|创建时间（host_hw_rec 表 created_time）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|string(date-time)|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» hw_info|any|false|none|Hw Info|硬件信息（host_hw_rec 表 hw_info）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|object|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»»» *anonymous*|null|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|» locale|any|false|none|Locale|语言代码（用于多语言支持）|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»» *anonymous*|null|false|none||none|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdapprove_hosts_api_v1_host_admin_appr_host_approve_post"></a>

## POST 同意启用待审批 host 主机

POST /api/v1/host/admin/appr-host/approve

同意启用待审批主机，更新硬件记录和主机状态

> Body 请求参数

```json
{
  "diff_type": 1,
  "host_ids": [
    0
  ]
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AdminApprHostApproveRequest](#schemaadminapprhostapproverequest)| 是 | AdminApprHostApproveRequest|none|

> 返回示例

> 200 Response

```json
{
  "success_count": 0,
  "failed_count": 0,
  "results": [
    {}
  ]
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "当 diff_type=2 时，host_ids 为必填参数",
  "error_code": "HOST_IDS_REQUIRED"
}
```

> 500 Response

```json
{
  "code": 500,
  "message": "同意启用主机失败: 数据库操作异常",
  "error_code": "APPROVE_HOST_FAILED"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|处理成功|[AdminApprHostApproveResponse](#schemaadminapprhostapproveresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|服务器内部错误|Inline|

### 返回数据结构

状态码 **200**

*AdminApprHostApproveResponse*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» success_count|integer|true|none|Success Count|成功处理的主机数量|
|» failed_count|integer|true|none|Failed Count|失败的主机数量|
|» results|[object]|false|none|Results|处理结果详情（包含成功和失败的记录）|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdget_maintain_email_api_v1_host_admin_appr_host_maintain_email_get"></a>

## GET 获取维护通知邮箱

GET /api/v1/host/admin/appr-host/maintain-email

查询 sys_conf 表，获取维护通知邮箱配置

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "conf_key": "string",
  "conf_val": "string"
}
```

> 500 Response

```json
{
  "code": 500,
  "message": "获取维护通知邮箱失败: 数据库操作异常",
  "error_code": "GET_MAINTAIN_EMAIL_FAILED"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[AdminMaintainEmailResponse](#schemaadminmaintainemailresponse)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|服务器内部错误|Inline|

### 返回数据结构

状态码 **200**

*AdminMaintainEmailResponse*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» conf_key|string|true|none|Conf Key|配置键（固定为 'email'）|
|» conf_val|string|true|none|Conf Val|配置值（格式化后的邮箱地址）|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

<a id="opIdset_maintain_email_api_v1_host_admin_appr_host_maintain_email_post"></a>

## POST 设置维护通知邮箱

POST /api/v1/host/admin/appr-host/maintain-email

设置维护通知邮箱，多个邮箱以半角逗号分割

> Body 请求参数

```json
{
  "email": "string"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AdminMaintainEmailRequest](#schemaadminmaintainemailrequest)| 是 | AdminMaintainEmailRequest|none|

> 返回示例

> 200 Response

```json
{
  "conf_key": "string",
  "conf_val": "string"
}
```

> 400 Response

```json
{
  "code": 400,
  "message": "邮箱地址不能为空",
  "error_code": "EMAIL_EMPTY"
}
```

> 500 Response

```json
{
  "code": 500,
  "message": "设置维护通知邮箱失败: 数据库操作异常",
  "error_code": "SET_MAINTAIN_EMAIL_FAILED"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|设置成功|[AdminMaintainEmailResponse](#schemaadminmaintainemailresponse)|
|400|[Bad Request](https://tools.ietf.org/html/rfc7231#section-6.5.1)|请求参数错误|Inline|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|
|500|[Internal Server Error](https://tools.ietf.org/html/rfc7231#section-6.6.1)|服务器内部错误|Inline|

### 返回数据结构

状态码 **200**

*AdminMaintainEmailResponse*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» conf_key|string|true|none|Conf Key|配置键（固定为 'email'）|
|» conf_val|string|true|none|Conf Val|配置值（格式化后的邮箱地址）|

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

# Host-Service/管理后台-OTA管理

<a id="opIdlist_ota_configs_api_v1_host_admin_ota_list_get"></a>

## GET 查询 OTA 配置列表

GET /api/v1/host/admin/ota/list

查询 sys_conf 表中 conf_key = 'ota', state_flag = 0, del_flag = 0 的全部数据

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "ota_configs": [
      {
        "id": "string",
        "conf_ver": "string",
        "conf_name": "string",
        "conf_url": "string",
        "conf_md5": "string"
      }
    ],
    "total": 0
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|查询成功|[Result_AdminOtaListResponse_](#schemaresult_adminotalistresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIddeploy_ota_config_api_v1_host_admin_ota_deploy_post"></a>

## POST 下发 OTA 配置

POST /api/v1/host/admin/ota/deploy

下发 OTA 配置到所有连接的 Host，更新 sys_conf 表并广播消息

> Body 请求参数

```json
{
  "id": 0,
  "conf_ver": "string",
  "conf_name": "string",
  "conf_url": "string",
  "conf_md5": "stringstringstringstringstringst"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AdminOtaDeployRequest](#schemaadminotadeployrequest)| 是 | AdminOtaDeployRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": "string",
    "conf_ver": "string",
    "conf_name": "string",
    "conf_url": "string",
    "conf_md5": "string",
    "broadcast_count": 0
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|下发成功|[Result_AdminOtaDeployResponse_](#schemaresult_adminotadeployresponse_)|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|OTA 配置不存在|None|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

# Host-Service/文件管理

<a id="opIdupload_file_api_v1_host_file_upload_post"></a>

## POST 上传文件

POST /api/v1/host/file/upload

上传文件到服务器指定目录，返回文件访问 URL

> Body 请求参数

```yaml
file: ""

```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|object| 是 ||none|
|» file|body|string(binary)| 是 | File|要上传的文件|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "file_id": "string",
    "filename": "string",
    "saved_filename": "string",
    "file_url": "string",
    "file_size": 0,
    "content_type": "string",
    "upload_time": "string"
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|上传成功|[Result_FileUploadResponse_](#schemaresult_fileuploadresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIdget_file_api_v1_host_file__filename__get"></a>

## GET 获取文件（支持断点续传）

GET /api/v1/host/file/{filename}

通过 `saved_filename` 获取上传的文件内容，默认返回完整文件。

### Range 下载说明

- 支持标准 HTTP Range 请求头，格式：`Range: bytes=start-end`
- 例如：`Range: bytes=0-1048575` 可获取前 1MB，用于断点续传
- 响应会携带 `Accept-Ranges: bytes`、`Content-Range`、`Content-Length`
- 当 Range 合法时返回 `206 Partial Content`，否则返回 `416`
- 未携带 Range 时返回完整文件（200 OK）

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|filename|path|string| 是 | Filename|保存的文件名（由上传接口返回的 saved_filename）|

> 返回示例

> 200 Response

```json
null
```

> 206 Response

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|返回完整文件内容|Inline|
|206|[Partial Content](https://tools.ietf.org/html/rfc7233#section-4.1)|返回部分内容（断点续传），包含 Content-Range 头|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|文件不存在|None|
|416|[Range Not Satisfiable](https://tools.ietf.org/html/rfc7233#section-4.4)|Range 请求范围无效|None|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

### 返回数据结构

状态码 **422**

*HTTPValidationError*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|
|»» ValidationError|[ValidationError](#schemavalidationerror)|false|none|ValidationError|none|
|»»» loc|[anyOf]|true|none|Location|none|

*anyOf*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|string|false|none||none|

*or*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»»» *anonymous*|integer|false|none||none|

*continued*

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|»»» msg|string|true|none|Message|none|
|»»» type|string|true|none|Error Type|none|

# Auth-Service/认证

<a id="opIdadmin_login_api_v1_auth_admin_login_post"></a>

## POST 管理员登录

POST /api/v1/auth/admin/login

管理员登录（传统方式）

使用用户名和密码进行登录，返回访问令牌

Args:
    login_data: 登录请求数据（username, ***REMOVED***word）
    auth_service: 认证服务实例

Returns:
    Result[LoginResponse]: 包含 token 的成功响应

Raises:
    HTTPException: 登录失败时抛出（由 @handle_api_errors 统一处理）

> Body 请求参数

```json
{
  "***REMOVED***word": "***REMOVED***",
  "username": "admin"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AdminLoginRequest](#schemaadminloginrequest)| 是 | AdminLoginRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "refresh_expires_in": 604800,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[Result_LoginResponse_](#schemaresult_loginresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIddevice_login_api_v1_auth_device_login_post"></a>

## POST 设备登录

POST /api/v1/auth/device/login

设备登录（传统方式）

使用 mg_id、host_ip 和 username 进行登录
如果 mg_id 存在则更新信息，不存在则创建新记录

Args:
    login_data: 设备登录请求数据（mg_id, host_ip, username）
    auth_service: 认证服务实例
    current_user: 当前用户信息（可选，用于审计）

Returns:
    Result[LoginResponse]: 包含 token 的成功响应

Raises:
    HTTPException: 登录失败时抛出（由 @handle_api_errors 统一处理）

> Body 请求参数

```json
{
  "host_ip": "192.168.1.100",
  "mg_id": "device-12345",
  "username": "root"
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[DeviceLoginRequest](#schemadeviceloginrequest)| 是 | DeviceLoginRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "refresh_expires_in": 604800,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[Result_LoginResponse_](#schemaresult_loginresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIdrefresh_token_api_v1_auth_refresh_post"></a>

## POST Refresh Token

POST /api/v1/auth/refresh

刷新访问令牌

Args:
    refresh_data: 刷新令牌请求数据
    auth_service: 认证服务实例

Returns:
    Result[TokenResponse]: 包含新令牌的成功响应

Raises:
    HTTPException: 刷新失败时抛出（由 @handle_api_errors 统一处理）

> Body 请求参数

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[RefreshTokenRequest](#schemarefreshtokenrequest)| 是 | RefreshTokenRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "refresh_expires_in": 604800,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[Result_TokenResponse_](#schemaresult_tokenresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIdauto_refresh_tokens_api_v1_auth_auto_refresh_post"></a>

## POST 自动续期令牌

POST /api/v1/auth/auto-refresh

自动续期访问令牌和刷新令牌

当刷新令牌将要过期时，同时生成新的 access_token 和 refresh_token
实现真正的"双 token 续期"机制

Args:
    refresh_data: 自动续期请求数据（包含 auto_renew 参数）
    auth_service: 认证服务实例

Returns:
    Result[TokenResponse]: 包含新的 access_token 和 refresh_token 的成功响应

Raises:
    HTTPException: 续期失败时抛出（由 @handle_api_errors 统一处理）

> Body 请求参数

```json
{
  "auto_renew": true,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[AutoRefreshTokenRequest](#schemaautorefreshtokenrequest)| 是 | AutoRefreshTokenRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "refresh_expires_in": 604800,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[Result_TokenResponse_](#schemaresult_tokenresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIdintrospect_token_api_v1_auth_introspect_post"></a>

## POST Introspect Token

POST /api/v1/auth/introspect

验证令牌

Args:
    introspect_data: 令牌验证请求数据
    auth_service: 认证服务实例

Returns:
    Result[IntrospectResponse]: 包含令牌验证结果的成功响应

> Body 请求参数

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[IntrospectRequest](#schemaintrospectrequest)| 是 | IntrospectRequest|none|

> 返回示例

> 200 Response

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "active": true,
    "exp": 1640995200,
    "token_type": "access",
    "user_id": "1",
    "username": "admin"
  },
  "timestamp": "string",
  "locale": "string"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[Result_IntrospectResponse_](#schemaresult_introspectresponse_)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

<a id="opIdlogout_api_v1_auth_logout_post"></a>

## POST Logout

POST /api/v1/auth/logout

用户注销

Args:
    logout_data: 注销请求数据
    auth_service: 认证服务实例

Returns:
    SuccessResponse: 注销成功响应

Raises:
    HTTPException: 注销失败时抛出（由 @handle_api_errors 统一处理）

> Body 请求参数

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 请求参数

|名称|位置|类型|必选|中文名|说明|
|---|---|---|---|---|---|
|accept-language|header|any| 否 | Accept-Language|Accept-Language 请求头|
|body|body|[LogoutRequest](#schemalogoutrequest)| 是 | LogoutRequest|none|

> 返回示例

> 200 Response

```json
{}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|[SuccessResponse](#schemasuccessresponse)|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|[HTTPValidationError](#schemahttpvalidationerror)|

# 数据模型

<h2 id="tocS_AdminApprHostApproveRequest">AdminApprHostApproveRequest</h2>

<a id="schemaadminapprhostapproverequest"></a>
<a id="schema_AdminApprHostApproveRequest"></a>
<a id="tocSadminapprhostapproverequest"></a>
<a id="tocsadminapprhostapproverequest"></a>

```json
{
  "diff_type": 1,
  "host_ids": [
    0
  ]
}

```

AdminApprHostApproveRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|diff_type|integer|true|none|Diff Type|变更类型（1-版本号变化, 2-内容变化）|
|host_ids|any|false|none|Host Ids|主机ID列表（host_rec 表主键数组；当 diff_type=2 时必填）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|[integer]|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_AdminApprHostApproveResponse">AdminApprHostApproveResponse</h2>

<a id="schemaadminapprhostapproveresponse"></a>
<a id="schema_AdminApprHostApproveResponse"></a>
<a id="tocSadminapprhostapproveresponse"></a>
<a id="tocsadminapprhostapproveresponse"></a>

```json
{
  "success_count": 0,
  "failed_count": 0,
  "results": [
    {}
  ]
}

```

AdminApprHostApproveResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|success_count|integer|true|none|Success Count|成功处理的主机数量|
|failed_count|integer|true|none|Failed Count|失败的主机数量|
|results|[object]|false|none|Results|处理结果详情（包含成功和失败的记录）|

<h2 id="tocS_AdminApprHostDetailResponse">AdminApprHostDetailResponse</h2>

<a id="schemaadminapprhostdetailresponse"></a>
<a id="schema_AdminApprHostDetailResponse"></a>
<a id="tocSadminapprhostdetailresponse"></a>
<a id="tocsadminapprhostdetailresponse"></a>

```json
{
  "mg_id": "string",
  "mac": "string",
  "ip": "string",
  "username": "string",
  "***REMOVED***word": "string",
  "port": 0,
  "host_state": 0,
  "hw_list": [
    {
      "created_time": "2019-08-24T14:15:22Z",
      "hw_info": {}
    }
  ]
}

```

AdminApprHostDetailResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mg_id|any|false|none|Mg Id|唯一引导ID（host_rec 表 mg_id）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mac|any|false|none|Mac|MAC地址（host_rec 表 mac_addr）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|ip|any|false|none|Ip|IP地址（host_rec 表 host_ip）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|username|any|false|none|Username|主机账号（host_rec 表 host_acct）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|***REMOVED***word|any|false|none|Password|主机密码（host_rec 表 host_pwd，已解密）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|port|any|false|none|Port|端口（host_rec 表 host_port）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_state|any|false|none|Host State|主机状态（host_rec 表 host_state；0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, 5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hw_list|[[AdminApprHostHwInfo](#schemaadminapprhosthwinfo)]|false|none|Hw List|硬件信息列表（host_hw_rec 表 sync_state=1 的记录，按 created_time 倒序）|

<h2 id="tocS_AdminApprHostHwInfo">AdminApprHostHwInfo</h2>

<a id="schemaadminapprhosthwinfo"></a>
<a id="schema_AdminApprHostHwInfo"></a>
<a id="tocSadminapprhosthwinfo"></a>
<a id="tocsadminapprhosthwinfo"></a>

```json
{
  "created_time": "2019-08-24T14:15:22Z",
  "hw_info": {}
}

```

AdminApprHostHwInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|created_time|any|false|none|Created Time|创建时间（host_hw_rec 表 created_time）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string(date-time)|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hw_info|any|false|none|Hw Info|硬件信息（host_hw_rec 表 hw_info）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|object|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_AdminApprHostInfo">AdminApprHostInfo</h2>

<a id="schemaadminapprhostinfo"></a>
<a id="schema_AdminApprHostInfo"></a>
<a id="tocSadminapprhostinfo"></a>
<a id="tocsadminapprhostinfo"></a>

```json
{
  "host_id": "string",
  "mg_id": "string",
  "mac_addr": "string",
  "host_state": 0,
  "subm_time": "2019-08-24T14:15:22Z",
  "diff_state": 0
}

```

AdminApprHostInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|string|true|none|Host Id|主机ID（host_rec 表主键 id）|
|mg_id|any|false|none|Mg Id|唯一引导ID（host_rec 表 mg_id）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mac_addr|any|false|none|Mac Addr|MAC地址（host_rec 表 mac_addr）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_state|any|false|none|Host State|主机状态（host_rec 表 host_state；0-空闲, 1-已锁定, 2-已占用, 3-case执行中, 4-离线, 5-待激活, 6-硬件改动, 7-手动停用, 8-更新中）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|subm_time|any|false|none|Subm Time|申报时间（host_rec 表 subm_time）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string(date-time)|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|diff_state|any|false|none|Diff State|参数状态（host_hw_rec 表 diff_state，最新一条记录；1-版本号变化, 2-内容更改, 3-异常）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_AdminApprHostListResponse">AdminApprHostListResponse</h2>

<a id="schemaadminapprhostlistresponse"></a>
<a id="schema_AdminApprHostListResponse"></a>
<a id="tocSadminapprhostlistresponse"></a>
<a id="tocsadminapprhostlistresponse"></a>

```json
{
  "hosts": [
    {
      "host_id": "string",
      "mg_id": "string",
      "mac_addr": "string",
      "host_state": 0,
      "subm_time": "2019-08-24T14:15:22Z",
      "diff_state": 0
    }
  ],
  "total": 0,
  "page": 0,
  "page_size": 0,
  "total_pages": 0,
  "has_next": true,
  "has_prev": true
}

```

AdminApprHostListResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hosts|[[AdminApprHostInfo](#schemaadminapprhostinfo)]|false|none|Hosts|待审批主机列表|
|total|integer|true|none|Total|总记录数|
|page|integer|true|none|Page|当前页码|
|page_size|integer|true|none|Page Size|每页大小|
|total_pages|integer|true|none|Total Pages|总页数|
|has_next|boolean|true|none|Has Next|是否有下一页|
|has_prev|boolean|true|none|Has Prev|是否有上一页|

<h2 id="tocS_AdminHostDetailResponse">AdminHostDetailResponse</h2>

<a id="schemaadminhostdetailresponse"></a>
<a id="schema_AdminHostDetailResponse"></a>
<a id="tocSadminhostdetailresponse"></a>
<a id="tocsadminhostdetailresponse"></a>

```json
{
  "mg_id": "string",
  "mac": "string",
  "ip": "string",
  "username": "string",
  "***REMOVED***word": "string",
  "port": 0,
  "hw_list": [
    {
      "hw_info": {},
      "appr_time": "2019-08-24T14:15:22Z"
    }
  ]
}

```

AdminHostDetailResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mg_id|any|false|none|Mg Id|唯一引导ID（host_rec 表 mg_id）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mac|any|false|none|Mac|MAC地址（host_rec 表 mac_addr）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|ip|any|false|none|Ip|IP地址（host_rec 表 host_ip）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|username|any|false|none|Username|主机账号（host_rec 表 host_acct）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|***REMOVED***word|any|false|none|Password|主机密码（host_rec 表 host_pwd，已解密）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|port|any|false|none|Port|端口（host_rec 表 host_port）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hw_list|[[AdminHostHwDetailInfo](#schemaadminhosthwdetailinfo)]|false|none|Hw List|硬件信息列表（host_hw_rec 表 sync_state=2 的记录，按 updated_time 倒序）|

<h2 id="tocS_AdminHostDisableRequest">AdminHostDisableRequest</h2>

<a id="schemaadminhostdisablerequest"></a>
<a id="schema_AdminHostDisableRequest"></a>
<a id="tocSadminhostdisablerequest"></a>
<a id="tocsadminhostdisablerequest"></a>

```json
{
  "host_id": 1
}

```

AdminHostDisableRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|integer|true|none|Host Id|主机ID（host_rec.id）|

<h2 id="tocS_AdminHostExecLogInfo">AdminHostExecLogInfo</h2>

<a id="schemaadminhostexecloginfo"></a>
<a id="schema_AdminHostExecLogInfo"></a>
<a id="tocSadminhostexecloginfo"></a>
<a id="tocsadminhostexecloginfo"></a>

```json
{
  "log_id": "string",
  "exec_date": "string",
  "exec_time": "string",
  "tc_id": "string",
  "use_by": "string",
  "case_state": 0,
  "result_msg": "string",
  "log_url": "string"
}

```

AdminHostExecLogInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|log_id|any|false|none|Log Id|执行日志ID（host_exec_log 表 id）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|exec_date|any|false|none|Exec Date|执行日期（格式：%Y-%m-%d）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|exec_time|any|false|none|Exec Time|执行时长（格式：%H:%M:%S）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|tc_id|any|false|none|Tc Id|执行测试ID（host_exec_log 表 tc_id）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|use_by|any|false|none|Use By|使用人（host_exec_log 表 user_name）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|case_state|any|false|none|Case State|执行状态（0-空闲, 1-启动, 2-成功, 3-失败）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|result_msg|any|false|none|Result Msg|执行结果（host_exec_log 表 result_msg）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|log_url|any|false|none|Log Url|执行日志地址（host_exec_log 表 log_url）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_AdminHostExecLogListResponse">AdminHostExecLogListResponse</h2>

<a id="schemaadminhostexecloglistresponse"></a>
<a id="schema_AdminHostExecLogListResponse"></a>
<a id="tocSadminhostexecloglistresponse"></a>
<a id="tocsadminhostexecloglistresponse"></a>

```json
{
  "logs": [
    {
      "log_id": "string",
      "exec_date": "string",
      "exec_time": "string",
      "tc_id": "string",
      "use_by": "string",
      "case_state": 0,
      "result_msg": "string",
      "log_url": "string"
    }
  ],
  "total": 0,
  "page": 0,
  "page_size": 0,
  "total_pages": 0,
  "has_next": true,
  "has_prev": true
}

```

AdminHostExecLogListResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|logs|[[AdminHostExecLogInfo](#schemaadminhostexecloginfo)]|false|none|Logs|执行日志列表|
|total|integer|true|none|Total|总记录数|
|page|integer|true|none|Page|当前页码|
|page_size|integer|true|none|Page Size|每页大小|
|total_pages|integer|true|none|Total Pages|总页数|
|has_next|boolean|true|none|Has Next|是否有下一页|
|has_prev|boolean|true|none|Has Prev|是否有上一页|

<h2 id="tocS_AdminHostForceOfflineRequest">AdminHostForceOfflineRequest</h2>

<a id="schemaadminhostforceofflinerequest"></a>
<a id="schema_AdminHostForceOfflineRequest"></a>
<a id="tocSadminhostforceofflinerequest"></a>
<a id="tocsadminhostforceofflinerequest"></a>

```json
{
  "host_id": 1
}

```

AdminHostForceOfflineRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|integer|true|none|Host Id|主机ID（host_rec.id）|

<h2 id="tocS_AdminHostHwDetailInfo">AdminHostHwDetailInfo</h2>

<a id="schemaadminhosthwdetailinfo"></a>
<a id="schema_AdminHostHwDetailInfo"></a>
<a id="tocSadminhosthwdetailinfo"></a>
<a id="tocsadminhosthwdetailinfo"></a>

```json
{
  "hw_info": {},
  "appr_time": "2019-08-24T14:15:22Z"
}

```

AdminHostHwDetailInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hw_info|any|false|none|Hw Info|硬件信息（host_hw_rec 表 hw_info）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|object|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|appr_time|any|false|none|Appr Time|审批时间（host_hw_rec 表 appr_time）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string(date-time)|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_AdminHostInfo">AdminHostInfo</h2>

<a id="schemaadminhostinfo"></a>
<a id="schema_AdminHostInfo"></a>
<a id="tocSadminhostinfo"></a>
<a id="tocsadminhostinfo"></a>

```json
{
  "host_id": "string",
  "username": "string",
  "mg_id": "string",
  "mac": "string",
  "use_by": "string",
  "host_state": 0,
  "appr_state": 0
}

```

AdminHostInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|string|true|none|Host Id|主机ID（host_rec 表主键 id）|
|username|any|false|none|Username|主机账号（host_rec 表 host_acct）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mg_id|any|false|none|Mg Id|唯一引导ID（host_rec 表 mg_id）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mac|any|false|none|Mac|MAC地址（host_rec 表 mac_addr）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|use_by|any|false|none|Use By|使用人（host_exec_log 表 user_name，最新一条）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_state|any|false|none|Host State|主机状态（host_rec 表 host_state）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|appr_state|any|false|none|Appr State|审批状态（host_rec 表 appr_state）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_AdminHostListResponse">AdminHostListResponse</h2>

<a id="schemaadminhostlistresponse"></a>
<a id="schema_AdminHostListResponse"></a>
<a id="tocSadminhostlistresponse"></a>
<a id="tocsadminhostlistresponse"></a>

```json
{
  "hosts": [
    {
      "host_id": "string",
      "username": "string",
      "mg_id": "string",
      "mac": "string",
      "use_by": "string",
      "host_state": 0,
      "appr_state": 0
    }
  ],
  "total": 0,
  "page": 0,
  "page_size": 0,
  "total_pages": 0,
  "has_next": true,
  "has_prev": true
}

```

AdminHostListResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hosts|[[AdminHostInfo](#schemaadminhostinfo)]|true|none|Hosts|主机列表|
|total|integer|true|none|Total|总记录数|
|page|integer|true|none|Page|当前页码|
|page_size|integer|true|none|Page Size|每页大小|
|total_pages|integer|true|none|Total Pages|总页数|
|has_next|boolean|true|none|Has Next|是否有下一页|
|has_prev|boolean|true|none|Has Prev|是否有上一页|

<h2 id="tocS_AdminHostUpdatePasswordRequest">AdminHostUpdatePasswordRequest</h2>

<a id="schemaadminhostupdate***REMOVED***wordrequest"></a>
<a id="schema_AdminHostUpdatePasswordRequest"></a>
<a id="tocSadminhostupdate***REMOVED***wordrequest"></a>
<a id="tocsadminhostupdate***REMOVED***wordrequest"></a>

```json
{
  "host_id": 1,
  "***REMOVED***word": "string"
}

```

AdminHostUpdatePasswordRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|integer|true|none|Host Id|主机ID（host_rec.id）|
|***REMOVED***word|string|true|none|Password|新密码（明文，将进行AES加密后存储）|

<h2 id="tocS_AdminMaintainEmailRequest">AdminMaintainEmailRequest</h2>

<a id="schemaadminmaintainemailrequest"></a>
<a id="schema_AdminMaintainEmailRequest"></a>
<a id="tocSadminmaintainemailrequest"></a>
<a id="tocsadminmaintainemailrequest"></a>

```json
{
  "email": "string"
}

```

AdminMaintainEmailRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|email|string|true|none|Email|邮箱地址（多个邮箱以半角逗号分割）|

<h2 id="tocS_AdminMaintainEmailResponse">AdminMaintainEmailResponse</h2>

<a id="schemaadminmaintainemailresponse"></a>
<a id="schema_AdminMaintainEmailResponse"></a>
<a id="tocSadminmaintainemailresponse"></a>
<a id="tocsadminmaintainemailresponse"></a>

```json
{
  "conf_key": "string",
  "conf_val": "string"
}

```

AdminMaintainEmailResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_key|string|true|none|Conf Key|配置键（固定为 'email'）|
|conf_val|string|true|none|Conf Val|配置值（格式化后的邮箱地址）|

<h2 id="tocS_AdminOtaConfigInfo">AdminOtaConfigInfo</h2>

<a id="schemaadminotaconfiginfo"></a>
<a id="schema_AdminOtaConfigInfo"></a>
<a id="tocSadminotaconfiginfo"></a>
<a id="tocsadminotaconfiginfo"></a>

```json
{
  "id": "string",
  "conf_ver": "string",
  "conf_name": "string",
  "conf_url": "string",
  "conf_md5": "string"
}

```

AdminOtaConfigInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|string|true|none|Id|配置ID（主键）|
|conf_ver|any|false|none|Conf Ver|配置版本号|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_name|any|false|none|Conf Name|配置名称|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_url|any|false|none|Conf Url|OTA 包下载地址|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_md5|any|false|none|Conf Md5|OTA 包 MD5 校验值|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_AdminOtaDeployRequest">AdminOtaDeployRequest</h2>

<a id="schemaadminotadeployrequest"></a>
<a id="schema_AdminOtaDeployRequest"></a>
<a id="tocSadminotadeployrequest"></a>
<a id="tocsadminotadeployrequest"></a>

```json
{
  "id": 0,
  "conf_ver": "string",
  "conf_name": "string",
  "conf_url": "string",
  "conf_md5": "stringstringstringstringstringst"
}

```

AdminOtaDeployRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|integer|true|none|Id|配置ID（主键）|
|conf_ver|string|true|none|Conf Ver|配置版本号|
|conf_name|string|true|none|Conf Name|配置名称|
|conf_url|string|true|none|Conf Url|OTA 包下载地址（字符串，允许任意格式）|
|conf_md5|string|true|none|Conf Md5|OTA 包 MD5 校验值（32位十六进制）|

<h2 id="tocS_AdminOtaDeployResponse">AdminOtaDeployResponse</h2>

<a id="schemaadminotadeployresponse"></a>
<a id="schema_AdminOtaDeployResponse"></a>
<a id="tocSadminotadeployresponse"></a>
<a id="tocsadminotadeployresponse"></a>

```json
{
  "id": "string",
  "conf_ver": "string",
  "conf_name": "string",
  "conf_url": "string",
  "conf_md5": "string",
  "broadcast_count": 0
}

```

AdminOtaDeployResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|string|true|none|Id|配置ID（主键）|
|conf_ver|string|true|none|Conf Ver|配置版本号|
|conf_name|string|true|none|Conf Name|配置名称|
|conf_url|string|true|none|Conf Url|OTA 包下载地址|
|conf_md5|string|true|none|Conf Md5|OTA 包 MD5 校验值|
|broadcast_count|integer|true|none|Broadcast Count|广播消息成功发送的主机数量|

<h2 id="tocS_AdminOtaListResponse">AdminOtaListResponse</h2>

<a id="schemaadminotalistresponse"></a>
<a id="schema_AdminOtaListResponse"></a>
<a id="tocSadminotalistresponse"></a>
<a id="tocsadminotalistresponse"></a>

```json
{
  "ota_configs": [
    {
      "id": "string",
      "conf_ver": "string",
      "conf_name": "string",
      "conf_url": "string",
      "conf_md5": "string"
    }
  ],
  "total": 0
}

```

AdminOtaListResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|ota_configs|[[AdminOtaConfigInfo](#schemaadminotaconfiginfo)]|true|none|Ota Configs|OTA 配置列表|
|total|integer|true|none|Total|配置总数|

<h2 id="tocS_AvailableHostInfo">AvailableHostInfo</h2>

<a id="schemaavailablehostinfo"></a>
<a id="schema_AvailableHostInfo"></a>
<a id="tocSavailablehostinfo"></a>
<a id="tocsavailablehostinfo"></a>

```json
{
  "host_rec_id": "string",
  "hardware_id": "string",
  "user_name": "string",
  "host_ip": "string",
  "appr_state": 0,
  "host_state": 0
}

```

AvailableHostInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_rec_id|string|true|none|Host Rec Id|主机记录ID (host_rec.id)|
|hardware_id|string|true|none|Hardware Id|硬件ID|
|user_name|string|true|none|User Name|用户名 (host_acct)|
|host_ip|string|true|none|Host Ip|主机IP|
|appr_state|integer|true|none|Appr State|审批状态|
|host_state|integer|true|none|Host State|主机状态|

<h2 id="tocS_AvailableHostsListResponse">AvailableHostsListResponse</h2>

<a id="schemaavailablehostslistresponse"></a>
<a id="schema_AvailableHostsListResponse"></a>
<a id="tocSavailablehostslistresponse"></a>
<a id="tocsavailablehostslistresponse"></a>

```json
{
  "hosts": [
    {
      "host_rec_id": "string",
      "hardware_id": "string",
      "user_name": "string",
      "host_ip": "string",
      "appr_state": 0,
      "host_state": 0
    }
  ],
  "total": 0,
  "page_size": 0,
  "has_next": true,
  "last_id": "string"
}

```

AvailableHostsListResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hosts|[[AvailableHostInfo](#schemaavailablehostinfo)]|true|none|Hosts|可用主机列表|
|total|integer|true|none|Total|本次查询发现的可用主机总数|
|page_size|integer|true|none|Page Size|每页大小|
|has_next|boolean|true|none|Has Next|是否有下一页|
|last_id|any|false|none|Last Id|当前页最后一条记录的 id，用于请求下一页|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Body_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post">Body_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post</h2>

<a id="schemabody_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post"></a>
<a id="schema_Body_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post"></a>
<a id="tocSbody_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post"></a>
<a id="tocsbody_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post"></a>

```json
{
  "user_id": "string"
}

```

Body_get_retry_vnc_list_api_v1_host_hosts_retry_vnc_post

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|user_id|string|true|none|User Id|用户ID|

<h2 id="tocS_Body_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post">Body_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post</h2>

<a id="schemabody_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post"></a>
<a id="schema_Body_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post"></a>
<a id="tocSbody_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post"></a>
<a id="tocsbody_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post"></a>

```json
{
  "host_ids": [
    "string"
  ],
  "message": {}
}

```

Body_send_message_to_hosts_api_v1_host_ws_send_to_hosts_post

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_ids|[string]|true|none|Host Ids|none|
|message|object|true|none|Message|none|

<h2 id="tocS_Body_upload_file_api_v1_host_file_upload_post">Body_upload_file_api_v1_host_file_upload_post</h2>

<a id="schemabody_upload_file_api_v1_host_file_upload_post"></a>
<a id="schema_Body_upload_file_api_v1_host_file_upload_post"></a>
<a id="tocSbody_upload_file_api_v1_host_file_upload_post"></a>
<a id="tocsbody_upload_file_api_v1_host_file_upload_post"></a>

```json
{
  "file": "string"
}

```

Body_upload_file_api_v1_host_file_upload_post

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|file|string(binary)|true|none|File|要上传的文件|

<h2 id="tocS_FileUploadResponse">FileUploadResponse</h2>

<a id="schemafileuploadresponse"></a>
<a id="schema_FileUploadResponse"></a>
<a id="tocSfileuploadresponse"></a>
<a id="tocsfileuploadresponse"></a>

```json
{
  "file_id": "string",
  "filename": "string",
  "saved_filename": "string",
  "file_url": "string",
  "file_size": 0,
  "content_type": "string",
  "upload_time": "string"
}

```

FileUploadResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|file_id|string|true|none|File Id|文件唯一标识|
|filename|string|true|none|Filename|原始文件名|
|saved_filename|string|true|none|Saved Filename|保存的文件名|
|file_url|string|true|none|File Url|文件访问 URL|
|file_size|integer|true|none|File Size|文件大小（字节）|
|content_type|string|true|none|Content Type|文件 MIME 类型|
|upload_time|string|true|none|Upload Time|上传时间|

<h2 id="tocS_GetVNCConnectionRequest">GetVNCConnectionRequest</h2>

<a id="schemagetvncconnectionrequest"></a>
<a id="schema_GetVNCConnectionRequest"></a>
<a id="tocSgetvncconnectionrequest"></a>
<a id="tocsgetvncconnectionrequest"></a>

```json
{
  "id": "string"
}

```

GetVNCConnectionRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|id|string|true|none|Id|主机ID (host_rec.id)|

<h2 id="tocS_HTTPValidationError">HTTPValidationError</h2>

<a id="schemahttpvalidationerror"></a>
<a id="schema_HTTPValidationError"></a>
<a id="tocShttpvalidationerror"></a>
<a id="tocshttpvalidationerror"></a>

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}

```

HTTPValidationError

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|detail|[[ValidationError](#schemavalidationerror)]|false|none|Detail|none|

<h2 id="tocS_HardwareReportResponse">HardwareReportResponse</h2>

<a id="schemahardwarereportresponse"></a>
<a id="schema_HardwareReportResponse"></a>
<a id="tocShardwarereportresponse"></a>
<a id="tocshardwarereportresponse"></a>

```json
{
  "status": "string",
  "hw_rec_id": 0,
  "diff_state": 0,
  "diff_details": {},
  "message": "string"
}

```

HardwareReportResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|status|string|true|none|Status|状态 (first_report/hardware_changed/no_change)|
|hw_rec_id|any|false|none|Hw Rec Id|硬件记录ID|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|diff_state|any|false|none|Diff State|差异状态 (1-版本号变化, 2-内容更改)|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|diff_details|any|false|none|Diff Details|差异详情|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|object|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|message|string|true|none|Message|响应消息|

<h2 id="tocS_OtaConfigItem">OtaConfigItem</h2>

<a id="schemaotaconfigitem"></a>
<a id="schema_OtaConfigItem"></a>
<a id="tocSotaconfigitem"></a>
<a id="tocsotaconfigitem"></a>

```json
{
  "conf_name": "string",
  "conf_ver": "string",
  "conf_url": "string",
  "conf_md5": "string"
}

```

OtaConfigItem

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_name|any|false|none|Conf Name|配置名称|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_ver|any|false|none|Conf Ver|配置版本|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_url|any|false|none|Conf Url|OTA 包下载 URL|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|conf_md5|any|false|none|Conf Md5|OTA 包 MD5 校验值|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_QueryAvailableHostsRequest">QueryAvailableHostsRequest</h2>

<a id="schemaqueryavailablehostsrequest"></a>
<a id="schema_QueryAvailableHostsRequest"></a>
<a id="tocSqueryavailablehostsrequest"></a>
<a id="tocsqueryavailablehostsrequest"></a>

```json
{
  "tc_id": "string",
  "cycle_name": "string",
  "user_name": "string",
  "page_size": 20,
  "last_id": "string"
}

```

QueryAvailableHostsRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|tc_id|string|true|none|Tc Id|测试用例ID|
|cycle_name|string|true|none|Cycle Name|测试周期名称|
|user_name|string|true|none|User Name|用户名|
|page_size|integer|false|none|Page Size|每页数量（1-100）|
|last_id|any|false|none|Last Id|上一页最后一条记录的 id。首次请求为 null，后续请求需要传入上一页最后一条记录的 host_rec_id|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_ReleaseHostsRequest">ReleaseHostsRequest</h2>

<a id="schemareleasehostsrequest"></a>
<a id="schema_ReleaseHostsRequest"></a>
<a id="tocSreleasehostsrequest"></a>
<a id="tocsreleasehostsrequest"></a>

```json
{
  "user_id": "string",
  "host_list": [
    "string"
  ]
}

```

ReleaseHostsRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|user_id|string|true|none|User Id|用户ID|
|host_list|[string]|true|none|Host List|主机ID列表|

<h2 id="tocS_ReleaseHostsResponse">ReleaseHostsResponse</h2>

<a id="schemareleasehostsresponse"></a>
<a id="schema_ReleaseHostsResponse"></a>
<a id="tocSreleasehostsresponse"></a>
<a id="tocsreleasehostsresponse"></a>

```json
{
  "updated_count": 0,
  "user_id": "string",
  "host_list": [
    "string"
  ]
}

```

ReleaseHostsResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|updated_count|integer|true|none|Updated Count|更新的记录数（逻辑删除）|
|user_id|string|true|none|User Id|用户ID|
|host_list|[string]|true|none|Host List|主机ID列表|

<h2 id="tocS_Result_AdminApprHostDetailResponse_">Result_AdminApprHostDetailResponse_</h2>

<a id="schemaresult_adminapprhostdetailresponse_"></a>
<a id="schema_Result_AdminApprHostDetailResponse_"></a>
<a id="tocSresult_adminapprhostdetailresponse_"></a>
<a id="tocsresult_adminapprhostdetailresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "mg_id": "string",
    "mac": "string",
    "ip": "string",
    "username": "string",
    "***REMOVED***word": "string",
    "port": 0,
    "host_state": 0,
    "hw_list": [
      {
        "created_time": "2019-08-24T14:15:22Z",
        "hw_info": {}
      }
    ]
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AdminApprHostDetailResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AdminApprHostDetailResponse](#schemaadminapprhostdetailresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_AdminApprHostListResponse_">Result_AdminApprHostListResponse_</h2>

<a id="schemaresult_adminapprhostlistresponse_"></a>
<a id="schema_Result_AdminApprHostListResponse_"></a>
<a id="tocSresult_adminapprhostlistresponse_"></a>
<a id="tocsresult_adminapprhostlistresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_id": "string",
        "mg_id": "string",
        "mac_addr": "string",
        "host_state": 0,
        "subm_time": "2019-08-24T14:15:22Z",
        "diff_state": 0
      }
    ],
    "total": 0,
    "page": 0,
    "page_size": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AdminApprHostListResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AdminApprHostListResponse](#schemaadminapprhostlistresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_AdminHostDetailResponse_">Result_AdminHostDetailResponse_</h2>

<a id="schemaresult_adminhostdetailresponse_"></a>
<a id="schema_Result_AdminHostDetailResponse_"></a>
<a id="tocSresult_adminhostdetailresponse_"></a>
<a id="tocsresult_adminhostdetailresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "mg_id": "string",
    "mac": "string",
    "ip": "string",
    "username": "string",
    "***REMOVED***word": "string",
    "port": 0,
    "hw_list": [
      {
        "hw_info": {},
        "appr_time": "2019-08-24T14:15:22Z"
      }
    ]
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AdminHostDetailResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AdminHostDetailResponse](#schemaadminhostdetailresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_AdminHostExecLogListResponse_">Result_AdminHostExecLogListResponse_</h2>

<a id="schemaresult_adminhostexecloglistresponse_"></a>
<a id="schema_Result_AdminHostExecLogListResponse_"></a>
<a id="tocSresult_adminhostexecloglistresponse_"></a>
<a id="tocsresult_adminhostexecloglistresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "logs": [
      {
        "log_id": "string",
        "exec_date": "string",
        "exec_time": "string",
        "tc_id": "string",
        "use_by": "string",
        "case_state": 0,
        "result_msg": "string",
        "log_url": "string"
      }
    ],
    "total": 0,
    "page": 0,
    "page_size": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AdminHostExecLogListResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AdminHostExecLogListResponse](#schemaadminhostexecloglistresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_AdminHostListResponse_">Result_AdminHostListResponse_</h2>

<a id="schemaresult_adminhostlistresponse_"></a>
<a id="schema_Result_AdminHostListResponse_"></a>
<a id="tocSresult_adminhostlistresponse_"></a>
<a id="tocsresult_adminhostlistresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_id": "string",
        "username": "string",
        "mg_id": "string",
        "mac": "string",
        "use_by": "string",
        "host_state": 0,
        "appr_state": 0
      }
    ],
    "total": 0,
    "page": 0,
    "page_size": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AdminHostListResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AdminHostListResponse](#schemaadminhostlistresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_AdminOtaDeployResponse_">Result_AdminOtaDeployResponse_</h2>

<a id="schemaresult_adminotadeployresponse_"></a>
<a id="schema_Result_AdminOtaDeployResponse_"></a>
<a id="tocSresult_adminotadeployresponse_"></a>
<a id="tocsresult_adminotadeployresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": "string",
    "conf_ver": "string",
    "conf_name": "string",
    "conf_url": "string",
    "conf_md5": "string",
    "broadcast_count": 0
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AdminOtaDeployResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AdminOtaDeployResponse](#schemaadminotadeployresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_AdminOtaListResponse_">Result_AdminOtaListResponse_</h2>

<a id="schemaresult_adminotalistresponse_"></a>
<a id="schema_Result_AdminOtaListResponse_"></a>
<a id="tocSresult_adminotalistresponse_"></a>
<a id="tocsresult_adminotalistresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "ota_configs": [
      {
        "id": "string",
        "conf_ver": "string",
        "conf_name": "string",
        "conf_url": "string",
        "conf_md5": "string"
      }
    ],
    "total": 0
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AdminOtaListResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AdminOtaListResponse](#schemaadminotalistresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_AvailableHostsListResponse_">Result_AvailableHostsListResponse_</h2>

<a id="schemaresult_availablehostslistresponse_"></a>
<a id="schema_Result_AvailableHostsListResponse_"></a>
<a id="tocSresult_availablehostslistresponse_"></a>
<a id="tocsresult_availablehostslistresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_rec_id": "string",
        "hardware_id": "string",
        "user_name": "string",
        "host_ip": "string",
        "appr_state": 0,
        "host_state": 0
      }
    ],
    "total": 0,
    "page_size": 0,
    "has_next": true,
    "last_id": "string"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[AvailableHostsListResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[AvailableHostsListResponse](#schemaavailablehostslistresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_FileUploadResponse_">Result_FileUploadResponse_</h2>

<a id="schemaresult_fileuploadresponse_"></a>
<a id="schema_Result_FileUploadResponse_"></a>
<a id="tocSresult_fileuploadresponse_"></a>
<a id="tocsresult_fileuploadresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "file_id": "string",
    "filename": "string",
    "saved_filename": "string",
    "file_url": "string",
    "file_size": 0,
    "content_type": "string",
    "upload_time": "string"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[FileUploadResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[FileUploadResponse](#schemafileuploadresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_HardwareReportResponse_">Result_HardwareReportResponse_</h2>

<a id="schemaresult_hardwarereportresponse_"></a>
<a id="schema_Result_HardwareReportResponse_"></a>
<a id="tocSresult_hardwarereportresponse_"></a>
<a id="tocsresult_hardwarereportresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "status": "string",
    "hw_rec_id": 0,
    "diff_state": 0,
    "diff_details": {},
    "message": "string"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[HardwareReportResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[HardwareReportResponse](#schemahardwarereportresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_List_OtaConfigItem__">Result_List_OtaConfigItem__</h2>

<a id="schemaresult_list_otaconfigitem__"></a>
<a id="schema_Result_List_OtaConfigItem__"></a>
<a id="tocSresult_list_otaconfigitem__"></a>
<a id="tocsresult_list_otaconfigitem__"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": [
    {
      "conf_name": "string",
      "conf_ver": "string",
      "conf_url": "string",
      "conf_md5": "string"
    }
  ],
  "timestamp": "string",
  "locale": "string"
}

```

Result[List[app.schemas.host.OtaConfigItem]]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[[OtaConfigItem](#schemaotaconfigitem)]|true|none|Data|响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_ReleaseHostsResponse_">Result_ReleaseHostsResponse_</h2>

<a id="schemaresult_releasehostsresponse_"></a>
<a id="schema_Result_ReleaseHostsResponse_"></a>
<a id="tocSresult_releasehostsresponse_"></a>
<a id="tocsresult_releasehostsresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "updated_count": 0,
    "user_id": "string",
    "host_list": [
      "string"
    ]
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[ReleaseHostsResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[ReleaseHostsResponse](#schemareleasehostsresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_RetryVNCListResponse_">Result_RetryVNCListResponse_</h2>

<a id="schemaresult_retryvnclistresponse_"></a>
<a id="schema_Result_RetryVNCListResponse_"></a>
<a id="tocSresult_retryvnclistresponse_"></a>
<a id="tocsresult_retryvnclistresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "hosts": [
      {
        "host_id": "string",
        "host_ip": "string",
        "user_name": "string"
      }
    ],
    "total": 0
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[RetryVNCListResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[RetryVNCListResponse](#schemaretryvnclistresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_TestCaseReportResponse_">Result_TestCaseReportResponse_</h2>

<a id="schemaresult_testcasereportresponse_"></a>
<a id="schema_Result_TestCaseReportResponse_"></a>
<a id="tocSresult_testcasereportresponse_"></a>
<a id="tocsresult_testcasereportresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "host_id": "string",
    "tc_id": "string",
    "case_state": 0,
    "result_msg": "string",
    "log_url": "string",
    "updated": true
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[TestCaseReportResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[TestCaseReportResponse](#schematestcasereportresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_VNCConnectionInfo_">Result_VNCConnectionInfo_</h2>

<a id="schemaresult_vncconnectioninfo_"></a>
<a id="schema_Result_VNCConnectionInfo_"></a>
<a id="tocSresult_vncconnectioninfo_"></a>
<a id="tocsresult_vncconnectioninfo_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "ip": "string",
    "port": "string",
    "username": "string",
    "***REMOVED***word": "string"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[VNCConnectionInfo]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[VNCConnectionInfo](#schemavncconnectioninfo)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_VNCConnectionResponse_">Result_VNCConnectionResponse_</h2>

<a id="schemaresult_vncconnectionresponse_"></a>
<a id="schema_Result_VNCConnectionResponse_"></a>
<a id="tocSresult_vncconnectionresponse_"></a>
<a id="tocsresult_vncconnectionresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "host_id": "string",
    "connection_status": "string",
    "connection_time": "2019-08-24T14:15:22Z"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[VNCConnectionResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[VNCConnectionResponse](#schemavncconnectionresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_RetryVNCHostInfo">RetryVNCHostInfo</h2>

<a id="schemaretryvnchostinfo"></a>
<a id="schema_RetryVNCHostInfo"></a>
<a id="tocSretryvnchostinfo"></a>
<a id="tocsretryvnchostinfo"></a>

```json
{
  "host_id": "string",
  "host_ip": "string",
  "user_name": "string"
}

```

RetryVNCHostInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|string|true|none|Host Id|主机ID (host_rec.id)|
|host_ip|string|true|none|Host Ip|主机IP|
|user_name|string|true|none|User Name|主机账号 (host_acct)|

<h2 id="tocS_RetryVNCListResponse">RetryVNCListResponse</h2>

<a id="schemaretryvnclistresponse"></a>
<a id="schema_RetryVNCListResponse"></a>
<a id="tocSretryvnclistresponse"></a>
<a id="tocsretryvnclistresponse"></a>

```json
{
  "hosts": [
    {
      "host_id": "string",
      "host_ip": "string",
      "user_name": "string"
    }
  ],
  "total": 0
}

```

RetryVNCListResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|hosts|[[RetryVNCHostInfo](#schemaretryvnchostinfo)]|true|none|Hosts|重试 VNC 主机列表|
|total|integer|true|none|Total|主机总数|

<h2 id="tocS_SuccessResponse">SuccessResponse</h2>

<a id="schemasuccessresponse"></a>
<a id="schema_SuccessResponse"></a>
<a id="tocSsuccessresponse"></a>
<a id="tocssuccessresponse"></a>

```json
{}

```

### 属性

*None*

<h2 id="tocS_TestCaseReportRequest">TestCaseReportRequest</h2>

<a id="schematestcasereportrequest"></a>
<a id="schema_TestCaseReportRequest"></a>
<a id="tocStestcasereportrequest"></a>
<a id="tocstestcasereportrequest"></a>

```json
{
  "log_url": "https://www.aaa.com/xxxx.log",
  "result_msg": "{\"code\":\"200\",\"msg\":\"ok\"}",
  "state": 2,
  "tc_id": "absdf1234"
}

```

TestCaseReportRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|tc_id|string|true|none|Tc Id|测试用例ID|
|state|integer|true|none|State|执行状态;0-空闲 1-启动 2-成功 3-失败|
|result_msg|any|false|none|Result Msg|结果消息|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|log_url|any|false|none|Log Url|日志文件URL|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_TestCaseReportResponse">TestCaseReportResponse</h2>

<a id="schematestcasereportresponse"></a>
<a id="schema_TestCaseReportResponse"></a>
<a id="tocStestcasereportresponse"></a>
<a id="tocstestcasereportresponse"></a>

```json
{
  "host_id": "string",
  "tc_id": "string",
  "case_state": 0,
  "result_msg": "string",
  "log_url": "string",
  "updated": true
}

```

TestCaseReportResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|string|true|none|Host Id|主机ID|
|tc_id|string|true|none|Tc Id|测试用例ID|
|case_state|integer|true|none|Case State|case执行状态;0-空闲 1-启动 2-成功 3-失败|
|result_msg|any|false|none|Result Msg|结果消息|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|log_url|any|false|none|Log Url|日志文件URL|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|updated|boolean|true|none|Updated|是否成功更新|

<h2 id="tocS_VNCConnectionInfo">VNCConnectionInfo</h2>

<a id="schemavncconnectioninfo"></a>
<a id="schema_VNCConnectionInfo"></a>
<a id="tocSvncconnectioninfo"></a>
<a id="tocsvncconnectioninfo"></a>

```json
{
  "ip": "string",
  "port": "string",
  "username": "string",
  "***REMOVED***word": "string"
}

```

VNCConnectionInfo

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|ip|string|true|none|Ip|VNC服务器IP地址|
|port|string|true|none|Port|VNC服务端口|
|username|string|true|none|Username|连接用户名|
|***REMOVED***word|string|true|none|Password|连接密码|

<h2 id="tocS_VNCConnectionReport">VNCConnectionReport</h2>

<a id="schemavncconnectionreport"></a>
<a id="schema_VNCConnectionReport"></a>
<a id="tocSvncconnectionreport"></a>
<a id="tocsvncconnectionreport"></a>

```json
{
  "user_id": "string",
  "tc_id": "string",
  "cycle_name": "string",
  "user_name": "string",
  "host_id": "string",
  "connection_status": "string",
  "connection_time": "2019-08-24T14:15:22Z"
}

```

VNCConnectionReport

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|user_id|string|true|none|User Id|用户ID|
|tc_id|string|true|none|Tc Id|执行测试ID|
|cycle_name|string|true|none|Cycle Name|周期名称|
|user_name|string|true|none|User Name|用户名称|
|host_id|string|true|none|Host Id|主机ID|
|connection_status|string|true|none|Connection Status|连接状态 (success/failed)|
|connection_time|string(date-time)|true|none|Connection Time|连接时间|

<h2 id="tocS_VNCConnectionResponse">VNCConnectionResponse</h2>

<a id="schemavncconnectionresponse"></a>
<a id="schema_VNCConnectionResponse"></a>
<a id="tocSvncconnectionresponse"></a>
<a id="tocsvncconnectionresponse"></a>

```json
{
  "host_id": "string",
  "connection_status": "string",
  "connection_time": "2019-08-24T14:15:22Z"
}

```

VNCConnectionResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_id|string|true|none|Host Id|主机ID|
|connection_status|string|true|none|Connection Status|连接状态|
|connection_time|string(date-time)|true|none|Connection Time|连接时间|

<h2 id="tocS_ValidationError">ValidationError</h2>

<a id="schemavalidationerror"></a>
<a id="schema_ValidationError"></a>
<a id="tocSvalidationerror"></a>
<a id="tocsvalidationerror"></a>

```json
{
  "loc": [
    "string"
  ],
  "msg": "string",
  "type": "string"
}

```

ValidationError

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|loc|[anyOf]|true|none|Location|none|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|msg|string|true|none|Message|none|
|type|string|true|none|Error Type|none|

<h2 id="tocS_AdminLoginRequest">AdminLoginRequest</h2>

<a id="schemaadminloginrequest"></a>
<a id="schema_AdminLoginRequest"></a>
<a id="tocSadminloginrequest"></a>
<a id="tocsadminloginrequest"></a>

```json
{
  "***REMOVED***word": "***REMOVED***",
  "username": "admin"
}

```

AdminLoginRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|username|string|true|none|Username|用户名|
|***REMOVED***word|string|true|none|Password|密码|

<h2 id="tocS_AutoRefreshTokenRequest">AutoRefreshTokenRequest</h2>

<a id="schemaautorefreshtokenrequest"></a>
<a id="schema_AutoRefreshTokenRequest"></a>
<a id="tocSautorefreshtokenrequest"></a>
<a id="tocsautorefreshtokenrequest"></a>

```json
{
  "auto_renew": true,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

```

AutoRefreshTokenRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|refresh_token|string|true|none|Refresh Token|当前刷新令牌|
|auto_renew|boolean|false|none|Auto Renew|是否自动续期 refresh_token|

<h2 id="tocS_DeviceLoginRequest">DeviceLoginRequest</h2>

<a id="schemadeviceloginrequest"></a>
<a id="schema_DeviceLoginRequest"></a>
<a id="tocSdeviceloginrequest"></a>
<a id="tocsdeviceloginrequest"></a>

```json
{
  "host_ip": "192.168.1.100",
  "mg_id": "device-12345",
  "username": "root"
}

```

DeviceLoginRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mg_id|string|true|none|Mg Id|唯一引导ID|
|host_ip|string|true|none|Host Ip|主机IP地址|
|username|string|true|none|Username|主机账号|

<h2 id="tocS_IntrospectRequest">IntrospectRequest</h2>

<a id="schemaintrospectrequest"></a>
<a id="schema_IntrospectRequest"></a>
<a id="tocSintrospectrequest"></a>
<a id="tocsintrospectrequest"></a>

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

```

IntrospectRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|token|string|true|none|Token|待验证的令牌|

<h2 id="tocS_IntrospectResponse">IntrospectResponse</h2>

<a id="schemaintrospectresponse"></a>
<a id="schema_IntrospectResponse"></a>
<a id="tocSintrospectresponse"></a>
<a id="tocsintrospectresponse"></a>

```json
{
  "active": true,
  "exp": 1640995200,
  "token_type": "access",
  "user_id": "1",
  "username": "admin"
}

```

IntrospectResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|active|boolean|true|none|Active|令牌是否有效|
|username|any|false|none|Username|用户名|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|user_id|any|false|none|User Id|用户ID|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|exp|any|false|none|Exp|过期时间戳|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|token_type|any|false|none|Token Type|令牌类型|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|user_type|any|false|none|User Type|用户类型（admin/device）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|mg_id|any|false|none|Mg Id|设备管理ID|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|host_ip|any|false|none|Host Ip|主机IP|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|sub|any|false|none|Sub|Subject（用户/设备ID）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|error|any|false|none|Error|错误信息（当 active=False 时）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_LoginResponse">LoginResponse</h2>

<a id="schemaloginresponse"></a>
<a id="schema_LoginResponse"></a>
<a id="tocSloginresponse"></a>
<a id="tocsloginresponse"></a>

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "refresh_expires_in": 604800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

```

LoginResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|access_token|string|true|none|Access Token|访问令牌|
|token|any|false|none|Token|访问令牌兼容字段（与 access_token 相同，保留用于向后兼容）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|refresh_token|any|false|none|Refresh Token|刷新令牌|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

continued

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|token_type|string|false|none|Token Type|令牌类型|
|expires_in|integer|true|none|Expires In|过期时间（秒）|
|refresh_expires_in|any|false|none|Refresh Expires In|刷新令牌过期时间（秒）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_LogoutRequest">LogoutRequest</h2>

<a id="schemalogoutrequest"></a>
<a id="schema_LogoutRequest"></a>
<a id="tocSlogoutrequest"></a>
<a id="tocslogoutrequest"></a>

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

```

LogoutRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|token|string|true|none|Token|访问令牌|

<h2 id="tocS_RefreshTokenRequest">RefreshTokenRequest</h2>

<a id="schemarefreshtokenrequest"></a>
<a id="schema_RefreshTokenRequest"></a>
<a id="tocSrefreshtokenrequest"></a>
<a id="tocsrefreshtokenrequest"></a>

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

```

RefreshTokenRequest

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|refresh_token|string|true|none|Refresh Token|刷新令牌|

<h2 id="tocS_Result_IntrospectResponse_">Result_IntrospectResponse_</h2>

<a id="schemaresult_introspectresponse_"></a>
<a id="schema_Result_IntrospectResponse_"></a>
<a id="tocSresult_introspectresponse_"></a>
<a id="tocsresult_introspectresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "active": true,
    "exp": 1640995200,
    "token_type": "access",
    "user_id": "1",
    "username": "admin"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[IntrospectResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[IntrospectResponse](#schemaintrospectresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_LoginResponse_">Result_LoginResponse_</h2>

<a id="schemaresult_loginresponse_"></a>
<a id="schema_Result_LoginResponse_"></a>
<a id="tocSresult_loginresponse_"></a>
<a id="tocsresult_loginresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "refresh_expires_in": 604800,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[LoginResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[LoginResponse](#schemaloginresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_Result_TokenResponse_">Result_TokenResponse_</h2>

<a id="schemaresult_tokenresponse_"></a>
<a id="schema_Result_TokenResponse_"></a>
<a id="tocSresult_tokenresponse_"></a>
<a id="tocsresult_tokenresponse_"></a>

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "refresh_expires_in": 604800,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "timestamp": "string",
  "locale": "string"
}

```

Result[TokenResponse]

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|code|integer|false|none|Code|响应码|
|message|string|false|none|Message|响应消息|
|data|[TokenResponse](#schematokenresponse)|true|none||响应数据|
|timestamp|string|false|none|Timestamp|响应时间戳（ISO 8601 格式）|
|locale|any|false|none|Locale|语言代码（用于多语言支持）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|string|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|

<h2 id="tocS_TokenResponse">TokenResponse</h2>

<a id="schematokenresponse"></a>
<a id="schema_TokenResponse"></a>
<a id="tocStokenresponse"></a>
<a id="tocstokenresponse"></a>

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "refresh_expires_in": 604800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

```

TokenResponse

### 属性

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|access_token|string|true|none|Access Token|访问令牌|
|refresh_token|string|true|none|Refresh Token|刷新令牌|
|token_type|string|false|none|Token Type|令牌类型|
|expires_in|integer|true|none|Expires In|过期时间（秒）|
|refresh_expires_in|any|false|none|Refresh Expires In|刷新令牌过期时间（秒）|

anyOf

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|integer|false|none||none|

or

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» *anonymous*|null|false|none||none|
