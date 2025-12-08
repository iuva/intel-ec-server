#!/usr/bin/env python3
"""
慢查询分析工具

解析日志文件中的慢查询记录，生成统计报告和分析结果
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class SlowQueryAnalyzer:
    """慢查询分析器"""

    def __init__(self, log_file: str) -> None:
        """初始化分析器

        Args:
            log_file: 日志文件路径
        """
        self.log_file = Path(log_file)
        if not self.log_file.exists():
            raise FileNotFoundError(f"日志文件不存在: {log_file}")

        self.slow_queries: List[Dict[str, Any]] = []

    def parse_log_file(self) -> None:
        """解析日志文件，提取慢查询记录"""
        logger.info(f"开始解析日志文件: {self.log_file}")

        # Loguru日志格式：时间戳 | 级别 | 模块 | 消息 | extra数据（JSON）
        log_pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+\|\s+(\w+)\s+\|\s+([^\|]+)\s+\|\s+(.+?)(?:\s+\|\s+({.*}))?$"
        )

        slow_query_count = 0
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or "慢查询检测" not in line:
                    continue

                try:
                    # 解析日志行
                    match = log_pattern.match(line)
                    if not match:
                        continue

                    timestamp_str, level, module, message, extra_json = match.groups()

                    # 解析extra数据
                    extra_data: Dict[str, Any] = {}
                    if extra_json:
                        try:
                            extra_data = json.loads(extra_json)
                        except json.JSONDecodeError:
                            # 尝试修复常见的JSON格式问题
                            extra_json = extra_json.replace("'", '"')
                            try:
                                extra_data = json.loads(extra_json)
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析extra数据 (行 {line_num}): {extra_json[:100]}")

                    # 提取慢查询信息
                    if "sql" in extra_data and "duration_ms" in extra_data:
                        slow_query = {
                            "timestamp": timestamp_str,
                            "level": level,
                            "module": module.strip(),
                            "sql": extra_data.get("sql", ""),
                            "duration_ms": float(extra_data.get("duration_ms", 0)),
                            "duration_seconds": float(extra_data.get("duration_seconds", 0)),
                            "operation": extra_data.get("operation", "unknown"),
                            "table": extra_data.get("table", "unknown"),
                            "sql_hash": extra_data.get("sql_hash", ""),
                            "parameters": extra_data.get("parameters"),
                            "stack_trace": extra_data.get("stack_trace", []),
                            "line_number": line_num,
                        }
                        self.slow_queries.append(slow_query)
                        slow_query_count += 1

                except Exception as e:
                    logger.warning(f"解析日志行失败 (行 {line_num}): {e!s}")

        logger.info(f"解析完成，共找到 {slow_query_count} 条慢查询记录")

    def generate_statistics(self) -> Dict[str, Any]:
        """生成统计信息

        Returns:
            统计信息字典
        """
        if not self.slow_queries:
            return {
                "total_count": 0,
                "message": "未找到慢查询记录",
            }

        # 基本统计
        total_count = len(self.slow_queries)
        total_duration_ms = sum(q["duration_ms"] for q in self.slow_queries)
        avg_duration_ms = total_duration_ms / total_count
        max_duration_ms = max(q["duration_ms"] for q in self.slow_queries)
        min_duration_ms = min(q["duration_ms"] for q in self.slow_queries)

        # 按操作类型统计
        operation_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_ms": 0.0})
        for query in self.slow_queries:
            op = query["operation"]
            operation_stats[op]["count"] += 1
            operation_stats[op]["total_ms"] += query["duration_ms"]

        for op in operation_stats:
            operation_stats[op]["avg_ms"] = operation_stats[op]["total_ms"] / operation_stats[op]["count"]

        # 按表统计
        table_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_ms": 0.0})
        for query in self.slow_queries:
            table = query["table"]
            table_stats[table]["count"] += 1
            table_stats[table]["total_ms"] += query["duration_ms"]

        for table in table_stats:
            table_stats[table]["avg_ms"] = table_stats[table]["total_ms"] / table_stats[table]["count"]

        # 按SQL哈希统计（相同SQL的不同执行）
        sql_hash_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_ms": 0.0, "sql": "", "max_ms": 0.0}
        )
        for query in self.slow_queries:
            sql_hash = query["sql_hash"]
            sql_hash_stats[sql_hash]["count"] += 1
            sql_hash_stats[sql_hash]["total_ms"] += query["duration_ms"]
            sql_hash_stats[sql_hash]["sql"] = query["sql"][:200]  # 保存SQL前200字符
            sql_hash_stats[sql_hash]["max_ms"] = max(
                sql_hash_stats[sql_hash].get("max_ms", 0), query["duration_ms"]
            )

        for sql_hash in sql_hash_stats:
            sql_hash_stats[sql_hash]["avg_ms"] = (
                sql_hash_stats[sql_hash]["total_ms"] / sql_hash_stats[sql_hash]["count"]
            )

        return {
            "total_count": total_count,
            "duration_stats": {
                "total_ms": total_duration_ms,
                "avg_ms": avg_duration_ms,
                "max_ms": max_duration_ms,
                "min_ms": min_duration_ms,
            },
            "operation_stats": dict(operation_stats),
            "table_stats": dict(table_stats),
            "sql_hash_stats": dict(sql_hash_stats),
        }

    def get_top_slow_queries(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取Top N慢查询

        Args:
            top_n: 返回前N条

        Returns:
            慢查询列表（按耗时降序）
        """
        sorted_queries = sorted(self.slow_queries, key=lambda x: x["duration_ms"], reverse=True)
        return sorted_queries[:top_n]

    def print_report(self, top_n: int = 10) -> None:
        """打印分析报告

        Args:
            top_n: 显示Top N慢查询
        """
        stats = self.generate_statistics()

        if stats["total_count"] == 0:
            print("=" * 80)
            print("慢查询分析报告")
            print("=" * 80)
            print("\n未找到慢查询记录。")
            return

        print("=" * 80)
        print("慢查询分析报告")
        print("=" * 80)
        print(f"\n分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"日志文件: {self.log_file}")
        print(f"总慢查询数: {stats['total_count']}")

        # 耗时统计
        print("\n" + "-" * 80)
        print("耗时统计")
        print("-" * 80)
        duration_stats = stats["duration_stats"]
        print(f"  总耗时: {duration_stats['total_ms']:.2f} ms ({duration_stats['total_ms']/1000:.2f} s)")
        print(f"  平均耗时: {duration_stats['avg_ms']:.2f} ms ({duration_stats['avg_ms']/1000:.2f} s)")
        print(f"  最大耗时: {duration_stats['max_ms']:.2f} ms ({duration_stats['max_ms']/1000:.2f} s)")
        print(f"  最小耗时: {duration_stats['min_ms']:.2f} ms ({duration_stats['min_ms']/1000:.2f} s)")

        # 按操作类型统计
        print("\n" + "-" * 80)
        print("按操作类型统计")
        print("-" * 80)
        operation_stats = stats["operation_stats"]
        sorted_ops = sorted(operation_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        for op, op_stats in sorted_ops:
            print(f"  {op.upper():<10} - 次数: {op_stats['count']:>5}, 平均耗时: {op_stats['avg_ms']:>8.2f} ms")

        # 按表统计
        print("\n" + "-" * 80)
        print("按表统计")
        print("-" * 80)
        table_stats = stats["table_stats"]
        sorted_tables = sorted(table_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        for table, tbl_stats in sorted_tables[:20]:  # 只显示前20个表
            print(
                f"  {table:<30} - 次数: {tbl_stats['count']:>5}, 平均耗时: {tbl_stats['avg_ms']:>8.2f} ms"
            )

        # Top N慢查询
        print("\n" + "-" * 80)
        print(f"Top {top_n} 慢查询")
        print("-" * 80)
        top_queries = self.get_top_slow_queries(top_n)
        for idx, query in enumerate(top_queries, 1):
            print(f"\n{idx}. 耗时: {query['duration_ms']:.2f} ms ({query['duration_seconds']:.2f} s)")
            print(f"   操作: {query['operation'].upper()}")
            print(f"   表: {query['table']}")
            print(f"   SQL哈希: {query['sql_hash']}")
            print(f"   时间: {query['timestamp']}")
            sql_preview = query["sql"][:150].replace("\n", " ")
            print(f"   SQL: {sql_preview}...")
            if query.get("stack_trace"):
                print(f"   调用栈: {' -> '.join(query['stack_trace'][:3])}")

        # SQL哈希统计（相同SQL的不同执行）
        print("\n" + "-" * 80)
        print("相同SQL执行统计（按执行次数排序）")
        print("-" * 80)
        sql_hash_stats = stats["sql_hash_stats"]
        sorted_sql_hashes = sorted(sql_hash_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        for sql_hash, sql_stats in sorted_sql_hashes[:10]:  # 只显示前10个
            print(f"\n  SQL哈希: {sql_hash}")
            print(f"  执行次数: {sql_stats['count']}")
            print(f"  平均耗时: {sql_stats['avg_ms']:.2f} ms")
            print(f"  最大耗时: {sql_stats['max_ms']:.2f} ms")
            sql_preview = sql_stats["sql"][:150].replace("\n", " ")
            print(f"  SQL: {sql_preview}...")

        print("\n" + "=" * 80)


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="慢查询分析工具")
    parser.add_argument("log_file", help="日志文件路径")
    parser.add_argument(
        "-n",
        "--top-n",
        type=int,
        default=10,
        help="显示Top N慢查询（默认: 10）",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="输出JSON报告文件路径（可选）",
    )

    args = parser.parse_args()

    try:
        analyzer = SlowQueryAnalyzer(args.log_file)
        analyzer.parse_log_file()

        # 打印报告
        analyzer.print_report(top_n=args.top_n)

        # 输出JSON报告（如果指定）
        if args.output:
            stats = analyzer.generate_statistics()
            top_queries = analyzer.get_top_slow_queries(args.top_n)
            report = {
                "analysis_time": datetime.now().isoformat(),
                "log_file": str(args.log_file),
                "statistics": stats,
                "top_queries": top_queries,
            }

            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"\nJSON报告已保存到: {args.output}")

    except FileNotFoundError as e:
        logger.error(f"文件不存在: {e!s}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"分析失败: {e!s}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

