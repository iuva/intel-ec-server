# Linux 压测脚本使用说明

## 📋 概述

本目录包含适用于 Linux 平台的压测脚本和工具。

## 🛠️ 工具安装

### k6 安装

```bash
# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# CentOS/RHEL
sudo yum install https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.rpm

# 验证安装
k6 version
```


## 📝 脚本说明

### k6_load_test_linux.js

k6 压测脚本，适用于 Linux 平台。

**特点**：
- 支持高并发（100-500 VUs）
- 阶段式压测，逐步增加负载
- 支持环境变量配置

**使用方法**：

```bash
# 设置环境变量
export K6_HOST_URL=http://localhost:8003
export K6_ENV=local

# 执行压测
k6 run k6_load_test_linux.js

# 导出结果
k6 run k6_load_test_linux.js --out json=results/k6_results.json --out csv=results/k6_results.csv
```

### run_load_test.sh

Linux 压测执行脚本，提供交互式压测执行。

**使用方法**：

```bash
# 赋予执行权限
chmod +x run_load_test.sh

# 执行脚本
./run_load_test.sh

# 或使用环境变量
export K6_HOST_URL=http://localhost:8003
export K6_ENV=local
./run_load_test.sh
```

## ⚙️ 参数配置

| 参数 | Linux 推荐值 | 说明 |
|------|-------------|------|
| **k6 VUs** | 100-500 | Linux 支持高并发 |
| **k6 并发连接** | 200-1000 | 充分利用系统资源 |
| **请求超时** | 30s | 标准超时时间 |

## 🔧 系统优化

```bash
# 1. 增加文件描述符限制
ulimit -n 65535

# 永久设置（编辑 /etc/security/limits.conf）
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# 2. 优化 TCP 参数
sudo sysctl -w net.core.somaxconn=65535
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=65535
sudo sysctl -w net.ipv4.ip_local_port_range="10000 65535"

# 永久设置（编辑 /etc/sysctl.conf）
cat <<EOF | sudo tee -a /etc/sysctl.conf
net.core.somaxconn=65535
net.ipv4.tcp_max_syn_backlog=65535
net.ipv4.ip_local_port_range=10000 65535
EOF

sudo sysctl -p

# 3. 优化网络参数
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
sudo sysctl -w net.ipv4.tcp_fin_timeout=30
sudo sysctl -w net.ipv4.tcp_keepalive_time=600
```

## 📊 结果文件

压测结果会保存在 `results/` 目录下：

- `linux_k6_results.json` - k6 JSON 格式结果
- `linux_k6_results.csv` - k6 CSV 格式结果

## 🚀 分布式压测

### k6 云压测（k6 Cloud）

```bash
# 登录 k6 Cloud
k6 login cloud

# 运行云压测
k6 cloud k6_load_test_linux.js

# 或使用环境变量
export K6_CLOUD_TOKEN=your-token
k6 cloud k6_load_test_linux.js
```

## 🆘 常见问题

### Q1: k6 压测时连接数不够怎么办？

**A**: 增加系统文件描述符限制：

```bash
ulimit -n 65535
```

### Q2: 如何查看系统资源使用情况？

**A**: 

```bash
# CPU 和内存
top
htop

# 网络连接
netstat -an | grep ESTABLISHED | wc -l
ss -s

# 磁盘IO
iostat -x 1
```

---

**最后更新**: 2025-01-29

