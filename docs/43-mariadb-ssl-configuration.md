# MariaDB SSL 配置完整指南

## 📋 概述

本文档提供 MariaDB 10.11 启用 SSL/TLS 加密连接的完整配置指南，包括服务器端配置、客户端连接配置和 Docker 环境下的 SSL 设置。

---

## 🔐 SSL 配置方案

### 方案 1：使用自签名证书（开发/测试环境）

适用于开发、测试环境，快速启用 SSL 加密。

### 方案 2：使用 CA 签名的证书（生产环境）

适用于生产环境，需要从 CA（证书颁发机构）获取证书。

---

## 📝 方案 1：自签名证书配置

### 1. 生成自签名证书

#### 1.1 创建证书目录

```bash
# 在项目根目录创建 SSL 证书目录
mkdir -p infrastructure/mysql/ssl
cd infrastructure/mysql/ssl
```

#### 1.2 生成 CA 私钥和证书

```bash
# 生成 CA 私钥（2048位）
openssl genrsa -out ca-key.pem 2048

# 生成 CA 证书（有效期10年）
openssl req -new -x509 -nodes -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=Intel EC/OU=IT Department/CN=MariaDB-CA"
```

#### 1.3 生成服务器私钥和证书请求

```bash
# 生成服务器私钥
openssl genrsa -out server-key.pem 2048

# 生成证书签名请求（CSR）
openssl req -new -key server-key.pem -out server-req.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=Intel EC/OU=IT Department/CN=mariadb"
```

#### 1.4 使用 CA 签名服务器证书

```bash
# 使用 CA 证书签名服务器证书（有效期1年）
openssl x509 -req -in server-req.pem -days 365 -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem
```

#### 1.5 生成客户端证书（可选）

```bash
# 生成客户端私钥
openssl genrsa -out client-key.pem 2048

# 生成客户端证书请求
openssl req -new -key client-key.pem -out client-req.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=Intel EC/OU=IT Department/CN=client"

# 使用 CA 签名客户端证书
openssl x509 -req -in client-req.pem -days 365 -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out client-cert.pem
```

#### 1.6 设置文件权限

```bash
# 设置私钥文件权限（仅所有者可读）
chmod 600 ca-key.pem server-key.pem client-key.pem

# 设置证书文件权限（所有人可读）
chmod 644 ca-cert.pem server-cert.pem client-cert.pem
```

---

### 2. 配置 MariaDB 服务器（Docker 环境）

#### 2.1 创建 MariaDB 配置文件

创建 `infrastructure/mysql/conf/my.cnf`：

```ini
[mysqld]
# SSL 配置
ssl-ca=/etc/mysql/ssl/ca-cert.pem
ssl-cert=/etc/mysql/ssl/server-cert.pem
ssl-key=/etc/mysql/ssl/server-key.pem

# 强制 SSL 连接（可选，生产环境建议启用）
# require-secure-transport=ON

# 其他配置
max_connections=500
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
```

#### 2.2 更新 docker-compose.yml

```yaml
services:
  mariadb:
    image: mariadb:10.11
    container_name: intel-mariadb
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD:-mariadb123}
      MARIADB_DATABASE: ${MARIADB_DATABASE:-intel_cw}
      MARIADB_USER: ${MARIADB_USER:-intel_user}
      MARIADB_PASSWORD: ${MARIADB_PASSWORD:-intel_***REMOVED***}
      MARIADB_CHARSET: utf8mb4
      MARIADB_COLLATION: utf8mb4_unicode_ci
      MYSQL_MAX_CONNECTIONS: ${MYSQL_MAX_CONNECTIONS:-500}
    ports:
      - "${MARIADB_PORT:-3306}:3306"
    volumes:
      - mariadb_data:/var/lib/mysql
      - ./infrastructure/mysql/init:/docker-entrypoint-initdb.d
      # SSL 证书挂载
      - ./infrastructure/mysql/ssl:/etc/mysql/ssl:ro
      # MariaDB 配置文件挂载
      - ./infrastructure/mysql/conf/my.cnf:/etc/mysql/conf.d/ssl.cnf:ro
    networks:
      - intel-network
    healthcheck:
      test:
        [
          "CMD",
          "healthcheck.sh",
          "--connect",
          "--innodb_initialized",
        ]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
```

