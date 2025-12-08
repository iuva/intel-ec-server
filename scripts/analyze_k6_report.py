#!/usr/bin/env python3
"""
k6 压测报告分析工具

解析 k6 导出的 JSON 格式报告，生成统计分析和可视化报告
支持生成 HTML、Markdown 和 JSON 格式的专业报告
"""

import argparse
import base64
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    import os
    import sys

    # 添加项目根目录到 Python 路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    sys.path.insert(0, project_root)
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class K6ReportAnalyzer:
    """k6 报告分析器"""

    def __init__(self, json_file: str) -> None:
        """初始化分析器

        Args:
            json_file: k6 JSON 报告文件路径
        """
        self.json_file = Path(json_file)
        if not self.json_file.exists():
            raise FileNotFoundError(f"报告文件不存在: {json_file}")

        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.points: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def parse_json_file(self) -> None:
        """解析 k6 JSON 报告文件"""
        logger.info(f"开始解析 k6 报告文件: {self.json_file}")

        point_count = 0
        metric_count = 0

        with open(self.json_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # 解析 Metric 定义
                    if data.get("type") == "Metric":
                        metric_name = data.get("metric")
                        if metric_name:
                            self.metrics[metric_name] = data.get("data", {})
                            metric_count += 1

                    # 解析 Point 数据点
                    elif data.get("type") == "Point":
                        point = {
                            "metric": data.get("metric"),
                            "time": data.get("data", {}).get("time"),
                            "value": data.get("data", {}).get("value"),
                            "tags": data.get("data", {}).get("tags", {}),
                        }

                        # 解析时间戳
                        if point["time"]:
                            try:
                                time_obj = datetime.fromisoformat(point["time"].replace("Z", "+00:00"))
                                if self.start_time is None or time_obj < self.start_time:
                                    self.start_time = time_obj
                                if self.end_time is None or time_obj > self.end_time:
                                    self.end_time = time_obj
                            except (ValueError, AttributeError):
                                ***REMOVED***

                        self.points.append(point)
                        point_count += 1

                except json.JSONDecodeError as e:
                    logger.warning(f"解析 JSON 行失败 (行 {line_num}): {e!s}")
                except Exception as e:
                    logger.warning(f"处理行失败 (行 {line_num}): {e!s}")

        logger.info(f"解析完成: {metric_count} 个指标定义, {point_count} 个数据点")

    def calculate_statistics(self) -> Dict[str, Any]:
        """计算统计信息

        Returns:
            统计信息字典
        """
        if not self.points:
            return {
                "total_points": 0,
                "message": "未找到数据点",
            }

        # 按指标分组
        metric_groups: Dict[str, List[float]] = defaultdict(list)
        metric_tags: Dict[str, Dict[str, Any]] = defaultdict(dict)

        for point in self.points:
            metric_name = point["metric"]
            value = point.get("value")
            tags = point.get("tags", {})

            if value is not None and isinstance(value, (int, float)):
                metric_groups[metric_name].append(float(value))
                # 保存标签信息（使用第一个点的标签）
                if metric_name not in metric_tags:
                    metric_tags[metric_name] = tags

        # 计算每个指标的统计信息
        stats: Dict[str, Dict[str, Any]] = {}
        for metric_name, values in metric_groups.items():
            if not values:
                continue

            sorted_values = sorted(values)
            count = len(values)
            total = sum(values)
            avg = total / count if count > 0 else 0
            min_val = min(values)
            max_val = max(values)

            # 计算百分位数
            def percentile(data: List[float], p: float) -> float:
                """计算百分位数"""
                if not data:
                    return 0.0
                k = (len(data) - 1) * p
                f = int(k)
                c = k - f
                if f + 1 < len(data):
                    return data[f] + c * (data[f + 1] - data[f])
                return data[f]

            p50 = percentile(sorted_values, 0.50)
            p75 = percentile(sorted_values, 0.75)
            p90 = percentile(sorted_values, 0.90)
            p95 = percentile(sorted_values, 0.95)
            p99 = percentile(sorted_values, 0.99)

            stats[metric_name] = {
                "count": count,
                "total": total,
                "avg": avg,
                "min": min_val,
                "max": max_val,
                "p50": p50,
                "p75": p75,
                "p90": p90,
                "p95": p95,
                "p99": p99,
                "tags": metric_tags.get(metric_name, {}),
            }

        # 计算 HTTP 请求相关统计
        http_stats = self._calculate_http_statistics()

        # 计算测试时长
        duration_seconds = 0
        if self.start_time and self.end_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()

        return {
            "test_duration": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": duration_seconds,
                "duration_formatted": self._format_duration(duration_seconds),
            },
            "total_points": len(self.points),
            "metrics_count": len(self.metrics),
            "metric_statistics": stats,
            "http_statistics": http_stats,
        }

    def _calculate_http_statistics(self) -> Dict[str, Any]:
        """计算 HTTP 请求相关统计"""
        http_reqs_points = [p for p in self.points if p["metric"] == "http_reqs"]
        http_duration_points = [p for p in self.points if p["metric"] == "http_req_duration"]
        http_failed_points = [p for p in self.points if p["metric"] == "http_req_failed"]

        # 按端点分组统计
        endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_requests": 0,
                "success_requests": 0,
                "failed_requests": 0,
                "durations": [],
                "status_codes": defaultdict(int),
            }
        )

        # 统计请求数
        for point in http_reqs_points:
            tags = point.get("tags", {})
            endpoint = tags.get("endpoint", "unknown")
            status = tags.get("status", "unknown")
            url = tags.get("url", "unknown")

            endpoint_stats[endpoint]["total_requests"] += int(point.get("value", 0))
            endpoint_stats[endpoint]["status_codes"][status] += int(point.get("value", 0))
            if status == "200":
                endpoint_stats[endpoint]["success_requests"] += int(point.get("value", 0))
            else:
                endpoint_stats[endpoint]["failed_requests"] += int(point.get("value", 0))

        # 统计响应时间
        for point in http_duration_points:
            tags = point.get("tags", {})
            endpoint = tags.get("endpoint", "unknown")
            value = point.get("value")
            if value is not None:
                endpoint_stats[endpoint]["durations"].append(float(value))

        # 计算每个端点的统计信息
        endpoint_summary: Dict[str, Dict[str, Any]] = {}
        for endpoint, stats_data in endpoint_stats.items():
            durations = stats_data["durations"]
            if durations:
                sorted_durations = sorted(durations)
                count = len(durations)
                total = sum(durations)
                avg = total / count if count > 0 else 0

                def percentile(data: List[float], p: float) -> float:
                    if not data:
                        return 0.0
                    k = (len(data) - 1) * p
                    f = int(k)
                    c = k - f
                    if f + 1 < len(data):
                        return data[f] + c * (data[f + 1] - data[f])
                    return data[f]

                endpoint_summary[endpoint] = {
                    "total_requests": stats_data["total_requests"],
                    "success_requests": stats_data["success_requests"],
                    "failed_requests": stats_data["failed_requests"],
                    "error_rate": (
                        stats_data["failed_requests"] / stats_data["total_requests"]
                        if stats_data["total_requests"] > 0
                        else 0
                    ),
                    "duration_stats": {
                        "count": count,
                        "avg_ms": avg,
                        "min_ms": min(durations),
                        "max_ms": max(durations),
                        "p50_ms": percentile(sorted_durations, 0.50),
                        "p95_ms": percentile(sorted_durations, 0.95),
                        "p99_ms": percentile(sorted_durations, 0.99),
                    },
                    "status_codes": dict(stats_data["status_codes"]),
                }
            else:
                endpoint_summary[endpoint] = {
                    "total_requests": stats_data["total_requests"],
                    "success_requests": stats_data["success_requests"],
                    "failed_requests": stats_data["failed_requests"],
                    "error_rate": (
                        stats_data["failed_requests"] / stats_data["total_requests"]
                        if stats_data["total_requests"] > 0
                        else 0
                    ),
                    "duration_stats": None,
                    "status_codes": dict(stats_data["status_codes"]),
                }

        # 计算总体统计
        total_requests = sum(s["total_requests"] for s in endpoint_summary.values())
        total_success = sum(s["success_requests"] for s in endpoint_summary.values())
        total_failed = sum(s["failed_requests"] for s in endpoint_summary.values())

        all_durations = []
        for stats_data in endpoint_stats.values():
            all_durations.extend(stats_data["durations"])

        overall_duration_stats = None
        if all_durations:
            sorted_all = sorted(all_durations)
            count = len(all_durations)
            total = sum(all_durations)
            avg = total / count if count > 0 else 0

            def percentile(data: List[float], p: float) -> float:
                if not data:
                    return 0.0
                k = (len(data) - 1) * p
                f = int(k)
                c = k - f
                if f + 1 < len(data):
                    return data[f] + c * (data[f + 1] - data[f])
                return data[f]

            overall_duration_stats = {
                "count": count,
                "avg_ms": avg,
                "min_ms": min(all_durations),
                "max_ms": max(all_durations),
                "p50_ms": percentile(sorted_all, 0.50),
                "p95_ms": percentile(sorted_all, 0.95),
                "p99_ms": percentile(sorted_all, 0.99),
            }

        return {
            "overall": {
                "total_requests": total_requests,
                "success_requests": total_success,
                "failed_requests": total_failed,
                "error_rate": total_failed / total_requests if total_requests > 0 else 0,
                "duration_stats": overall_duration_stats,
            },
            "by_endpoint": endpoint_summary,
        }

    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f} 秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} 分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} 小时"

    def print_report(self, top_n: int = 10) -> None:
        """打印分析报告

        Args:
            top_n: 显示 Top N 端点
        """
        stats = self.calculate_statistics()

        if stats.get("total_points") == 0:
            print("=" * 80)
            print("k6 压测报告分析")
            print("=" * 80)
            print("\n未找到数据点。")
            return

        print("=" * 80)
        print("k6 压测报告分析")
        print("=" * 80)
        print(f"\n分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"报告文件: {self.json_file}")
        print(f"数据点总数: {stats['total_points']}")
        print(f"指标数量: {stats['metrics_count']}")

        # 测试时长
        test_duration = stats.get("test_duration", {})
        if test_duration.get("start_time") and test_duration.get("end_time"):
            print("\n" + "-" * 80)
            print("测试时长")
            print("-" * 80)
            print(f"  开始时间: {test_duration['start_time']}")
            print(f"  结束时间: {test_duration['end_time']}")
            print(f"  持续时间: {test_duration.get('duration_formatted', 'N/A')}")

        # HTTP 总体统计
        http_stats = stats.get("http_statistics", {})
        overall = http_stats.get("overall", {})
        if overall:
            print("\n" + "-" * 80)
            print("HTTP 请求总体统计")
            print("-" * 80)
            print(f"  总请求数: {overall.get('total_requests', 0):,}")
            print(f"  成功请求: {overall.get('success_requests', 0):,}")
            print(f"  失败请求: {overall.get('failed_requests', 0):,}")
            print(f"  错误率: {overall.get('error_rate', 0) * 100:.2f}%")

            duration_stats = overall.get("duration_stats")
            if duration_stats:
                print(f"\n  响应时间统计:")
                print(f"    平均: {duration_stats['avg_ms']:.2f} ms")
                print(f"    最小: {duration_stats['min_ms']:.2f} ms")
                print(f"    最大: {duration_stats['max_ms']:.2f} ms")
                print(f"    P50:  {duration_stats['p50_ms']:.2f} ms")
                print(f"    P95:  {duration_stats['p95_ms']:.2f} ms")
                print(f"    P99:  {duration_stats['p99_ms']:.2f} ms")

        # 按端点统计
        by_endpoint = http_stats.get("by_endpoint", {})
        if by_endpoint:
            print("\n" + "-" * 80)
            print(f"按端点统计 (Top {top_n})")
            print("-" * 80)

            # 按请求数排序
            sorted_endpoints = sorted(
                by_endpoint.items(), key=lambda x: x[1].get("total_requests", 0), reverse=True
            )

            for idx, (endpoint, endpoint_stats) in enumerate(sorted_endpoints[:top_n], 1):
                print(f"\n{idx}. {endpoint}")
                print(f"   总请求数: {endpoint_stats.get('total_requests', 0):,}")
                print(f"   成功请求: {endpoint_stats.get('success_requests', 0):,}")
                print(f"   失败请求: {endpoint_stats.get('failed_requests', 0):,}")
                print(f"   错误率: {endpoint_stats.get('error_rate', 0) * 100:.2f}%")

                duration_stats = endpoint_stats.get("duration_stats")
                if duration_stats:
                    print(f"   响应时间:")
                    print(f"     平均: {duration_stats['avg_ms']:.2f} ms")
                    print(f"     P95:  {duration_stats['p95_ms']:.2f} ms")
                    print(f"     P99:  {duration_stats['p99_ms']:.2f} ms")

                status_codes = endpoint_stats.get("status_codes", {})
                if status_codes:
                    status_str = ", ".join([f"{code}: {count}" for code, count in status_codes.items()])
                    print(f"   状态码分布: {status_str}")

        # 关键指标统计
        metric_stats = stats.get("metric_statistics", {})
        if metric_stats:
            print("\n" + "-" * 80)
            print("关键指标统计")
            print("-" * 80)

            # 显示关键指标
            key_metrics = [
                "http_reqs",
                "http_req_duration",
                "http_req_failed",
                "iterations",
                "vus",
                "data_sent",
                "data_received",
            ]

            for metric_name in key_metrics:
                if metric_name in metric_stats:
                    metric_data = metric_stats[metric_name]
                    print(f"\n{metric_name}:")
                    print(f"  计数: {metric_data['count']:,}")
                    print(f"  平均值: {metric_data['avg']:.2f}")
                    print(f"  最小值: {metric_data['min']:.2f}")
                    print(f"  最大值: {metric_data['max']:.2f}")
                    if "p95" in metric_data:
                        print(f"  P95: {metric_data['p95']:.2f}")
                        print(f"  P99: {metric_data['p99']:.2f}")

        # 阈值检查结果
        print("\n" + "-" * 80)
        print("阈值检查结果")
        print("-" * 80)

        # 检查 HTTP 响应时间阈值
        if "http_req_duration" in metric_stats:
            duration_data = metric_stats["http_req_duration"]
            thresholds = [
                ("P50 < 500ms", duration_data.get("p50", 0) < 500),
                ("P95 < 1500ms", duration_data.get("p95", 0) < 1500),
                ("P99 < 2000ms", duration_data.get("p99", 0) < 2000),
                ("Max < 3000ms", duration_data.get("max", 0) < 3000),
            ]

            for threshold_name, ***REMOVED***ed in thresholds:
                status = "✅ 通过" if ***REMOVED***ed else "❌ 失败"
                print(f"  {threshold_name}: {status}")

        # 检查错误率阈值
        if "http_req_failed" in metric_stats:
            failed_data = metric_stats["http_req_failed"]
            error_rate = failed_data.get("avg", 0)
            ***REMOVED***ed = error_rate < 0.01
            status = "✅ 通过" if ***REMOVED***ed else "❌ 失败"
            print(f"  错误率 < 1%: {status} (实际: {error_rate * 100:.2f}%)")

        print("\n" + "=" * 80)

    def generate_html_report(self, stats: Dict[str, Any], top_n: int = 10) -> str:
        """生成 HTML 格式的专业报告

        Args:
            stats: 统计信息字典
            top_n: 显示 Top N 端点

        Returns:
            HTML 报告内容
        """
        test_duration = stats.get("test_duration", {})
        http_stats = stats.get("http_statistics", {})
        overall = http_stats.get("overall", {})
        by_endpoint = http_stats.get("by_endpoint", {})
        metric_stats = stats.get("metric_statistics", {})

        # 生成状态徽章
        def get_status_badge(***REMOVED***ed: bool) -> str:
            if ***REMOVED***ed:
                return '<span class="badge badge-success">✅ 通过</span>'
            return '<span class="badge badge-danger">❌ 失败</span>'

        # 生成阈值检查结果
        threshold_results = []
        if "http_req_duration" in metric_stats:
            duration_data = metric_stats["http_req_duration"]
            thresholds = [
                ("P50 < 500ms", duration_data.get("p50", 0), 500),
                ("P95 < 1500ms", duration_data.get("p95", 0), 1500),
                ("P99 < 2000ms", duration_data.get("p99", 0), 2000),
                ("Max < 3000ms", duration_data.get("max", 0), 3000),
            ]
            for name, value, threshold in thresholds:
                ***REMOVED***ed = value < threshold
                threshold_results.append({
                    "name": name,
                    "value": value,
                    "threshold": threshold,
                    "***REMOVED***ed": ***REMOVED***ed,
                })

        if "http_req_failed" in metric_stats:
            failed_data = metric_stats["http_req_failed"]
            error_rate = failed_data.get("avg", 0) * 100
            ***REMOVED***ed = error_rate < 1.0
            threshold_results.append({
                "name": "错误率 < 1%",
                "value": error_rate,
                "threshold": 1.0,
                "***REMOVED***ed": ***REMOVED***ed,
            })

        # 生成端点表格行
        endpoint_rows = ""
        if by_endpoint:
            sorted_endpoints = sorted(
                by_endpoint.items(), key=lambda x: x[1].get("total_requests", 0), reverse=True
            )
            for idx, (endpoint, endpoint_stats) in enumerate(sorted_endpoints[:top_n], 1):
                duration_stats = endpoint_stats.get("duration_stats")
                error_rate = endpoint_stats.get("error_rate", 0) * 100
                endpoint_rows += f"""
                <tr>
                    <td>{idx}</td>
                    <td><code>{endpoint}</code></td>
                    <td>{endpoint_stats.get('total_requests', 0):,}</td>
                    <td>{endpoint_stats.get('success_requests', 0):,}</td>
                    <td>{endpoint_stats.get('failed_requests', 0):,}</td>
                    <td><span class="{'text-success' if error_rate < 1 else 'text-danger'}">{error_rate:.2f}%</span></td>
                    <td>{duration_stats['avg_ms']:.2f} ms</td>
                    <td>{duration_stats['p95_ms']:.2f} ms</td>
                    <td>{duration_stats['p99_ms']:.2f} ms</td>
                </tr>
                """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>k6 压测报告分析</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .meta {{
            opacity: 0.9;
            font-size: 0.95em;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }}
        
        .stat-card .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
        }}
        
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        
        .stat-card.success {{
            border-left-color: #28a745;
        }}
        
        .stat-card.danger {{
            border-left-color: #dc3545;
        }}
        
        .stat-card.warning {{
            border-left-color: #ffc107;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .text-success {{
            color: #28a745;
        }}
        
        .text-danger {{
            color: #dc3545;
        }}
        
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        .threshold-list {{
            list-style: none;
            padding: 0;
        }}
        
        .threshold-list li {{
            padding: 10px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 k6 压测报告分析</h1>
            <div class="meta">
                <p>分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>报告文件: {self.json_file.name}</p>
            </div>
        </div>
        
        <div class="content">
            <!-- 测试时长 -->
            <div class="section">
                <h2 class="section-title">⏱️ 测试时长</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">开始时间</div>
                        <div class="value" style="font-size: 1.2em;">{test_duration.get('start_time', 'N/A')[:19] if test_duration.get('start_time') else 'N/A'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">结束时间</div>
                        <div class="value" style="font-size: 1.2em;">{test_duration.get('end_time', 'N/A')[:19] if test_duration.get('end_time') else 'N/A'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">持续时间</div>
                        <div class="value">{test_duration.get('duration_formatted', 'N/A')}</div>
                    </div>
                </div>
            </div>
            
            <!-- HTTP 请求总体统计 -->
            <div class="section">
                <h2 class="section-title">📈 HTTP 请求总体统计</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">总请求数</div>
                        <div class="value">{overall.get('total_requests', 0):,}</div>
                    </div>
                    <div class="stat-card success">
                        <div class="label">成功请求</div>
                        <div class="value">{overall.get('success_requests', 0):,}</div>
                    </div>
                    <div class="stat-card danger">
                        <div class="label">失败请求</div>
                        <div class="value">{overall.get('failed_requests', 0):,}</div>
                    </div>
                    <div class="stat-card {'success' if overall.get('error_rate', 0) < 0.01 else 'danger'}">
                        <div class="label">错误率</div>
                        <div class="value">{overall.get('error_rate', 0) * 100:.2f}%</div>
                    </div>
                </div>
                
                {f'''
                <h3 style="margin-top: 30px; margin-bottom: 15px;">响应时间统计</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">平均响应时间</div>
                        <div class="value">{overall.get('duration_stats', {}).get('avg_ms', 0):.2f} ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">最小响应时间</div>
                        <div class="value">{overall.get('duration_stats', {}).get('min_ms', 0):.2f} ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">最大响应时间</div>
                        <div class="value">{overall.get('duration_stats', {}).get('max_ms', 0):.2f} ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">P50 响应时间</div>
                        <div class="value">{overall.get('duration_stats', {}).get('p50_ms', 0):.2f} ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">P95 响应时间</div>
                        <div class="value">{overall.get('duration_stats', {}).get('p95_ms', 0):.2f} ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">P99 响应时间</div>
                        <div class="value">{overall.get('duration_stats', {}).get('p99_ms', 0):.2f} ms</div>
                    </div>
                </div>
                ''' if overall.get('duration_stats') else ''}
            </div>
            
            <!-- 按端点统计 -->
            {f'''
            <div class="section">
                <h2 class="section-title">🔍 按端点统计 (Top {top_n})</h2>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>端点</th>
                            <th>总请求数</th>
                            <th>成功请求</th>
                            <th>失败请求</th>
                            <th>错误率</th>
                            <th>平均响应时间</th>
                            <th>P95 响应时间</th>
                            <th>P99 响应时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        {endpoint_rows}
                    </tbody>
                </table>
            </div>
            ''' if endpoint_rows else ''}
            
            <!-- 阈值检查结果 -->
            <div class="section">
                <h2 class="section-title">✅ 阈值检查结果</h2>
                <ul class="threshold-list">
                    {''.join([f'''
                    <li>
                        <span>{result['name']}: {result['value']:.2f} {'ms' if 'ms' in result['name'] else '%'}</span>
                        {get_status_badge(result['***REMOVED***ed'])}
                    </li>
                    ''' for result in threshold_results])}
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by k6 Report Analyzer | Intel EC Microservices</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def generate_markdown_report(self, stats: Dict[str, Any], top_n: int = 10) -> str:
        """生成 Markdown 格式的专业报告

        Args:
            stats: 统计信息字典
            top_n: 显示 Top N 端点

        Returns:
            Markdown 报告内容
        """
        test_duration = stats.get("test_duration", {})
        http_stats = stats.get("http_statistics", {})
        overall = http_stats.get("overall", {})
        by_endpoint = http_stats.get("by_endpoint", {})
        metric_stats = stats.get("metric_statistics", {})

        md = f"""# 📊 k6 压测报告分析

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**报告文件**: `{self.json_file.name}`  
**数据点总数**: {stats.get('total_points', 0):,}  
**指标数量**: {stats.get('metrics_count', 0)}

---

## ⏱️ 测试时长

| 项目 | 值 |
|------|-----|
| 开始时间 | {test_duration.get('start_time', 'N/A')[:19] if test_duration.get('start_time') else 'N/A'} |
| 结束时间 | {test_duration.get('end_time', 'N/A')[:19] if test_duration.get('end_time') else 'N/A'} |
| 持续时间 | {test_duration.get('duration_formatted', 'N/A')} |

---

## 📈 HTTP 请求总体统计

### 请求统计

| 指标 | 值 |
|------|-----|
| 总请求数 | {overall.get('total_requests', 0):,} |
| 成功请求 | {overall.get('success_requests', 0):,} |
| 失败请求 | {overall.get('failed_requests', 0):,} |
| 错误率 | {overall.get('error_rate', 0) * 100:.2f}% {'✅' if overall.get('error_rate', 0) < 0.01 else '❌'} |

### 响应时间统计

"""
        if overall.get("duration_stats"):
            duration_stats = overall["duration_stats"]
            md += f"""| 指标 | 值 |
|------|-----|
| 平均响应时间 | {duration_stats.get('avg_ms', 0):.2f} ms |
| 最小响应时间 | {duration_stats.get('min_ms', 0):.2f} ms |
| 最大响应时间 | {duration_stats.get('max_ms', 0):.2f} ms |
| P50 响应时间 | {duration_stats.get('p50_ms', 0):.2f} ms |
| P95 响应时间 | {duration_stats.get('p95_ms', 0):.2f} ms |
| P99 响应时间 | {duration_stats.get('p99_ms', 0):.2f} ms |

"""

        # 按端点统计
        if by_endpoint:
            md += f"""---

## 🔍 按端点统计 (Top {top_n})

| 排名 | 端点 | 总请求数 | 成功请求 | 失败请求 | 错误率 | 平均响应时间 | P95 响应时间 | P99 响应时间 |
|------|------|---------|---------|---------|--------|------------|------------|------------|
"""
            sorted_endpoints = sorted(
                by_endpoint.items(), key=lambda x: x[1].get("total_requests", 0), reverse=True
            )
            for idx, (endpoint, endpoint_stats) in enumerate(sorted_endpoints[:top_n], 1):
                duration_stats = endpoint_stats.get("duration_stats")
                error_rate = endpoint_stats.get("error_rate", 0) * 100
                status_icon = "✅" if error_rate < 1 else "❌"
                if duration_stats:
                    md += f"| {idx} | `{endpoint}` | {endpoint_stats.get('total_requests', 0):,} | {endpoint_stats.get('success_requests', 0):,} | {endpoint_stats.get('failed_requests', 0):,} | {error_rate:.2f}% {status_icon} | {duration_stats['avg_ms']:.2f} ms | {duration_stats['p95_ms']:.2f} ms | {duration_stats['p99_ms']:.2f} ms |\n"
                else:
                    md += f"| {idx} | `{endpoint}` | {endpoint_stats.get('total_requests', 0):,} | {endpoint_stats.get('success_requests', 0):,} | {endpoint_stats.get('failed_requests', 0):,} | {error_rate:.2f}% {status_icon} | N/A | N/A | N/A |\n"

        # 阈值检查结果
        md += """---

## ✅ 阈值检查结果

| 阈值 | 实际值 | 目标值 | 状态 |
|------|--------|--------|------|
"""
        if "http_req_duration" in metric_stats:
            duration_data = metric_stats["http_req_duration"]
            thresholds = [
                ("P50 < 500ms", duration_data.get("p50", 0), 500),
                ("P95 < 1500ms", duration_data.get("p95", 0), 1500),
                ("P99 < 2000ms", duration_data.get("p99", 0), 2000),
                ("Max < 3000ms", duration_data.get("max", 0), 3000),
            ]
            for name, value, threshold in thresholds:
                ***REMOVED***ed = value < threshold
                status = "✅ 通过" if ***REMOVED***ed else "❌ 失败"
                md += f"| {name} | {value:.2f} ms | {threshold} ms | {status} |\n"

        if "http_req_failed" in metric_stats:
            failed_data = metric_stats["http_req_failed"]
            error_rate = failed_data.get("avg", 0) * 100
            ***REMOVED***ed = error_rate < 1.0
            status = "✅ 通过" if ***REMOVED***ed else "❌ 失败"
            md += f"| 错误率 < 1% | {error_rate:.2f}% | 1% | {status} |\n"

        md += """
---

**报告生成工具**: k6 Report Analyzer  
**项目**: Intel EC Microservices
"""
        return md


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="k6 压测报告分析工具")
    parser.add_argument("json_file", help="k6 JSON 报告文件路径")
    parser.add_argument(
        "-n",
        "--top-n",
        type=int,
        default=10,
        help="显示 Top N 端点（默认: 10）",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="输出 JSON 报告文件路径（可选）",
    )
    parser.add_argument(
        "--html",
        help="生成 HTML 格式报告（指定输出文件路径）",
    )
    parser.add_argument(
        "--markdown",
        help="生成 Markdown 格式报告（指定输出文件路径）",
    )

    args = parser.parse_args()

    try:
        analyzer = K6ReportAnalyzer(args.json_file)
        analyzer.parse_json_file()

        # 打印报告
        analyzer.print_report(top_n=args.top_n)

        stats = analyzer.calculate_statistics()

        # 输出 JSON 报告（如果指定）
        if args.output:
            report = {
                "analysis_time": datetime.now().isoformat(),
                "json_file": str(args.json_file),
                "statistics": stats,
            }

            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"\n✅ JSON 报告已保存到: {args.output}")

        # 生成 HTML 报告（如果指定）
        if args.html:
            html_content = analyzer.generate_html_report(stats, top_n=args.top_n)
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"✅ HTML 报告已保存到: {args.html}")

        # 生成 Markdown 报告（如果指定）
        if args.markdown:
            md_content = analyzer.generate_markdown_report(stats, top_n=args.top_n)
            with open(args.markdown, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"✅ Markdown 报告已保存到: {args.markdown}")

    except FileNotFoundError as e:
        logger.error(f"文件不存在: {e!s}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"分析失败: {e!s}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

