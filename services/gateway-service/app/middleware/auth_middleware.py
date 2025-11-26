"""
认证中间件模块

负责验证请求的 JWT 令牌，调用 Auth Service 进行令牌验证
"""

import os
import sys
from typing import Any, Dict, Optional

import httpx

# 使用 try-except 方式处理路径导入
try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse
except ImportError:
    # 如果导入失败，添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from shared.common.i18n import parse_accept_language
    from shared.common.loguru_config import get_logger
    from shared.common.response import ErrorResponse


logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件

    拦截所有请求，验证 JWT 令牌有效性
    """

    def __init__(self, app):
        """初始化认证中间件

        Args:
            app: FastAPI 应用实例
        """
        super().__init__(app)

        # 公开路径白名单（不需要认证）
        self.public_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/test-error",  # 测试用
            # 认证端点（公开访问）
            "/api/v1/auth/admin/login",
            "/api/v1/auth/device/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",  # ✅ Token 刷新端点
            "/api/v1/auth/auto-refresh",  # ✅ 自动续期端点
            "/api/v1/auth/introspect",  # Token 验证端点
            # 浏览器插件接口（不需要认证）
            "/api/v1/host/hosts/available",  # 查询可用主机列表
            "/api/v1/host/hosts/retry-vnc",  # 获取重试 VNC 列表
            "/api/v1/host/hosts/release",  # 释放主机
            "/api/v1/host/vnc/report",  # 上报 VNC 连接结果
            "/api/v1/host/vnc/connect",  # 获取 VNC 连接信息
            # ⚠️ WebSocket 路由需要在路由级别进行认证检查，
            # 不能在中间件级别设为公开路径，否则无法强制认证
        }

        # ✅ 从配置读取认证服务 URL 和端口（兼容 Docker 和本地开发）
        # 优先级：AUTH_SERVICE_URL > (AUTH_SERVICE_IP + AUTH_SERVICE_PORT) > 自动判定（Docker/本地）
        auth_service_url = os.getenv("AUTH_SERVICE_URL")
        if auth_service_url:
            # 如果设置了完整的 URL，直接使用
            self.auth_service_url = auth_service_url.rstrip("/")
        else:
            # 否则从 IP 和端口构建（根据运行环境自动选择默认值）
            is_docker_env = os.getenv("DOCKER_ENV") == "true" or os.path.exists("/.dockerenv")

            auth_service_host = (
                os.getenv("AUTH_SERVICE_IP")
                or ("auth-service" if is_docker_env else "127.0.0.1")
            )
            auth_service_port = int(
                os.getenv("AUTH_SERVICE_PORT", "8001")
            )

            self.auth_service_url = f"http://{auth_service_host}:{auth_service_port}"

        logger.info(
            "认证中间件初始化完成",
            extra={
                "auth_service_url": self.auth_service_url,
            },
        )

        # ✅ 从配置读取 HTTP 客户端超时配置
        auth_timeout = float(os.getenv("AUTH_MIDDLEWARE_TIMEOUT", "10.0"))
        auth_connect_timeout = float(os.getenv("AUTH_MIDDLEWARE_CONNECT_TIMEOUT", "5.0"))
        self.timeout = httpx.Timeout(auth_timeout, connect=auth_connect_timeout)

    async def dispatch(self, request: Request, call_next):
        """处理请求

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        # ✅ 处理 OPTIONS 预检请求（CORS 预检请求）
        # OPTIONS 请求应该直接通过，由 CORS 中间件处理
        if request.method == "OPTIONS":
            logger.debug(
                "OPTIONS 预检请求，跳过认证检查",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            return await call_next(request)

        # 获取 Authorization 头（使用多种方式确保兼容性）
        # Starlette 的 headers 对象是大小写不敏感的，但为了确保兼容性，使用多种方式提取
        auth_header = None

        # 方式1: 标准方式（Starlette headers 是大小写不敏感的）
        auth_header = request.headers.get("Authorization")

        # 方式2: 如果方式1失败，尝试使用小写键名
        if not auth_header:
            auth_header = request.headers.get("authorization")

        # 方式3: 如果还是找不到，尝试遍历所有 headers 查找（处理特殊情况）
        if not auth_header:
            for key, value in request.headers.items():
                if key.lower() == "authorization":
                    auth_header = value
                    logger.debug(
                        "从 headers 遍历中找到 Authorization 头",
                        extra={
                            "header_key": key,
                            "header_value": value,
                            "header_value_preview": value[:20] + "..." if len(value) > 20 else value,
                        },
                    )
                    break

        has_token = bool(auth_header)

        # 调试日志：记录所有 header 键（仅当找不到 Authorization 时，用于调试）
        if not auth_header:
            all_header_keys = list(request.headers.keys())
            logger.warning(
                "未找到 Authorization 头，记录所有 header 键用于调试",
                extra={
                    "all_header_keys": all_header_keys,
                    "header_count": len(all_header_keys),
                    "path": request.url.path,
                    "method": request.method,
                },
            )

        # 检查是否为公开路径
        is_public = self._is_public_path(request.url.path)

        # 详细的请求日志
        logger.info(
            "认证中间件处理请求",
            extra={
                "path": request.url.path,
                "method": request.method,
                "is_public_path": is_public,
                "has_authorization_header": has_token,
                "client_host": request.client.host if request.client else "unknown",
            },
        )

        # 如果是公开路径，跳过认证
        if is_public:
            logger.info(
                "公开路径，跳过认证检查",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            return await call_next(request)

        # 检查是否有 Authorization 头
        if not auth_header:
            logger.warning(
                "受保护路径缺少 Authorization 头",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host if request.client else "unknown",
                },
            )
            return self._unauthorized_response(
                request=request,
                message="缺少认证令牌",
                message_key="error.auth.missing_token",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "请在请求头中添加 Authorization: Bearer <token>",
                },
            )

        # 验证令牌格式
        if not auth_header.startswith("Bearer "):
            logger.warning(
                "无效的 Authorization 头格式",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "auth_header_prefix": auth_header[:20] if len(auth_header) > 20 else auth_header,
                },
            )
            return self._unauthorized_response(
                request=request,
                message="无效的认证令牌格式",
                message_key="error.auth.invalid_token_format",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "Authorization 头必须使用 Bearer 格式",
                    "expected_format": "Bearer <token>",
                },
            )

        # 提取令牌
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        token_preview = token[:8] + "..." if len(token) > 8 else token

        logger.debug(
            "开始验证令牌",
            extra={
                "path": request.url.path,
                "method": request.method,
                "token_preview": token_preview,
            },
        )

        # 验证令牌
        user_info = await self._verify_token(token, request.url.path, request.method)

        # 处理验证结果
        if not user_info:
            logger.warning(
                "令牌验证失败，拒绝访问",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "token_preview": token_preview,
                },
            )
            return self._unauthorized_response(
                request=request,
                message="无效或过期的认证令牌",
                message_key="error.auth.token_invalid_or_expired",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "令牌可能已过期或无效，请重新登录获取新令牌",
                },
            )

        # 检查是否为服务错误（超时或连接错误）
        if isinstance(user_info, dict) and "error_type" in user_info:
            error_type = user_info["error_type"]

            if error_type == "timeout":
                logger.error(
                    "认证服务超时，返回 504 错误",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    request=request,
                    code=504,
                    message="认证服务响应超时，请稍后重试",
                    message_key="error.auth.service_timeout",
                    error_code="GATEWAY_TIMEOUT",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": "认证服务当前响应缓慢，请稍后重试",
                    },
                )

            if error_type == "connection_error":
                logger.error(
                    "无法连接到认证服务，返回 503 错误",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    request=request,
                    code=503,
                    message="认证服务暂时不可用，请稍后重试",
                    message_key="error.auth.service_unavailable",
                    error_code="SERVICE_UNAVAILABLE",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": "认证服务当前不可用，请联系系统管理员或稍后重试",
                    },
                )

            if error_type == "request_error":
                logger.error(
                    "认证服务请求错误，返回 502 错误",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "token_preview": token_preview,
                    },
                )
                return self._create_error_response(
                    request=request,
                    code=502,
                    message="认证服务请求失败",
                    message_key="error.auth.service_error",
                    error_code="BAD_GATEWAY",
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "service": "auth-service",
                        "hint": "网关无法从认证服务获取有效响应",
                    },
                )

            # 其他未知错误类型，返回 500
            logger.error(
                "认证过程中发生未知错误",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": error_type,
                    "token_preview": token_preview,
                },
            )
            return self._create_error_response(
                request=request,
                code=500,
                message="认证过程中发生内部错误",
                message_key="error.internal",
                error_code="INTERNAL_ERROR",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "hint": "系统内部错误，请联系系统管理员",
                },
            )

        # 将用户信息添加到请求状态
        request.state.user = user_info

        logger.info(
            "令牌验证成功，允许访问",
            extra={
                "path": request.url.path,
                "method": request.method,
                "user_id": user_info.get("user_id"),
                "username": user_info.get("username"),
                "user_type": user_info.get("user_type"),
            },
        )

        # 继续处理请求
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """检查是否为公开路径

        Args:
            path: 请求路径

        Returns:
            是否为公开路径
        """
        # 移除查询参数
        clean_path = path.split("?")[0]

        # 移除尾部斜杠（但保留根路径 "/"）
        if clean_path != "/" and clean_path.endswith("/"):
            clean_path = clean_path.rstrip("/")

        logger.debug(
            "检查路径是否为公开路径",
            extra={
                "original_path": path,
                "clean_path": clean_path,
                "public_paths_count": len(self.public_paths),
            },
        )

        # 检查精确匹配
        if clean_path in self.public_paths:
            logger.debug(
                "路径精确匹配公开路径",
                extra={
                    "path": clean_path,
                    "match_type": "exact",
                },
            )
            return True

        # ✅ 检查前缀匹配（用于文档路径和 WebSocket 路由）
        # 支持前缀匹配的路径模式：
        # - /docs, /redoc, /openapi.json (文档路径)
        # - /host/, /auth/, /admin/, /ws/ (WebSocket 路由)
        prefix_match_paths = {
            "/docs",  # Swagger UI
            "/redoc",  # ReDoc
            "/openapi.json",  # OpenAPI spec
            # ⚠️ WebSocket 路由 (/ws/, /host/, /auth/, /admin/) 已移除
            # 需要在路由级别进行认证检查
        }

        for prefix_path in prefix_match_paths:
            if clean_path.startswith(prefix_path):
                logger.debug(
                    "路径前缀匹配公开路径",
                    extra={
                        "path": clean_path,
                        "matched_prefix": prefix_path,
                        "match_type": "prefix",
                    },
                )
                return True

        logger.debug(
            "路径不是公开路径，需要认证",
            extra={
                "path": clean_path,
                "checked_against_paths": list(self.public_paths),
            },
        )
        return False

    async def _verify_token(
        self, token: str, request_path: str = "", request_method: str = ""
    ) -> Optional[Dict[str, Any]]:
        """验证 JWT 令牌

        调用 Auth Service 的 introspect 端点验证令牌

        Args:
            token: JWT 访问令牌
            request_path: 请求路径（用于日志）
            request_method: 请求方法（用于日志）

        Returns:
            用户信息，如果验证失败则返回 None
            特殊情况：返回包含 error_type 的字典表示服务错误
        """
        token_preview = token[:8] + "..." if len(token) > 8 else token

        try:
            # 调用 Auth Service 的 introspect 端点来验证令牌
            # ✅ 正确: auth_router 使用 prefix="/auth" 注册，所以端点是 /api/v1/auth/introspect
            introspect_url = f"{self.auth_service_url}/api/v1/auth/introspect"

            logger.debug(
                "调用 Auth Service 验证令牌",
                extra={
                    "introspect_url": introspect_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(
                    "准备调用 Auth Service introspect",
                    extra={
                        "url": introspect_url,
                        "timeout": self.timeout,
                        "token_preview": token_preview,
                    },
                )

                response = await client.post(
                    introspect_url,
                    json={"token": token},  # 使用 JSON 格式
                    headers={"Content-Type": "application/json"},
                )

                logger.debug(
                    "Auth Service 响应",
                    extra={
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] if response.text else "",
                        "token_preview": token_preview,
                    },
                )

                if response.status_code == 200:
                    result = response.json()

                    # 检查令牌是否有效
                    if result.get("code") == 200:
                        data = result.get("data", {})
                        if data.get("active"):
                            # 构造用户信息
                            user_info = {
                                "user_id": data.get("user_id"),  # 修正：auth-service 返回的是 user_id 而不是 sub
                                "username": data.get("username"),
                                "user_type": data.get("user_type"),
                                "active": data.get("active"),
                            }

                            logger.info(
                                "令牌验证成功 - Auth Service 返回有效用户信息",
                                extra={
                                    "user_id": user_info.get("user_id"),
                                    "username": user_info.get("username"),
                                    "user_type": user_info.get("user_type"),
                                    "token_preview": token_preview,
                                    "request_path": request_path,
                                },
                            )
                            return user_info
                        logger.warning(
                            "令牌验证失败 - 令牌未激活",
                            extra={
                                "token_preview": token_preview,
                                "active": data.get("active"),
                                "request_path": request_path,
                                "request_method": request_method,
                                "reason": "token_inactive",
                            },
                        )
                    else:
                        logger.warning(
                            "令牌验证失败 - Auth Service 返回错误码",
                            extra={
                                "response_code": result.get("code"),
                                "response_message": result.get("message"),
                                "token_preview": token_preview,
                                "request_path": request_path,
                                "request_method": request_method,
                                "reason": "auth_service_error",
                            },
                        )
                else:
                    logger.warning(
                        "令牌验证失败 - HTTP 状态码异常",
                        extra={
                            "status_code": response.status_code,
                            "response_text": response.text[:200] if response.text else "",
                            "token_preview": token_preview,
                            "request_path": request_path,
                            "request_method": request_method,
                            "reason": "http_error",
                        },
                    )
                return None

        except httpx.TimeoutException as e:
            logger.error(
                "令牌验证超时 - Auth Service 响应超时",
                extra={
                    "auth_service_url": self.auth_service_url,
                    "timeout_config": str(self.timeout),
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_type": "timeout",
                    "error_detail": str(e),
                },
            )
            # 返回特殊标记，表示超时错误
            return {"error_type": "timeout"}

        except httpx.ConnectError as e:
            logger.error(
                "无法连接到认证服务 - 网络连接失败",
                extra={
                    "auth_service_url": self.auth_service_url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_detail": "connection_refused_or_network_unreachable",
                },
            )
            # 返回特殊标记，表示连接错误
            return {"error_type": "connection_error"}

        except httpx.HTTPStatusError as e:
            logger.error(
                "Auth Service 返回 HTTP 错误状态",
                extra={
                    "status_code": e.response.status_code,
                    "response_text": e.response.text[:200] if e.response.text else "",
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                    "error_type": "http_status_error",
                },
            )
            return None

        except httpx.RequestError as e:
            logger.error(
                "Auth Service 请求错误",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
            )
            return {"error_type": "request_error"}

        except Exception as e:
            logger.error(
                "令牌验证异常 - 未预期的错误",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "auth_service_url": self.auth_service_url,
                    "token_preview": token_preview,
                    "request_path": request_path,
                    "request_method": request_method,
                },
                exc_info=True,
            )
            return None

    def _create_error_response(
        self,
        request: Request,
        code: int,
        message: str,
        error_code: str,
        message_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """创建统一的错误响应（支持多语言）

        Args:
            request: 请求对象（用于获取语言偏好）
            code: HTTP 状态码
            message: 错误消息（备用消息）
            error_code: 错误类型标识
            message_key: 翻译键（可选）
            details: 错误详情（可选）

        Returns:
            JSON 响应
        """
        # 获取语言偏好
        accept_language = request.headers.get("Accept-Language")
        locale = parse_accept_language(accept_language)

        error_response = ErrorResponse(
            code=code,
            message=message,  # 备用消息
            message_key=message_key,
            error_code=error_code,
            details=details,
            locale=locale,
            **(details or {}),  # 传递格式化变量
        )

        logger.warning(
            "返回错误响应",
            extra={
                "status_code": code,
                "error_code": error_code,
                "message": message,
                "request_id": error_response.request_id,
            },
        )

        return JSONResponse(
            status_code=code,
            content=error_response.model_dump(),
        )

    def _unauthorized_response(
        self,
        request: Request,
        message: str,
        message_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """返回未授权响应（401）（支持多语言）

        Args:
            request: 请求对象（用于获取语言偏好）
            message: 错误消息（备用消息）
            message_key: 翻译键（可选）
            details: 错误详情（可选）

        Returns:
            JSON 响应
        """
        return self._create_error_response(
            request=request,
            code=401,
            message=message,
            message_key=message_key,
            error_code="UNAUTHORIZED",
            details=details,
        )