#### 2.3 重启 MariaDB 容器

```bash
# 停止并删除旧容器
docker-compose stop mariadb
docker-compose rm -f mariadb

# 启动新容器
docker-compose up -d mariadb

# 查看日志确认 SSL 已启用
docker-compose logs mariadb | grep -i ssl
```

---

### 3. 验证 SSL 配置

#### 3.1 检查 SSL 状态

```bash
# 进入 MariaDB 容器
docker-compose exec mariadb bash

# 连接数据库
mysql -u root -p

# 查看 SSL 状态
SHOW VARIABLES LIKE '%ssl%';

# 应该看到：
# have_openssl = YES
# have_ssl = YES
# ssl_ca = /etc/mysql/ssl/ca-cert.pem
# ssl_cert = /etc/mysql/ssl/server-cert.pem
# ssl_key = /etc/mysql/ssl/server-key.pem
```

#### 3.2 测试 SSL 连接

```bash
# 使用 SSL 连接（客户端验证）
mysql -u intel_user -p --ssl-ca=/etc/mysql/ssl/ca-cert.pem \
  --ssl-cert=/etc/mysql/ssl/client-cert.pem \
  --ssl-key=/etc/mysql/ssl/client-key.pem

# 使用 SSL 连接（仅服务器验证）
mysql -u intel_user -p --ssl-ca=/etc/mysql/ssl/ca-cert.pem

# 检查当前连接是否使用 SSL
\s
# 或
STATUS;
# 查看 "SSL:" 行，应该显示 "Cipher in use is ..."
```

---

### 4. 配置 Python 客户端（SQLAlchemy）

#### 4.1 安装 SSL 依赖

```bash
# 安装 PyMySQL（aiomysql 的同步版本，用于 SSL 测试）
pip install PyMySQL

# aiomysql 已包含在 requirements.txt 中
```

#### 4.2 更新数据库连接管理器（正确方法）

**重要**：aiomysql **不支持**通过 URL 查询参数传递 `ssl_verify_cert`。必须使用 `connect_args` 传递 SSL 配置。

修改 `shared/common/database.py` 中的 `connect()` 方法：

```python
async def connect(
    self,
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    echo: bool = False,
    enable_sql_monitoring: bool = True,
    slow_query_threshold: float = 2.0,
    service_name: str = "unknown",
    pool_timeout: float = 30.0,
    connect_timeout: int = 10,
    read_timeout: int = 30,
    write_timeout: int = 30,
    # SSL 参数
    ssl_ca: Optional[str] = None,
    ssl_cert: Optional[str] = None,
    ssl_key: Optional[str] = None,
    ssl_verify_cert: bool = True,
    ssl_verify_identity: bool = False,
) -> None:
    """连接到MariaDB数据库
    
    Args:
        database_url: 数据库连接URL，格式：mysql+aiomysql://user:***REMOVED***@host:port/db
        # ... 其他参数 ...
        ssl_ca: CA 证书文件路径
        ssl_cert: 客户端证书文件路径
        ssl_key: 客户端私钥文件路径
        ssl_verify_cert: 是否验证服务器证书（默认 True）
        ssl_verify_identity: 是否验证服务器身份（默认 False）
    """
    try:
        # 处理超时参数
        if "?" in database_url:
            timeout_params = f"&connect_timeout={connect_timeout}"
            database_url_with_timeout = database_url + timeout_params
        else:
            timeout_params = f"?connect_timeout={connect_timeout}"
            database_url_with_timeout = database_url + timeout_params

        # ✅ 构建 SSL 配置（通过 connect_args 传递）
        # 注意：aiomysql 需要 SSLContext 对象，而不是字典
        connect_args = {}
        
        # 如果启用了 SSL，构建 SSL 上下文
        if ssl_ca or ssl_cert or ssl_key or not ssl_verify_cert:
            import ssl
            
            # 创建 SSL 上下文
            if not ssl_verify_cert:
                # ✅ 不验证证书：创建不验证的 SSL 上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                # 验证证书：创建默认 SSL 上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = ssl_verify_identity
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # 加载证书文件
            if ssl_ca:
                ssl_context.load_verify_locations(ssl_ca)
            if ssl_cert and ssl_key:
                ssl_context.load_cert_chain(ssl_cert, ssl_key)
            
            # ✅ 将 SSL 上下文对象（不是字典）添加到 connect_args
            connect_args['ssl'] = ssl_context
        
        # 保存连接池配置用于监控
        self._pool_size = pool_size
        self._max_overflow = max_overflow

        # 创建异步引擎（通过 connect_args 传递 SSL 配置）
        self.engine = create_async_engine(
            database_url_with_timeout,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            echo=echo,
            pool_recycle=3600,
            pool_timeout=pool_timeout,
            connect_args=connect_args,  # ✅ 通过 connect_args 传递 SSL 配置
        )
        
        # ... 其余代码保持不变 ...
```

