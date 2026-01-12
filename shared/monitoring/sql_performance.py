"""
SQL Performance Monitoring Module

Provides SQL query performance monitoring and slow query detection functionality
"""

import hashlib
import re
import time
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from shared.common.loguru_config import get_logger
from shared.monitoring.metrics import (
    db_slow_query_duration_seconds,
    db_slow_queries_total,
)

logger = get_logger(__name__)


class SQLPerformanceMonitor:
    """SQL Performance Monitor

    Automatically monitors SQL query performance, detects slow queries and records detailed information
    """

    def __init__(
        self,
        slow_query_threshold: float = 2.0,
        enabled: bool = True,
        service_name: str = "unknown",
    ) -> None:
        """Initialize SQL performance monitor

        Args:
            slow_query_threshold: Slow query threshold (seconds), default 2 seconds
            enabled: Whether to enable monitoring
            service_name: Service name, used for metrics labels
        """
        self.slow_query_threshold = slow_query_threshold
        self.enabled = enabled
        self.service_name = service_name
        self._query_timings: Dict[str, float] = {}
        self._query_contexts: Dict[str, Dict[str, Any]] = {}

    def _generate_sql_hash(self, sql: str) -> str:
        """Generate hash value for SQL statement (for deduplication)

        Args:
            sql: SQL statement

        Returns:
            SQL hash value (first 8 characters)
        """
        # Normalize SQL (remove extra spaces and line breaks)
        normalized_sql = re.sub(r"\s+", " ", sql.strip())
        sql_hash = hashlib.md5(normalized_sql.encode()).hexdigest()[:8]
        return sql_hash

    def _parse_sql_info(self, sql: str) -> Tuple[str, str]:
        """Parse SQL statement, extract operation type and table name

        Args:
            sql: SQL statement

        Returns:
            (operation type, table name)
        """
        sql_upper = sql.upper().strip()

        # Extract operation type
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

        # Extract table name (simplified version, suitable for common SQL patterns)
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
        """Record slow query

        Args:
            sql: SQL statement
            parameters: SQL parameters
            duration: Execution time (seconds)
            operation: Operation type
            table: Table name
            sql_hash: SQL hash value
        """
        # Record Prometheus metrics
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
            logger.warning(f"Failed to record slow query metrics: {e!s}", exc_info=True)

        # Record structured logs
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
            logger.warning(f"Failed to record slow query logs: {e!s}", exc_info=True)

    def _before_cursor_execute(
        self,
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Optional[Dict[str, Any]],
        context: Any,
        executemany: bool,
    ) -> None:
        """Callback before SQL execution

        Args:
            conn: Database connection
            cursor: Cursor
            statement: SQL statement
            parameters: SQL parameters
            context: Execution context
            executemany: Whether to execute in batches
        """
        if not self.enabled:
            return

        # Record start time
        query_id = str(id(cursor))  # Convert to string to match dictionary key type
        self._query_timings[query_id] = time.time()

        # Save query context
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
        """Callback after SQL execution

        Args:
            conn: Database connection
            cursor: Cursor
            statement: SQL statement
            parameters: SQL parameters
            context: Execution context
            executemany: Whether to execute in batches
        """
        if not self.enabled:
            return

        query_id = str(id(cursor))  # Convert to string to match dictionary key type
        start_time = self._query_timings.pop(query_id, None)
        query_context = self._query_contexts.pop(query_id, None)

        if start_time is None or query_context is None:
            return

        # Calculate execution time
        duration = time.time() - start_time

        # Check if it's a slow query
        if duration >= self.slow_query_threshold:
            sql = query_context["sql"]
            sql_params = query_context.get("parameters")

            # Parse SQL information
            operation, table = self._parse_sql_info(sql)
            sql_hash = self._generate_sql_hash(sql)

            # Record slow query
            self._record_slow_query(
                sql=sql,
                parameters=sql_params,
                duration=duration,
                operation=operation,
                table=table,
                sql_hash=sql_hash,
            )

    def attach_to_engine(self, engine: Any) -> None:
        """Attach monitor to SQLAlchemy engine

        Args:
            engine: SQLAlchemy engine (sync or async)
        """
        if not self.enabled:
            return

        # Listen to sync engine
        if isinstance(engine, Engine):
            event.listen(engine, "before_cursor_execute", self._before_cursor_execute)
            event.listen(engine, "after_cursor_execute", self._after_cursor_execute)
            logger.info(f"SQL performance monitoring attached to sync engine: {self.service_name}")
        # Listen to async engine
        elif isinstance(engine, AsyncEngine):
            # Async engine needs sync wrapper
            sync_engine = engine.sync_engine
            event.listen(sync_engine, "before_cursor_execute", self._before_cursor_execute)
            event.listen(sync_engine, "after_cursor_execute", self._after_cursor_execute)
            logger.info(f"SQL performance monitoring attached to async engine: {self.service_name}")
        else:
            logger.warning(f"Unsupported engine type: {type(engine)}")

    def detach_from_engine(self, engine: Any) -> None:
        """Remove monitor from SQLAlchemy engine

        Args:
            engine: SQLAlchemy engine (sync or async)
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
            logger.info(f"SQL performance monitoring removed from engine: {self.service_name}")
        except Exception as e:
            logger.warning(f"Failed to remove SQL performance monitoring: {e!s}", exc_info=True)


# Global SQL performance monitor instance
_sql_monitor: Optional[SQLPerformanceMonitor] = None


def get_sql_monitor() -> Optional[SQLPerformanceMonitor]:
    """Get global SQL performance monitor instance

    Returns:
        SQL performance monitor instance, or None if not initialized
    """
    return _sql_monitor


def init_sql_monitor(
    slow_query_threshold: float = 2.0,
    enabled: bool = True,
    service_name: str = "unknown",
) -> SQLPerformanceMonitor:
    """Initialize global SQL performance monitor

    Args:
        slow_query_threshold: Slow query threshold (seconds), default 2 seconds
        enabled: Whether to enable monitoring
        service_name: Service name

    Returns:
        Initialized SQL performance monitor instance
    """
    global _sql_monitor
    _sql_monitor = SQLPerformanceMonitor(
        slow_query_threshold=slow_query_threshold,
        enabled=enabled,
        service_name=service_name,
    )
    message = (
        f"SQL Performance Monitor initialized: service={service_name}, "
        f"threshold={slow_query_threshold}s, enabled={enabled}"
    )
    logger.info(message)
    return _sql_monitor
