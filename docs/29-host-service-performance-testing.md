# Host Service 性能测试文档

## 📋 目录

- [性能测试概述](#性能测试概述)
- [性能指标定义](#性能指标定义)
- [测试环境准备](#测试环境准备)
- [测试工具和方法](#测试工具和方法)
- [HTTP 接口性能测试](#http-接口性能测试)
- [WebSocket 性能测试](#websocket-性能测试)
- [数据库性能测试](#数据库性能测试)
- [负载测试](#负载测试)
- [压力测试](#压力测试)
- [性能基准](#性能基准)
- [监控指标说明](#监控指标说明)
- [性能优化建议](#性能优化建议)

---

## 性能测试概述

### 测试目标

1. **响应时间**: 验证接口响应时间是否符合要求
2. **吞吐量**: 测试系统在正常和峰值负载下的处理能力
3. **并发能力**: 验证系统同时处理多个请求的能力
4. **资源使用**: 监控 CPU、内存、数据库连接等资源使用情况
5. **稳定性**: 验证系统在长时间运行下的稳定性

### 测试范围

| 测试类型 | 测试内容 | 优先级 |
|---------|---------|--------|
| HTTP 接口性能 | 所有 REST API 接口的响应时间和吞吐量 | 高 |
| WebSocket 性能 | 连接建立时间、消息延迟、并发连接数 | 高 |
| 数据库性能 | 查询响应时间、连接池使用情况 | 中 |
| 文件操作性能 | 文件上传/下载速度、断点续传性能 | 中 |
| 系统资源 | CPU、内存、网络带宽使用情况 | 中 |
| 长时间运行 | 内存泄漏、性能衰退检测 | 低 |

---

## 性能指标定义

### 1. 响应时间指标

| 指标 | 定义 | 目标值 | 说明 |
|------|------|--------|------|
| **平均响应时间** | 所有请求的平均响应时间 | < 200ms | 正常负载下 |
| **P50 响应时间** | 50% 的请求响应时间 | < 150ms | 中位数 |
| **P95 响应时间** | 95% 的请求响应时间 | < 500ms | 大部分请求 |
| **P99 响应时间** | 99% 的请求响应时间 | < 1000ms | 极端情况 |
| **最大响应时间** | 最慢请求的响应时间 | < 2000ms | 异常情况 |

### 2. 吞吐量指标

| 指标 | 定义 | 目标值 | 说明 |
|------|------|--------|------|
| **QPS** | 每秒查询数（Queries Per Second） | > 1000 | 正常负载 |
| **RPS** | 每秒请求数（Requests Per Second） | > 500 | 正常负载 |
| **并发用户数** | 同时在线用户数 | > 100 | 正常负载 |
| **峰值 QPS** | 峰值负载下的 QPS | > 2000 | 峰值负载 |

### 3. 资源使用指标

| 指标 | 定义 | 目标值 | 说明 |
|------|------|--------|------|
| **CPU 使用率** | CPU 使用百分比 | < 70% | 正常负载 |
| **内存使用率** | 内存使用百分比 | < 80% | 正常负载 |
| **数据库连接数** | 活跃数据库连接数 | < 80% | 连接池限制 |
| **网络带宽** | 网络带宽使用率 | < 80% | 正常负载 |

### 4. 错误率指标

| 指标 | 定义 | 目标值 | 说明 |
|------|------|--------|------|
| **错误率** | 错误请求占总请求的百分比 | < 0.1% | 正常负载 |
| **超时率** | 超时请求占总请求的百分比 | < 0.01% | 正常负载 |
| **5xx 错误率** | 服务器错误占总请求的百分比 | < 0.01% | 正常负载 |

---

## 测试环境准备

### 1. 测试环境配置

```bash
# 测试服务器配置
CPU: 4 核
内存: 8GB
磁盘: 100GB SSD
网络: 1Gbps

# 服务配置
Host Service: http://localhost:8003
Gateway Service: http://localhost:8000
Database: MariaDB 10.11
Redis: Redis 6.0+
```

### 2. 测试数据准备

```bash
# 创建测试数据脚本
# scripts/prepare_test_data.sh

# 准备测试主机数据
# 准备测试用户数据
# 准备测试文件数据
```

### 3. 监控工具配置

```bash
# Prometheus 配置
PROMETHEUS_URL="http://localhost:9090"

# Grafana 配置
GRAFANA_URL="http://localhost:3000"

# 查看 Prometheus 指标
curl http://localhost:8003/metrics
```

---

## 测试工具和方法

### 1. Apache Bench (ab)

**安装**

```bash
# Ubuntu/Debian
sudo apt-get install apache2-utils

# macOS
brew install httpd
```

**使用示例**

```bash
# 基本用法
ab -n 1000 -c 10 http://localhost:8003/api/v1/host/hosts/available

# 参数说明
# -n: 总请求数
# -c: 并发数
# -t: 测试时间（秒）
# -p: POST 数据文件
# -T: Content-Type
```

### 2. wrk

**安装**

```bash
# Ubuntu/Debian
sudo apt-get install wrk

# macOSt
brew install wrk
```

**使用示例**

```bash
# 基本用法
wrk -t4 -c100 -d30s http://localhost:8003/api/v1/host/hosts/available

# 参数说明
# -t: 线程数
# -c: 连接数
# -d: 测试持续时间
# -s: Lua 脚本文件
```

### 3. Locust

**安装**

```bash
pip install locust
```

**使用示例**

```bash
# 启动 Locust
locust -f locustfile.py --host=http://localhost:8003

# 访问 Web UI
# http://localhost:8089
```

### 4. k6

**安装**

```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**使用示例**

```bash
# 运行测试脚本
k6 run performance_test.js
```

### 5. Python 测试脚本

使用 `asyncio` 和 `aiohttp` 编写自定义性能测试脚本。

---

## HTTP 接口性能测试

### 1. 查询可用主机列表

**测试脚本 (k6)**

```javascript
// tests/performance/query_available_hosts.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // 逐步增加到 50 用户
    { duration: '1m', target: 50 },    // 保持 50 用户 1 分钟
    { duration: '30s', target: 100 },  // 逐步增加到 100 用户
    { duration: '1m', target: 100 },   // 保持 100 用户 1 分钟
    { duration: '30s', target: 0 },    // 逐步减少到 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% 请求 < 500ms, 99% < 1000ms
    http_req_failed: ['rate<0.01'],                 // 错误率 < 1%
  },
};

export default function () {
  const url = 'http://localhost:8003/api/v1/host/hosts/available';
  const payload = JSON.stringify({
    tc_id: 'test_case_001',
    cycle_name: 'test_cycle_001',
    user_name: 'test_user',
    page_size: 20,
    last_id: null,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(url, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'response time < 1000ms': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}
```

**运行测试**

```bash
k6 run tests/performance/query_available_hosts.js
```

**预期结果**

- 平均响应时间: < 200ms
- P95 响应时间: < 500ms
- P99 响应时间: < 1000ms
- 错误率: < 0.1%
- QPS: > 100

---

### 2. 获取 VNC 连接信息

**测试脚本 (Locust)**

```python
# tests/performance/vnc_connect_test.py
from locust import HttpUser, task, between
import json

class VNCConnectUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """测试开始前执行"""
        self.host_id = "1846486359367955051"

    @task(3)
    def get_vnc_connection(self):
        """获取 VNC 连接信息"""
        url = "/api/v1/host/vnc/connect"
        payload = {
            "id": self.host_id
        }
        
        with self.client.post(
            url,
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
```

**运行测试**

```bash
locust -f tests/performance/vnc_connect_test.py --host=http://localhost:8003
```

---

### 3. 文件上传性能测试

**测试脚本 (Python)**

```python
# tests/performance/file_upload_test.py
import asyncio
import aiohttp
import time
import os
from statistics import mean, median

async def upload_file(session, url, file_path, token):
    """上传文件并测量时间"""
    start_time = time.time()
    
    with open(file_path, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('file', f, filename=os.path.basename(file_path))
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        async with session.post(url, data=data, headers=headers) as response:
            elapsed = time.time() - start_time
            return {
                'status': response.status,
                'duration': elapsed,
                'size': os.path.getsize(file_path)
            }

async def run_upload_test(num_requests=100, concurrency=10):
    """运行文件上传性能测试"""
    url = "http://localhost:8003/api/v1/host/file/upload"
    token = "YOUR_TOKEN"
    file_path = "test_file_1mb.txt"  # 1MB 测试文件
    
    # 创建测试文件
    with open(file_path, 'wb') as f:
        f.write(b'0' * 1024 * 1024)  # 1MB
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_upload():
            async with semaphore:
                return await upload_file(session, url, file_path, token)
        
        tasks = [bounded_upload() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    # 分析结果
    durations = [r['duration'] for r in results if r['status'] == 200]
    sizes = [r['size'] for r in results if r['status'] == 200]
    
    if durations:
        avg_duration = mean(durations)
        median_duration = median(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        total_size = sum(sizes)
        throughput = total_size / sum(durations)  # bytes/sec
        
        print(f"\n文件上传性能测试结果:")
        print(f"  总请求数: {num_requests}")
        print(f"  成功请求: {len(durations)}")
        print(f"  平均响应时间: {avg_duration:.3f}s")
        print(f"  中位数响应时间: {median_duration:.3f}s")
        print(f"  最大响应时间: {max_duration:.3f}s")
        print(f"  最小响应时间: {min_duration:.3f}s")
        print(f"  平均吞吐量: {throughput / 1024 / 1024:.2f} MB/s")
    
    # 清理测试文件
    os.remove(file_path)

if __name__ == "__main__":
    asyncio.run(run_upload_test(num_requests=100, concurrency=10))
```

**运行测试**

```bash
python tests/performance/file_upload_test.py
```

---

### 4. 文件下载性能测试（断点续传）

**测试脚本 (Python)**

```python
# tests/performance/file_download_test.py
import asyncio
import aiohttp
import time
from statistics import mean

async def download_file(session, url, token, range_header=None):
    """下载文件并测量时间"""
    start_time = time.time()
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    if range_header:
        headers['Range'] = range_header
    
    async with session.get(url, headers=headers) as response:
        content = await response.read()
        elapsed = time.time() - start_time
        
        return {
            'status': response.status,
            'duration': elapsed,
            'size': len(content),
            'content_range': response.headers.get('Content-Range'),
            'accept_ranges': response.headers.get('Accept-Ranges')
        }

async def run_download_test(num_requests=100, concurrency=10):
    """运行文件下载性能测试"""
    url = "http://localhost:8003/api/v1/host/file/test_file_10mb.txt"
    token = "YOUR_TOKEN"
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_download():
            async with semaphore:
                return await download_file(session, url, token)
        
        tasks = [bounded_download() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    # 分析结果
    durations = [r['duration'] for r in results if r['status'] in [200, 206]]
    
    if durations:
        avg_duration = mean(durations)
        total_size = sum(r['size'] for r in results if r['status'] in [200, 206])
        throughput = total_size / sum(durations)  # bytes/sec
        
        print(f"\n文件下载性能测试结果:")
        print(f"  总请求数: {num_requests}")
        print(f"  成功请求: {len(durations)}")
        print(f"  平均响应时间: {avg_duration:.3f}s")
        print(f"  平均吞吐量: {throughput / 1024 / 1024:.2f} MB/s")
        
        # 测试断点续传
        print(f"\n断点续传测试:")
        result = await download_file(session, url, token, "bytes=0-1048575")  # 前 1MB
        print(f"  状态码: {result['status']}")
        print(f"  内容范围: {result['content_range']}")
        print(f"  支持范围: {result['accept_ranges']}")

if __name__ == "__main__":
    asyncio.run(run_download_test(num_requests=100, concurrency=10))
```

---

## WebSocket 性能测试

### 1. 连接建立时间测试

**测试脚本 (Python)**

```python
# tests/performance/websocket_connection_test.py
import asyncio
import websockets
import time
from statistics import mean, median

async def test_connection_time(uri, num_tests=100):
    """测试 WebSocket 连接建立时间"""
    connection_times = []
    
    for i in range(num_tests):
        start_time = time.time()
        try:
            async with websockets.connect(uri, ping_interval=None) as ws:
                connection_time = time.time() - start_time
                connection_times.append(connection_time)
                await ws.close()
        except Exception as e:
            print(f"连接失败: {e}")
    
    if connection_times:
        avg_time = mean(connection_times)
        median_time = median(connection_times)
        min_time = min(connection_times)
        max_time = max(connection_times)
        
        print(f"\nWebSocket 连接建立时间测试:")
        print(f"  测试次数: {num_tests}")
        print(f"  成功连接: {len(connection_times)}")
        print(f"  平均时间: {avg_time * 1000:.2f} ms")
        print(f"  中位数时间: {median_time * 1000:.2f} ms")
        print(f"  最小时间: {min_time * 1000:.2f} ms")
        print(f"  最大时间: {max_time * 1000:.2f} ms")
        
        # 验证性能
        assert avg_time < 1.0, f"平均连接时间应该 < 1s，实际: {avg_time:.3f}s"

async def main():
    uri = "ws://localhost:8003/api/v1/host/ws/host?token=YOUR_TOKEN"
    await test_connection_time(uri, num_tests=100)

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 2. 消息吞吐量测试

**测试脚本 (Python)**

```python
# tests/performance/websocket_throughput_test.py
import asyncio
import websockets
import json
import time

async def test_message_throughput(uri, num_messages=1000):
    """测试 WebSocket 消息吞吐量"""
    async with websockets.connect(uri, ping_interval=None) as ws:
        start_time = time.time()
        
        # 发送消息
        for i in range(num_messages):
            message = {"type": "throughput_test", "index": i}
            await ws.send(json.dumps(message))
        
        elapsed_time = time.time() - start_time
        throughput = num_messages / elapsed_time
        
        print(f"\nWebSocket 消息吞吐量测试:")
        print(f"  消息数量: {num_messages}")
        print(f"  总时间: {elapsed_time:.3f}s")
        print(f"  吞吐量: {throughput:.2f} 消息/秒")
        
        # 验证性能
        assert throughput > 100, f"吞吐量应该 > 100 msg/sec，实际: {throughput:.2f}"

async def main():
    uri = "ws://localhost:8003/api/v1/host/ws/host?token=YOUR_TOKEN"
    await test_message_throughput(uri, num_messages=1000)

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 3. 并发连接测试

**测试脚本 (Python)**

```python
# tests/performance/websocket_concurrent_test.py
import asyncio
import websockets
import json
import time

async def concurrent_connection(uri, agent_id, num_messages=100):
    """单个并发连接测试"""
    try:
        async with websockets.connect(uri, ping_interval=None) as ws:
            start_time = time.time()
            
            for i in range(num_messages):
                message = {"type": "concurrent_test", "agent_id": agent_id, "index": i}
                await ws.send(json.dumps(message))
            
            elapsed = time.time() - start_time
            return {
                'agent_id': agent_id,
                'messages': num_messages,
                'duration': elapsed,
                'throughput': num_messages / elapsed
            }
    except Exception as e:
        return {
            'agent_id': agent_id,
            'error': str(e)
        }

async def test_concurrent_connections(num_connections=100, messages_per_connection=100):
    """测试并发 WebSocket 连接"""
    base_uri = "ws://localhost:8003/api/v1/host/ws/host?token=YOUR_TOKEN"
    
    start_time = time.time()
    
    # 创建并发任务
    tasks = [
        concurrent_connection(base_uri, f"agent_{i:03d}", messages_per_connection)
        for i in range(num_connections)
    ]
    
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # 分析结果
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    if successful:
        total_messages = sum(r['messages'] for r in successful)
        total_throughput = total_messages / total_time
        avg_throughput = mean(r['throughput'] for r in successful)
        
        print(f"\n并发 WebSocket 连接测试:")
        print(f"  连接数: {num_connections}")
        print(f"  成功连接: {len(successful)}")
        print(f"  失败连接: {len(failed)}")
        print(f"  总消息数: {total_messages}")
        print(f"  总时间: {total_time:.3f}s")
        print(f"  总吞吐量: {total_throughput:.2f} 消息/秒")
        print(f"  平均单连接吞吐量: {avg_throughput:.2f} 消息/秒")
        
        # 验证性能
        assert total_throughput > 100, f"总吞吐量应该 > 100 msg/sec，实际: {total_throughput:.2f}"

async def main():
    await test_concurrent_connections(num_connections=100, messages_per_connection=100)

if __name__ == "__main__":
    from statistics import mean
    asyncio.run(main())
```

---

## 数据库性能测试

### 1. 查询性能测试

**测试脚本 (Python)**

```python
# tests/performance/database_query_test.py
import asyncio
import time
from statistics import mean, median

async def test_database_query(query_func, num_queries=100):
    """测试数据库查询性能"""
    query_times = []
    
    for i in range(num_queries):
        start_time = time.time()
        try:
            await query_func()
            query_time = time.time() - start_time
            query_times.append(query_time)
        except Exception as e:
            print(f"查询失败: {e}")
    
    if query_times:
        avg_time = mean(query_times)
        median_time = median(query_times)
        min_time = min(query_times)
        max_time = max(query_times)
        
        print(f"\n数据库查询性能测试:")
        print(f"  查询次数: {num_queries}")
        print(f"  成功查询: {len(query_times)}")
        print(f"  平均时间: {avg_time * 1000:.2f} ms")
        print(f"  中位数时间: {median_time * 1000:.2f} ms")
        print(f"  最小时间: {min_time * 1000:.2f} ms")
        print(f"  最大时间: {max_time * 1000:.2f} ms")
        
        # 验证性能
        assert avg_time < 0.1, f"平均查询时间应该 < 100ms，实际: {avg_time * 1000:.2f}ms"
```

---

## 负载测试

### 1. 渐进式负载测试

**测试场景**: 逐步增加负载，观察系统性能变化

**测试脚本 (k6)**

```javascript
// tests/performance/load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // 2 分钟内增加到 50 用户
    { duration: '5m', target: 50 },   // 保持 50 用户 5 分钟
    { duration: '2m', target: 100 },  // 2 分钟内增加到 100 用户
    { duration: '5m', target: 100 },  // 保持 100 用户 5 分钟
    { duration: '2m', target: 200 },  // 2 分钟内增加到 200 用户
    { duration: '5m', target: 200 },  // 保持 200 用户 5 分钟
    { duration: '2m', target: 0 },    // 2 分钟内减少到 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // 测试查询可用主机列表
  const url = 'http://localhost:8003/api/v1/host/hosts/available';
  const payload = JSON.stringify({
    tc_id: 'test_case_001',
    cycle_name: 'test_cycle_001',
    user_name: 'test_user',
    page_size: 20,
  });

  const res = http.post(url, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
```

---

### 2. 峰值负载测试

**测试场景**: 短时间内达到峰值负载，测试系统极限

**测试脚本 (k6)**

```javascript
// tests/performance/spike_test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 100 },  // 1 分钟内增加到 100 用户
    { duration: '30s', target: 500 }, // 30 秒内突然增加到 500 用户（峰值）
    { duration: '1m', target: 500 },  // 保持峰值 1 分钟
    { duration: '1m', target: 100 },  // 1 分钟内减少到 100 用户
    { duration: '1m', target: 0 },    // 1 分钟内减少到 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 峰值时放宽要求
    http_req_failed: ['rate<0.05'],    // 峰值时允许更多错误
  },
};

export default function () {
  const url = 'http://localhost:8003/api/v1/host/hosts/available';
  const payload = JSON.stringify({
    tc_id: 'test_case_001',
    cycle_name: 'test_cycle_001',
    user_name: 'test_user',
    page_size: 20,
  });

  const res = http.post(url, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
```

---

## 压力测试

### 1. 压力测试场景

**测试目标**: 找到系统崩溃点

**测试脚本 (k6)**

```javascript
// tests/performance/stress_test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },  // 正常负载
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },  // 逐步增加
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },  // 继续增加
    { duration: '5m', target: 300 },
    { duration: '2m', target: 400 },  // 接近极限
    { duration: '5m', target: 400 },
    { duration: '10m', target: 400 }, // 保持极限负载
    { duration: '2m', target: 0 },    // 恢复
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 压力测试时放宽要求
    http_req_failed: ['rate<0.1'],     // 允许更多错误
  },
};

export default function () {
  const url = 'http://localhost:8003/api/v1/host/hosts/available';
  const payload = JSON.stringify({
    tc_id: 'test_case_001',
    cycle_name: 'test_cycle_001',
    user_name: 'test_user',
    page_size: 20,
  });

  const res = http.post(url, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
```

---

## 性能基准

### 1. HTTP 接口性能基准

| 接口 | 平均响应时间 | P95 响应时间 | P99 响应时间 | QPS |
|------|------------|------------|------------|-----|
| POST /hosts/available | < 200ms | < 500ms | < 1000ms | > 100 |
| POST /vnc/connect | < 150ms | < 300ms | < 500ms | > 200 |
| POST /vnc/report | < 100ms | < 200ms | < 300ms | > 300 |
| POST /hosts/release | < 100ms | < 200ms | < 300ms | > 300 |
| GET /admin/host/list | < 300ms | < 600ms | < 1000ms | > 50 |
| POST /file/upload | < 1000ms | < 2000ms | < 3000ms | > 10 |
| GET /file/{filename} | < 500ms | < 1000ms | < 2000ms | > 20 |

### 2. WebSocket 性能基准

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 连接建立时间 | < 1s | 平均连接时间 |
| 消息延迟 | < 50ms | 平均消息延迟 |
| 消息吞吐量 | > 100 msg/sec | 单连接吞吐量 |
| 并发连接数 | > 1000 | 同时在线连接数 |
| 内存使用 | < 200MB/1000连接 | 每 1000 连接的内存使用 |

### 3. 数据库性能基准

| 操作 | 平均响应时间 | P95 响应时间 | 说明 |
|------|------------|------------|------|
| 简单查询 | < 10ms | < 50ms | 单表查询 |
| 复杂查询 | < 100ms | < 500ms | 多表关联查询 |
| 插入操作 | < 50ms | < 200ms | 单条插入 |
| 更新操作 | < 50ms | < 200ms | 单条更新 |
| 删除操作 | < 50ms | < 200ms | 单条删除 |

---

## 监控指标说明

### 1. Prometheus 指标

**HTTP 请求指标**

```promql
# 请求总数
http_requests_total{service="host-service"}

# 请求响应时间（P95）
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="host-service"}[5m]))

# 请求速率
rate(http_requests_total{service="host-service"}[5m])

# 错误率
rate(http_requests_total{service="host-service",status=~"5.."}[5m]) / rate(http_requests_total{service="host-service"}[5m])
```

**数据库指标**

```promql
# 数据库查询总数
db_queries_total{service="host-service"}

# 数据库查询响应时间（P95）
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket{service="host-service"}[5m]))

# 数据库连接数
db_connections_active{service="host-service"}
```

**WebSocket 指标**

```promql
# 活跃连接数
active_connections{service="host-service"}

# 连接建立总数
websocket_connections_total{service="host-service"}
```

### 2. Grafana 仪表板

**关键图表**

1. **请求响应时间趋势图**
   - 平均响应时间
   - P95 响应时间
   - P99 响应时间

2. **请求速率图**
   - QPS 趋势
   - 错误率趋势

3. **资源使用图**
   - CPU 使用率
   - 内存使用率
   - 数据库连接数

4. **WebSocket 连接图**
   - 活跃连接数
   - 连接建立速率
   - 消息吞吐量

---

## 性能优化建议

### 1. HTTP 接口优化

**优化建议**

1. **数据库查询优化**
   - 使用索引优化查询
   - 避免 N+1 查询问题
   - 使用连接池管理数据库连接

2. **缓存策略**
   - 对频繁查询的数据使用 Redis 缓存
   - 设置合理的缓存过期时间
   - 使用缓存预热策略

3. **异步处理**
   - 使用异步 I/O 操作
   - 长时间任务使用后台任务队列
   - 批量处理请求

4. **响应压缩**
   - 启用 Gzip 压缩
   - 减少响应数据大小

### 2. WebSocket 优化

**优化建议**

1. **连接管理**
   - 实现连接池管理
   - 及时清理断开的连接
   - 限制单个 IP 的连接数

2. **消息处理**
   - 使用消息队列处理大量消息
   - 批量发送消息
   - 实现消息优先级

3. **内存管理**
   - 及时释放不用的连接资源
   - 限制消息缓冲区大小
   - 定期清理过期数据

### 3. 数据库优化

**优化建议**

1. **索引优化**
   - 为常用查询字段添加索引
   - 定期分析查询性能
   - 删除不必要的索引

2. **查询优化**
   - 避免全表扫描
   - 使用分页查询
   - 优化 JOIN 查询

3. **连接池优化**
   - 合理设置连接池大小
   - 监控连接池使用情况
   - 及时释放空闲连接

### 4. 系统资源优化

**优化建议**

1. **CPU 优化**
   - 使用多进程/多线程处理
   - 优化算法复杂度
   - 减少不必要的计算

2. **内存优化**
   - 及时释放不用的对象
   - 使用对象池
   - 监控内存泄漏

3. **网络优化**
   - 使用 CDN 加速静态资源
   - 优化网络传输协议
   - 减少网络往返次数

---

## 性能测试报告模板

### 测试报告结构

```markdown
# Host Service 性能测试报告

## 测试概述
- 测试时间: 2025-01-15
- 测试环境: 生产环境
- 测试工具: k6, Locust, Python

## 测试结果摘要
- 平均响应时间: 150ms
- P95 响应时间: 450ms
- P99 响应时间: 900ms
- 峰值 QPS: 1200
- 错误率: 0.05%

## 详细测试结果
[各接口的详细测试数据]

## 性能瓶颈分析
[发现的性能问题和瓶颈]

## 优化建议
[具体的优化建议和方案]

## 结论
[测试结论和建议]
```

---

## 持续性能监控

### 1. 性能监控脚本

```bash
#!/bin/bash
# scripts/monitor_performance.sh

# 监控 Prometheus 指标
curl -s http://localhost:9090/api/v1/query?query=http_request_duration_seconds | jq

# 监控服务资源使用
docker stats host-service --no-stream

# 监控数据库连接
mysql -u root -p -e "SHOW PROCESSLIST;"
```

### 2. 性能告警规则

```yaml
# prometheus/alerts/performance_alerts.yml
groups:
  - name: performance_alerts
    rules:
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过高"
          description: "P95 响应时间超过 1 秒"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "错误率过高"
          description: "错误率超过 1%"
```

---

**最后更新**: 2025-01-15  
**文档版本**: 1.0.0  
**维护者**: Host Service 开发团队