#### 4.3 更新服务配置工厂

修改 `shared/app/service_factory.py` 中的 `from_env()` 方法，传递 SSL 参数：

```python
@staticmethod
def from_env(service_name: str, service_port_key: str = "SERVICE_PORT") -> "ServiceConfig":
    # ... 现有代码 ...
    
    # SSL 配置
    ssl_enabled = os.getenv("MARIADB_SSL_ENABLED", "false").lower() in ("true", "1", "yes")
    ssl_ca_path = os.getenv("MARIADB_SSL_CA", "")
    ssl_cert_path = os.getenv("MARIADB_SSL_CERT", "")
    ssl_key_path = os.getenv("MARIADB_SSL_KEY", "")
    ssl_verify_cert = os.getenv("MARIADB_SSL_VERIFY_CERT", "true").lower() in ("true", "1", "yes")
    ssl_verify_identity = os.getenv("MARIADB_SSL_VERIFY_IDENTITY", "false").lower() in ("true", "1", "yes")
    
    # 构建数据库 URL（不包含 SSL 参数）
    encoded_***REMOVED***word = quote_plus(mariadb_***REMOVED***word)
    mariadb_url = (
        f"mysql+aiomysql://{mariadb_user}:{encoded_***REMOVED***word}@{mariadb_host}:{mariadb_port}/{mariadb_database}"
    )
    
    # 注意：SSL 配置通过 connect() 方法的参数传递，而不是 URL 参数
    
    # ... 其余代码 ...
    
    # 在调用 init_databases 时传递 SSL 参数
    # 需要修改 init_databases 函数签名以支持 SSL 参数
```

#### 4.4 环境变量配置

在 `.env` 文件中添加 SSL 配置：

**完整验证（生产环境推荐）**：
```bash
# MariaDB SSL 配置
MARIADB_SSL_ENABLED=true
MARIADB_SSL_CA=./infrastructure/mysql/ssl/ca-cert.pem
MARIADB_SSL_CERT=./infrastructure/mysql/ssl/client-cert.pem
MARIADB_SSL_KEY=./infrastructure/mysql/ssl/client-key.pem

# SSL 验证选项
MARIADB_SSL_VERIFY_CERT=true
MARIADB_SSL_VERIFY_IDENTITY=false
```

**不验证证书（开发/测试环境）**：
```bash
# MariaDB SSL 配置（不验证证书）
MARIADB_SSL_ENABLED=true
# 不提供 CA 证书，或设置 ssl_verify_cert=false
MARIADB_SSL_VERIFY_CERT=false
MARIADB_SSL_VERIFY_IDENTITY=false

# 可选：如果服务器要求客户端证书
MARIADB_SSL_CERT=./infrastructure/mysql/ssl/client-cert.pem
MARIADB_SSL_KEY=./infrastructure/mysql/ssl/client-key.pem
```

**SSL 未启用（默认）**：
```bash
# 不设置或设置为 false
MARIADB_SSL_ENABLED=false
```

---

### 5. 不验证证书的配置（开发/测试环境）

#### 5.1 快速配置（推荐）

