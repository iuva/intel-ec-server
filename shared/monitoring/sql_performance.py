"""
SQL性能监控模块

提供SQL查询性能监控和慢查询检测功能
"""

import hashlib
import logging
import re
import time
import traceback
from contextlib import contextmanager
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import Pool

from shared.common.loguru_config import get_logger
from shared.monitoring.metrics import (
    db_slow_query_duration_seconds,
    db_slow_queries_total,
)

logger = get_logger(__name__)


class SQLPerformanceMonitor:
    """SQL性能监控器

    自动监控SQL查询性能，检测慢查询并记录详细信息
    """

    def __init__(
        self,
        slow_query_threshold: float = 2.0,
        enabled: bool = True,
        service_name: str = "unknown",
    ) -> None:
        """初始化SQL性能监控器

        Args:
            slow_query_threshold: 慢查询阈值（秒），默认2秒
            enabled: 是否启用监控
            service_name: 服务名称，用于指标标签
        """
        self.slow_query_threshold = slow_query_threshold
        self.enabled = enabled
        self.service_name = service_name
        self._query_timings: Dict[str, float] = {}
        self._query_contexts: Dict[str, Dict[str, Any]] = {}

    def _generate_sql_hash(self, sql: str) -> str:
        """生成SQL语句的哈希值（用于去重）

        Args:
            sql: SQL语句

        Returns:
            SQL哈希值（前8位）
        """
        # 标准化SQL（移除多余空格和换行）
        normalized_sql = re.sub(r"\s+", " ", sql.strip())
        sql_hash = hashlib.md5(normalized_sql.encode()).hexdigest()[:8]
        return sql_hash

    def _parse_sql_info(self, sql: str) -> Tuple[str, str]:
        """解析SQL语句，提取操作类型和表名

        Args:
            sql: SQL语句

        Returns:
            (操作类型, 表名)
        """
        sql_upper = sql.upper().strip()

        # 提取操作类型
        operation = "unknown"
        if sql_upper.startswith("SELECT"):
            operation = "select"
        elif sql_upper.startswith("INSERT"):
            operation = "insert"
        elif sql_upper.startswith("UPDATE"):
            operation = "update"
        elif sql_upper.startswith("DELETE"):
            operation = "delete"
        elif sql_upper.startswith("CREATE"):
            operation = "create"
        elif sql_upper.startswith("ALTER"):
            operation = "alter"
        elif sql_upper.startswith("DROP"):
            operation = "drop"

        # 提取表名（简化版，适用于常见SQL模式）
        table = "unknown"
        table_patterns = [
            r"FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            r"INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            r"UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            r"DELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        ]

        for pattern in table_patterns:
            match = re.search(pattern, sql_upper, re.IGNORECASE)
            if match:
                table = match.group(1).lower()
                break

        return operation, table

    def _record_slow_query(
        self,
        sql: str,
        parameters: Optional[Dict[str, Any]],
        duration: float,
        operation: str,
        table: str,
        sql_hash: str,
    ) -> None:
        """记录慢查询

        Args:
            sql: SQL语句
            parameters: SQL参数
            duration: 执行时间（秒）
            operation: 操作类型
            table: 表名
            sql_hash: SQL哈希值
        """
        # 记录Prometheus指标
        try:
            db_slow_queries_total.labels(
                operation=operation,
                table=table,
                service=self.service_name,
                sql_hash=sql_hash,
            ).inc()

            db_slow_query_duration_seconds.labels(
                operation=operation,
                table=table,
                service=self.service_name,
                sql_hash=sql_hash,
            ).observe(duration)
        except Exception as e:
            logger.warning(f"记录慢查询指标失败: {e!s}", exc_info=True)

        # 记录结构化日志
        try:
            from shared.common.loguru_config import log_slow_query

            log_slow_query(
                sql=sql,
                parameters=parameters,
                duration_ms=duration * 1000,
                operation=operation,
                table=table,
                sql_hash=sql_hash,
            )
        except Exception as e:
            logger.warning(f"记录慢查询日志失败: {e!s}", exc_info=True)

    def _before_cursor_execute(
        self,
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Optional[Dict[str, Any]],
        context: Any,
        executemany: bool,
    ) -> None:
        """SQL执行前的回调

        Args:
            conn: 数据库连接
            cursor: 游标
            statement: SQL语句
            parameters: SQL参数
            context: 执行上下文
            executemany: 是否批量执行
        """
        if not self.enabled:
            return

        # 记录开始时间
        query_id = id(cursor)
        self._query_timings[query_id] = time.time()

        # 保存查询上下文
        self._query_contexts[query_id] = {
            "sql": statement,
            "parameters": parameters,
            "executemany": executemany,
        }

    def _after_cursor_execute(
        self,
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Optional[Dict[str, Any]],
        context: Any,
        executemany: bool,
    ) -> None:
        """SQL执行后的回调

        Args:
            conn: 数据库连接
            cursor: 游标
            statement: SQL语句
            parameters: SQL参数
            context: 执行上下文
            executemany: 是否批量执行
        """
        if not self.enabled:
            return

        query_id = id(cursor)
        start_time = self._query_timings.pop(query_id, None)
        query_context = self._query_contexts.pop(query_id, None)

        if start_time is None or query_context is None:
            return

        # 计算执行时间
        duration = time.time() - start_time

        # 检查是否为慢查询
        if duration >= self.slow_query_threshold:
            sql = query_context["sql"]
            sql_params = query_context.get("parameters")

            # 解析SQL信息
            operation, table = self._parse_sql_info(sql)
            sql_hash = self._generate_sql_hash(sql)

            # 记录慢查询
            self._record_slow_query(
                sql=sql,
                parameters=sql_params,
                duration=duration,
                operation=operation,
                table=table,
                sql_hash=sql_hash,
            )

    def attach_to_engine(self, engine: Any) -> None:
        """将监控器附加到SQLAlchemy引擎

        Args:
            engine: SQLAlchemy引擎（同步或异步）
        """
        if not self.enabled:
            return

        # 监听同步引擎
        if isinstance(engine, Engine):
            event.listen(engine, "before_cursor_execute", self._before_cursor_execute)
            event.listen(engine, "after_cursor_execute", self._after_cursor_execute)
            logger.info(f"SQL性能监控已附加到同步引擎: {self.service_name}")
        # 监听异步引擎
        elif isinstance(engine, AsyncEngine):
            # 异步引擎需要同步包装器
            sync_engine = engine.sync_engine
            event.listen(sync_engine, "before_cursor_execute", self._before_cursor_execute)
            event.listen(sync_engine, "after_cursor_execute", self._after_cursor_execute)
            logger.info(f"SQL性能监控已附加到异步引擎: {self.service_name}")
        else:
            logger.warning(f"不支持的引擎类型: {type(engine)}")

    def detach_from_engine(self, engine: Any) -> None:
        """从SQLAlchemy引擎移除监控器

        Args:
            engine: SQLAlchemy引擎（同步或异步）
        """
        if not self.enabled:
            return

        try:
            if isinstance(engine, Engine):
                event.remove(engine, "before_cursor_execute", self._before_cursor_execute)
                event.remove(engine, "after_cursor_execute", self._after_cursor_execute)
            elif isinstance(engine, AsyncEngine):
                sync_engine = engine.sync_engine
                event.remove(sync_engine, "before_cursor_execute", self._before_cursor_execute)
                event.remove(sync_engine, "after_cursor_execute", self._after_cursor_execute)
            logger.info(f"SQL性能监控已从引擎移除: {self.service_name}")
        except Exception as e:
            logger.warning(f"移除SQL性能监控失败: {e!s}", exc_info=True)


# 全局SQL性能监控器实例
_sql_monitor: Optional[SQLPerformanceMonitor] = None


def get_sql_monitor() -> Optional[SQLPerformanceMonitor]:
    """获取全局SQL性能监控器实例

    Returns:
        SQL性能监控器实例，如果未初始化则返回None
    """
    return _sql_monitor


def init_sql_monitor(
    slow_query_threshold: float = 2.0,
    enabled: bool = True,
    service_name: str = "unknown",
) -> SQLPerformanceMonitor:
    """初始化全局SQL性能监控器

    Args:
        slow_query_threshold: 慢查询阈值（秒），默认2秒
        enabled: 是否启用监控
        service_name: 服务名称

    Returns:
        初始化的SQL性能监控器实例
    """
    global _sql_monitor
    _sql_monitor = SQLPerformanceMonitor(
        slow_query_threshold=slow_query_threshold,
        enabled=enabled,
        service_name=service_name,
    )
    logger.info(
        f"SQL性能监控器已初始化: service={service_name}, threshold={slow_query_threshold}s, enabled={enabled}"
    )
    return _sql_monitor

