# 性能与压力测试脚本

该目录存放 Host Service 的性能/压力测试脚本示例，用于配合 `docs/29-host-service-performance-testing.md` 和 `docs/30-host-service-stress-testing-*.md`。

## 目录结构

```
tests/performance/
├── README.md
├── http/
│   ├── k6_query_available_hosts.js
│   ├── k6_vnc_connect.js
│   ├── k6_admin_host_list.js
│   ├── locust_agent_report.py
│   └── python_file_upload_test.py
├── websocket/
│   ├── ws_connection_test.py
│   ├── ws_throughput_test.py
│   └── ws_concurrent_test.py
└── mixed/
    └── k6_mixed_stress.js
```

## 使用说明

- k6 脚本默认访问 `http://localhost:8003`，可通过 `K6_HOST_URL` 环境变量覆盖。
- Python/Locust 脚本默认访问 `http://localhost:8003`，可通过命令行参数或环境变量调整。
- 所有脚本仅为参考示例，请根据实际压测环境修改并接入监控采集。