对于开发或测试环境，可以跳过证书验证，仅启用 SSL 加密传输：

**环境变量配置**：
```bash
# .env 文件
MARIADB_SSL_ENABLED=true
MARIADB_SSL_VERIFY_CERT=false
```

**数据库连接配置**（通过 `connect_args` 传递 SSLContext）：
```python
from sqlalchemy.ext.asyncio import create_async_engine
import ssl

# 创建不验证证书的 SSL 上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    "mysql+aiomysql://user:***REMOVED***word@host:port/database",
    connect_args={
        "ssl": ssl_context  # ✅ 传递 SSLContext 对象
    }
)
```

#### 5.2 aiomysql 不验证证书的正确方法

**⚠️ 重要**：aiomysql **不支持**通过 URL 查询参数传递 `ssl_verify_cert`。必须使用 `connect_args` 传递 SSL 配置。

**正确方法：通过 connect_args 传递 SSLContext 对象（唯一正确的方法）**
```python
from sqlalchemy.ext.asyncio import create_async_engine
import ssl

# ✅ 不验证证书的 SSL 配置
database_url = "mysql+aiomysql://user:***REMOVED***word@host:port/database"

# 创建不验证证书的 SSL 上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    database_url,
    connect_args={
        "ssl": ssl_context  # ✅ 传递 SSLContext 对象，不是字典
    }
)
```

**如果使用证书文件但不验证**：
```python
import ssl

# 创建 SSL 上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 可选：加载证书文件
ssl_context.load_verify_locations("/path/to/ca-cert.pem")
ssl_context.load_cert_chain(
    "/path/to/client-cert.pem",
    "/path/to/client-key.pem"
)

engine = create_async_engine(
    database_url,
    connect_args={
        "ssl": ssl_context  # ✅ 传递 SSLContext 对象
    }
)
```

**❌ 错误方法（会导致 wrap_bio 错误）**：
```python
# ❌ 错误：传递字典而不是 SSLContext 对象
engine = create_async_engine(
    database_url,
    connect_args={
        "ssl": {
            "check_hostname": False,  # 这会导致 'dict' object has no attribute 'wrap_bio'
        }
    }
)
```

**错误方法（会导致报错）**：
```python
# ❌ 错误：aiomysql 不支持 URL 参数 ssl_verify_cert
database_url = "mysql+aiomysql://user:***REMOVED***word@host:port/database?ssl_verify_cert=false"
# 会报错：connect() got an unexpected keyword argument 'ssl_verify_cert'
```

#### 5.3 命令行测试（不验证证书）

```bash
# MySQL 客户端：使用 --ssl-mode=REQUIRED 但不验证证书
mysql -u intel_user -p \
  --ssl-mode=REQUIRED \
  --ssl-verify-server-cert=0

# 或使用 --ssl 但不提供 CA
mysql -u intel_user -p --ssl
```

---

### 6. 测试 SSL 连接

#### 6.1 Python 测试脚本

创建 `scripts/test_ssl_connection.py`：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 MariaDB SSL 连接"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from shared.common.database import mariadb_manager


