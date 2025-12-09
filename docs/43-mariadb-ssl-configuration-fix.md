# MariaDB SSL 配置修复：connect_args 正确用法

## 🐛 问题

使用 `mysql+aiomysql://user:***REMOVED***word@host:port/database?ssl_verify_cert=false` 时报错：

```
connect() got an unexpected keyword argument 'ssl_verify_cert'
```

## ✅ 解决方案

aiomysql **不支持**通过 URL 查询参数传递 `ssl_verify_cert`。必须使用 `connect_args` 传递 SSL 配置。

## 📝 代码修改

### 修改 `shared/common/database.py`

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

### 修改 `shared/app/service_factory.py`

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

### 修改 `shared/common/database.py` 中的 `init_databases` 函数

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

## 🎯 使用示例

### 不验证证书（开发环境）

**环境变量**（`.env` 文件）：
```bash
MARIADB_SSL_ENABLED=true
MARIADB_SSL_VERIFY_CERT=false
```

**代码会自动处理**：
- 读取 `MARIADB_SSL_VERIFY_CERT=false`
- 在 `connect_args` 中设置 `ssl={'check_hostname': False}`
- 连接时跳过证书验证

### 验证证书（生产环境）

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

## 📚 参考

- [完整 SSL 配置文档](./43-mariadb-ssl-configuration.md)
- [aiomysql SSL 文档](https://aiomysql.readthedocs.io/en/latest/usage.html#ssl)

