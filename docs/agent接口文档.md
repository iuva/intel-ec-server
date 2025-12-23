agent 接口根地址：<http://127.0.0.1:8000/api/v1>

#### 1. ek启动上报接口

**接口地址**：`/ek/start/result`  
**请求方法**：`POST`  
**功能描述**：发起ek测试后进行调用

**请求参数**：

```json
{
  "tool": "execution_kit",
  "timestamp": "",
  "session_id": "",
  "event": {
      "type": "start",
      "status_code": 0,
      "details": {
          "tc_id": "",
          "test_cycle": "",
          "user": ""
      }
  }
}
```

**请求字段说明**：

- `status_code`: 0成功、1异常
- `tc_id`: 测试用例 ID
- `test_cycle`: 测试周期名称
- `user`: 用户名

**响应格式**：

```json
{
 "code": 0,
 "msg": "success"
}
```

**响应字段说明**：

- `code`:  0成功、1异常
- `msg`:  描述

#### 2. ek测试结果上报接口

**接口地址**：`/ek/test/result`  
**请求方法**：`POST`  
**功能描述**：ek 测试有结果时进行调用

**请求参数**：

```json
{
  "tool": "execution_kit",
  "timestamp": "",
  "session_id": "",
  "event": {
      "type": "end",
      "status_code": 0,
      "details": {
          "tc_id": "",
          "test_cycle": "",
          "user": ""
      }
  }
}
```

**请求字段说明**：

- `status_code`: 0成功、1异常
- `tc_id`: 测试用例 ID
- `test_cycle`: 测试周期名称
- `user`: 用户名

**响应格式**：

```json
{
 "code": 0,
 "msg": "success"
}
```

**响应字段说明**：

- `code`:  0成功、1异常
- `msg`:  描述

#### 3. 硬件信息上报接口

**接口地址**：`/dmr/info/result`  
**请求方法**：`POST`  
**功能描述**：ek 测试有结果时进行调用

**请求参数**：

```json
{
  "tool": "dmr_config_schema",
  "timestamp": "",
  "event": {
      "type": "completion",
      "status_code": 0,
      "details": {
          "mode": "sut",
          "output_file": "",
          "output_data": ""
      }
  }
}
```

**请求字段说明**：

- `status_code`: 0成功、1异常
- `output_file`: 结果文件地址
- `output_data`: 结果数据

**响应格式**：

```json
{
 "code": 0,
 "msg": "success"
}
```

**响应字段说明**：

- `code`:  0成功、1异常
- `msg`:  描述