async def test_ssl_connection():
    """测试 SSL 连接"""
    # 从环境变量读取配置
    mariadb_host = os.getenv("MARIADB_HOST", "localhost")
    mariadb_port = os.getenv("MARIADB_PORT", "3306")
    mariadb_user = os.getenv("MARIADB_USER", "intel_user")
    mariadb_***REMOVED***word = os.getenv("MARIADB_PASSWORD", "intel_***REMOVED***")
    mariadb_database = os.getenv("MARIADB_DATABASE", "intel_cw")
    
    # SSL 配置
    ssl_enabled = os.getenv("MARIADB_SSL_ENABLED", "false").lower() in ("true", "1", "yes")
    ssl_ca = os.getenv("MARIADB_SSL_CA", "")
    ssl_cert = os.getenv("MARIADB_SSL_CERT", "")
    ssl_key = os.getenv("MARIADB_SSL_KEY", "")
    ssl_verify_cert = os.getenv("MARIADB_SSL_VERIFY_CERT", "true").lower() in ("true", "1", "yes")
    
    # 构建数据库 URL
    from urllib.parse import quote_plus
    
    database_url = (
        f"mysql+aiomysql://{mariadb_user}:{quote_plus(mariadb_***REMOVED***word)}"
        f"@{mariadb_host}:{mariadb_port}/{mariadb_database}"
    )
    
    # 注意：SSL 配置通过 connect_args 传递，不在 URL 中
    # 这里只构建基础 URL，SSL 配置在 connect() 方法中处理
    
    print(f"连接数据库: {mariadb_host}:{mariadb_port}/{mariadb_database}")
    print(f"SSL 启用: {ssl_enabled}")
    print(f"SSL 验证证书: {ssl_verify_cert}")
    if ssl_verify_cert:
        print(f"SSL CA: {ssl_ca}")
    print(f"SSL Cert: {ssl_cert}")
    print(f"SSL Key: {ssl_key}")
    print()
    
    try:
        # 连接数据库
        await mariadb_manager.connect(
            database_url=database_url,
            pool_size=5,
            max_overflow=10,
        )
        
        print("✓ SSL 连接成功！")
        
        # 测试查询
        from sqlalchemy import text
        session_factory = mariadb_manager.get_session()
        async with session_factory() as session:
            result = await session.execute(text("SELECT VERSION(), @@ssl_cipher"))
            row = result.fetchone()
            print(f"✓ MariaDB 版本: {row[0]}")
            print(f"✓ SSL 加密算法: {row[1] if row[1] else '未使用 SSL'}")
        
        # 断开连接
        await mariadb_manager.disconnect()
        print("✓ 连接已关闭")
        
    except Exception as e:
        print(f"✗ SSL 连接失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_ssl_connection())
```

#### 6.2 运行测试

**验证证书模式**：
```bash
# 设置环境变量
export MARIADB_SSL_ENABLED=true
export MARIADB_SSL_VERIFY_CERT=true
export MARIADB_SSL_CA=./infrastructure/mysql/ssl/ca-cert.pem
export MARIADB_SSL_CERT=./infrastructure/mysql/ssl/client-cert.pem
export MARIADB_SSL_KEY=./infrastructure/mysql/ssl/client-key.pem

# 运行测试
python scripts/test_ssl_connection.py
```

**不验证证书模式（开发/测试）**：
```bash
# 设置环境变量（不验证证书）
export MARIADB_SSL_ENABLED=true
export MARIADB_SSL_VERIFY_CERT=false

# 运行测试
python scripts/test_ssl_connection.py
```

---

## 📌 快速参考：不验证证书的配置

### 最简单的配置（开发环境）

**1. 环境变量（.env 文件）**：
```bash
MARIADB_SSL_ENABLED=true
MARIADB_SSL_VERIFY_CERT=false
```

**2. 数据库连接配置**（修改 `shared/common/database.py`）：
```python
import ssl

# 在 connect() 方法中添加 SSL 参数支持
# ✅ 通过 connect_args 传递 SSLContext 对象（不是字典）
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    database_url,
    connect_args={
        "ssl": ssl_context  # ✅ 传递 SSLContext 对象
    }
)
```

**3. 验证连接**：
```bash
# 检查 SSL 是否启用
docker-compose exec mariadb mysql -u root -p -e "SHOW VARIABLES LIKE 'have_ssl';"
# 应该显示: have_ssl = YES

# Python 测试
export MARIADB_SSL_ENABLED=true
export MARIADB_SSL_VERIFY_CERT=false
python scripts/test_ssl_connection.py
```

**⚠️ 安全提示**：
- 不验证证书仅适用于开发/测试环境
- 生产环境必须启用证书验证
- 不验证证书仍然提供加密传输，但不验证服务器身份

---

## 🏭 方案 2：生产环境 SSL 配置

### 1. 获取 CA 签名的证书

从 CA（如 Let's Encrypt、DigiCert）获取证书：

```bash
# Let's Encrypt 示例（使用 certbot）
certbot certonly --standalone -d mariadb.example.com

# 证书文件位置：
# /etc/letsencrypt/live/mariadb.example.com/fullchain.pem  # 服务器证书
# /etc/letsencrypt/live/mariadb.example.com/privkey.pem    # 服务器私钥
# /etc/letsencrypt/live/mariadb.example.com/chain.pem      # CA 证书链
```

### 2. 配置强制 SSL（生产环境）

在 `infrastructure/mysql/conf/my.cnf` 中启用强制 SSL：

```ini
[mysqld]
# SSL 配置
ssl-ca=/etc/mysql/ssl/ca-cert.pem
ssl-cert=/etc/mysql/ssl/server-cert.pem
ssl-key=/etc/mysql/ssl/server-key.pem

# 强制 SSL 连接（生产环境必须启用）
require-secure-transport=ON
```

### 3. 用户权限配置

```sql
-- 创建仅允许 SSL 连接的用户
CREATE USER 'ssl_user'@'%' IDENTIFIED BY 'secure_***REMOVED***word' REQUIRE SSL;

-- 或要求特定证书
CREATE USER 'ssl_user'@'%' IDENTIFIED BY 'secure_***REMOVED***word' 
  REQUIRE X509;

-- 或要求特定证书主题
CREATE USER 'ssl_user'@'%' IDENTIFIED BY 'secure_***REMOVED***word' 
  REQUIRE SUBJECT '/C=CN/ST=Beijing/L=Beijing/O=Intel EC/CN=client';

-- 授予权限
GRANT ALL PRIVILEGES ON intel_cw.* TO 'ssl_user'@'%';
FLUSH PRIVILEGES;
```

---

## 🔍 故障排除

### 问题 1：SSL 连接失败

**错误信息**：
```
SSL connection error: SSL_CTX_set_default_verify_paths failed
```

**解决方案**：
1. 检查证书文件路径是否正确
2. 确认证书文件权限（私钥应为 600）
3. 验证证书文件格式是否正确

### 问题 2：证书验证失败

**错误信息**：
```
SSL: error:0B080074:x509 certificate routines:X509_check_private_key:key values mismatch
```

**解决方案**：
1. 确认私钥和证书匹配
2. 重新生成匹配的证书对

### 问题 3：Docker 容器中证书路径问题

**解决方案**：
1. 确认卷挂载路径正确
2. 使用绝对路径或相对于项目根目录的路径
3. 检查文件权限

### 问题 4：Python 客户端 SSL 连接失败

**错误信息**：
```
SSL connection error: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**解决方案**：
1. 确认客户端证书路径正确
2. 检查环境变量配置
3. **开发环境**：设置 `MARIADB_SSL_VERIFY_CERT=false` 跳过证书验证
4. **生产环境**：确保 CA 证书正确且证书链完整

### 问题 5：不验证证书时仍然报错

**错误信息**：
```
SSL connection error: SSL is required but the server doesn't support it
```

**解决方案**：
1. 确认服务器端 SSL 已正确配置
2. 检查 `SHOW VARIABLES LIKE '%ssl%'` 确认 `have_ssl = YES`
3. **确认使用 `connect_args` 传递 SSL 配置，而不是 URL 参数**
4. 如果使用环境变量，确认 `MARIADB_SSL_VERIFY_CERT=false` 已设置

### 问题 6：ssl_verify_cert 参数错误

**错误信息**：
```
connect() got an unexpected keyword argument 'ssl_verify_cert'
```

**原因**：aiomysql 不支持通过 URL 查询参数传递 `ssl_verify_cert`。

**解决方案**：
1. **不要**在 URL 中使用 `?ssl_verify_cert=false`
2. **必须**使用 `connect_args` 传递 SSLContext 对象（不是字典）

### 问题 7：dict object has no attribute wrap_bio

**错误信息**：
```
AttributeError: 'dict' object has no attribute 'wrap_bio'
```

**原因**：aiomysql 期望 `ssl` 参数是 `ssl.SSLContext` 对象，而不是字典。

**解决方案**：
1. **不要**传递字典给 `ssl` 参数
2. **必须**创建 `ssl.SSLContext` 对象：
   ```python
   import ssl
   
   # ✅ 正确：创建 SSLContext 对象
   ssl_context = ssl.create_default_context()
   ssl_context.check_hostname = False
   ssl_context.verify_mode = ssl.CERT_NONE
   
   engine = create_async_engine(
       database_url,
       connect_args={
           "ssl": ssl_context  # ✅ 传递 SSLContext 对象
       }
   )
   ```
3. 修改 `shared/common/database.py` 中的 `connect()` 方法，使用 `ssl.create_default_context()` 创建 SSL 上下文

---

## 🔧 常见问题与修复

### 问题：connect_args 正确用法

#### 🐛 问题描述

使用 `mysql+aiomysql://user:***REMOVED***word@host:port/database?ssl_verify_cert=false` 时报错：

```
connect() got an unexpected keyword argument 'ssl_verify_cert'
```

#### ✅ 解决方案

aiomysql **不支持**通过 URL 查询参数传递 `ssl_verify_cert`。必须使用 `connect_args` 传递 SSL 配置。

#### 📝 代码修改

##### 修改 `shared/common/database.py`

在 `MariaDBManager.connect()` 方法中添加 SSL 支持：

```python
async def connect(
    self,
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    echo: bool = False,
    enable_sql_monitoring: bool = True,
    slow_query_threshold: float = 2.0,
    service_name: str = "unknown",
    pool_timeout: float = 30.0,
    connect_timeout: int = 10,
    read_timeout: int = 30,
    write_timeout: int = 30,
    # ✅ 新增 SSL 参数
    ssl_ca: Optional[str] = None,
    ssl_cert: Optional[str] = None,
    ssl_key: Optional[str] = None,
    ssl_verify_cert: bool = True,
    ssl_verify_identity: bool = False,
) -> None:
    """连接到MariaDB数据库"""
    try:
        # 处理超时参数
        if "?" in database_url:
            timeout_params = f"&connect_timeout={connect_timeout}"
            database_url_with_timeout = database_url + timeout_params
        else:
            timeout_params = f"?connect_timeout={connect_timeout}"
            database_url_with_timeout = database_url + timeout_params

        # ✅ 构建 SSL 配置（通过 connect_args 传递）
        # 注意：aiomysql 的 SSL 配置需要使用 ssl.create_default_context() 或自定义 SSLContext
        connect_args = {}
        
        # 如果启用了 SSL，构建 SSL 上下文
        if ssl_ca or ssl_cert or ssl_key or not ssl_verify_cert:
            import ssl
            
            # 创建 SSL 上下文
            if not ssl_verify_cert:
                # 不验证证书：创建不验证的 SSL 上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                # 验证证书：创建默认 SSL 上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = ssl_verify_identity
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # 加载证书文件
            if ssl_ca:
                ssl_context.load_verify_locations(ssl_ca)
            if ssl_cert:
                ssl_context.load_cert_chain(ssl_cert, ssl_key)
            
            # 将 SSL 上下文添加到 connect_args
            connect_args['ssl'] = ssl_context
        
        # 保存连接池配置
        self._pool_size = pool_size
        self._max_overflow = max_overflow

        # ✅ 创建异步引擎（通过 connect_args 传递 SSL 配置）
        self.engine = create_async_engine(
            database_url_with_timeout,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            echo=echo,
            pool_recycle=3600,
            pool_timeout=pool_timeout,
            connect_args=connect_args,  # ✅ 关键：通过 connect_args 传递 SSL
        )
        
        # ... 其余代码保持不变 ...
```

##### 修改 `shared/app/service_factory.py`

在 `ServiceConfig.from_env()` 方法中读取 SSL 配置并传递给 `init_databases`：

```python
@staticmethod
def from_env(service_name: str, service_port_key: str = "SERVICE_PORT") -> "ServiceConfig":
    # ... 现有代码 ...
    
    # ✅ SSL 配置
    ssl_enabled = os.getenv("MARIADB_SSL_ENABLED", "false").lower() in ("true", "1", "yes")
    ssl_ca = os.getenv("MARIADB_SSL_CA", "") if ssl_enabled else None
    ssl_cert = os.getenv("MARIADB_SSL_CERT", "") if ssl_enabled else None
    ssl_key = os.getenv("MARIADB_SSL_KEY", "") if ssl_enabled else None
    ssl_verify_cert = os.getenv("MARIADB_SSL_VERIFY_CERT", "true").lower() in ("true", "1", "yes") if ssl_enabled else True
    ssl_verify_identity = os.getenv("MARIADB_SSL_VERIFY_IDENTITY", "false").lower() in ("true", "1", "yes") if ssl_enabled else False
    
    # 构建数据库 URL（不包含 SSL 参数）
    encoded_***REMOVED***word = quote_plus(mariadb_***REMOVED***word)
    mariadb_url = (
        f"mysql+aiomysql://{mariadb_user}:{encoded_***REMOVED***word}@{mariadb_host}:{mariadb_port}/{mariadb_database}"
    )
    
    # ... 其余代码 ...
    
    # 在调用 init_databases 时传递 SSL 参数
    # 需要修改 init_databases 函数签名
```

##### 修改 `shared/common/database.py` 中的 `init_databases` 函数

```python
async def init_databases(
    mariadb_url: str,
    redis_url: Optional[str] = None,
    pool_size: int = 200,
    max_overflow: int = 500,
    enable_sql_monitoring: bool = True,
    slow_query_threshold: float = 2.0,
    service_name: str = "unknown",
    pool_timeout: float = 30.0,
    connect_timeout: int = 10,
    read_timeout: int = 30,
    write_timeout: int = 30,
    # ✅ 新增 SSL 参数
    ssl_ca: Optional[str] = None,
    ssl_cert: Optional[str] = None,
    ssl_key: Optional[str] = None,
    ssl_verify_cert: bool = True,
    ssl_verify_identity: bool = False,
) -> None:
    """初始化数据库连接"""
    try:
        # 连接MariaDB
        await mariadb_manager.connect(
            database_url=mariadb_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            enable_sql_monitoring=enable_sql_monitoring,
            slow_query_threshold=slow_query_threshold,
            service_name=service_name,
            pool_timeout=pool_timeout,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
            # ✅ 传递 SSL 参数
            ssl_ca=ssl_ca,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            ssl_verify_cert=ssl_verify_cert,
            ssl_verify_identity=ssl_verify_identity,
        )
        # ... 其余代码 ...
```

#### 🎯 使用示例

##### 不验证证书（开发环境）

**环境变量**（`.env` 文件）：
```bash
MARIADB_SSL_ENABLED=true
MARIADB_SSL_VERIFY_CERT=false
```

**代码会自动处理**：
- 读取 `MARIADB_SSL_VERIFY_CERT=false`
- 在 `connect_args` 中设置 `ssl={'check_hostname': False}`
- 连接时跳过证书验证

##### 验证证书（生产环境）

**环境变量**（`.env` 文件）：
```bash
MARIADB_SSL_ENABLED=true
MARIADB_SSL_CA=./infrastructure/mysql/ssl/ca-cert.pem
MARIADB_SSL_VERIFY_CERT=true
```

**代码会自动处理**：
- 读取 CA 证书路径
- 在 `connect_args` 中设置 `ssl={'ca': '...', 'check_hostname': True}`
- 连接时验证证书

---

## 📚 相关文档

- [基础设施配置指南](./01-infrastructure-config.md) - MariaDB 基础配置
- [数据库连接池优化](./performance/mysql-2000-concurrency-windows-optimization.md) - 连接池配置
- [SQL 性能监控](./40-sql-performance-monitoring.md) - 数据库性能监控

---

## 📅 更新历史

- **2025-01-29**: 初始版本，整理 MariaDB SSL 配置完整指南
- **2025-01-29**: 合并故障修复文档，添加 connect_args 正确用法说明
- **核心内容**:
  - 自签名证书生成和配置
  - Docker 环境 SSL 配置
  - Python/SQLAlchemy 客户端 SSL 连接
  - 生产环境 SSL 配置
  - 故障排除指南
  - connect_args 正确用法修复

