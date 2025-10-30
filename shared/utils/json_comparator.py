"""
JSON深度对比工具类

提供JSON数据结构的深度对比功能，用于检测配置变更、数据差异等场景。
"""

from typing import Any, Dict, List


class JSONComparator:
    """JSON深度对比工具类

    支持对比任意复杂的JSON数据结构（字典、列表、嵌套结构），
    并返回详细的差异信息，包括新增、删除、修改等类型。

    Example:
        >>> comparator = JSONComparator()
        >>> previous = {"name": "John", "age": 30, "tags": ["admin"]}
        >>> current = {"name": "John", "age": 31, "tags": ["admin", "user"]}
        >>> diff = comparator.compare(previous, current)
        >>> print(diff)
        {
            "age": {"type": "modified", "previous": 30, "current": 31},
            "tags.length": {"type": "modified", "previous": 1, "current": 2},
            "tags[1]": {"type": "added", "previous": None, "current": "user"}
        }
    """

    # 差异类型常量
    DIFF_TYPE_ADDED = "added"
    DIFF_TYPE_REMOVED = "removed"
    DIFF_TYPE_MODIFIED = "modified"

    def compare(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any],
        path: str = "",
    ) -> Dict[str, Any]:
        """对比两个JSON对象

        Args:
            previous: 历史数据
            current: 当前数据
            path: 当前路径前缀（用于记录差异位置）

        Returns:
            差异字典，格式为 {
                "path.to.field": {
                    "type": "added" | "removed" | "modified",
                    "previous": previous_value,
                    "current": current_value
                }
            }

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare(
            ...     {"user": {"name": "John", "age": 30}},
            ...     {"user": {"name": "Jane", "age": 30}}
            ... )
            >>> diff
            {'user.name': {'type': 'modified', 'previous': 'John', 'current': 'Jane'}}
        """
        return self._deep_compare_dict(previous, current, path)

    def _deep_compare_dict(self, previous: Dict[str, Any], current: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """深度对比字典数据

        递归对比两个字典对象，找出所有差异字段

        Args:
            previous: 历史字典
            current: 当前字典
            path: 当前路径（用于记录差异位置）

        Returns:
            差异字典
        """
        diff = {}

        # 获取所有键（包括previous和current的键）
        all_keys = set(previous.keys()) | set(current.keys())

        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            # 新增字段
            if key not in previous:
                diff[current_path] = {
                    "type": self.DIFF_TYPE_ADDED,
                    "previous": None,
                    "current": current[key],
                }
                continue

            # 删除字段
            if key not in current:
                diff[current_path] = {
                    "type": self.DIFF_TYPE_REMOVED,
                    "previous": previous[key],
                    "current": None,
                }
                continue

            prev_value = previous[key]
            curr_value = current[key]

            # 递归对比字典
            if isinstance(prev_value, dict) and isinstance(curr_value, dict):
                nested_diff = self._deep_compare_dict(prev_value, curr_value, current_path)
                diff.update(nested_diff)

            # 递归对比列表
            elif isinstance(prev_value, list) and isinstance(curr_value, list):
                list_diff = self._compare_list(prev_value, curr_value, current_path)
                diff.update(list_diff)

            # 值类型不同或值不同
            elif type(curr_value) is not type(prev_value) or prev_value != curr_value:
                diff[current_path] = {
                    "type": self.DIFF_TYPE_MODIFIED,
                    "previous": prev_value,
                    "current": curr_value,
                }

        return diff

    def _compare_list(self, previous: List[Any], current: List[Any], path: str) -> Dict[str, Any]:
        """对比列表数据

        逐项对比两个列表，检测新增、删除、修改的项

        Args:
            previous: 历史列表
            current: 当前列表
            path: 当前路径

        Returns:
            差异字典
        """
        diff = {}

        # 列表长度变化
        if len(previous) != len(current):
            diff[f"{path}.length"] = {
                "type": self.DIFF_TYPE_MODIFIED,
                "previous": len(previous),
                "current": len(current),
            }

        # 对比列表项
        max_len = max(len(previous), len(current))
        for idx in range(max_len):
            if idx >= len(previous):
                # 新增项
                diff[f"{path}[{idx}]"] = {
                    "type": self.DIFF_TYPE_ADDED,
                    "previous": None,
                    "current": current[idx],
                }
            elif idx >= len(current):
                # 删除项
                diff[f"{path}[{idx}]"] = {
                    "type": self.DIFF_TYPE_REMOVED,
                    "previous": previous[idx],
                    "current": None,
                }
            else:
                # 对比项内容
                prev_item = previous[idx]
                curr_item = current[idx]

                if isinstance(prev_item, dict) and isinstance(curr_item, dict):
                    # 递归对比字典项
                    item_diff = self._deep_compare_dict(prev_item, curr_item, f"{path}[{idx}]")
                    diff.update(item_diff)
                elif prev_item != curr_item:
                    # 值不同
                    diff[f"{path}[{idx}]"] = {
                        "type": self.DIFF_TYPE_MODIFIED,
                        "previous": prev_item,
                        "current": curr_item,
                    }

        return diff

    def has_changes(self, diff: Dict[str, Any]) -> bool:
        """检查是否存在差异

        Args:
            diff: compare() 方法返回的差异字典

        Returns:
            True 如果存在差异，否则 False

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1}, {"a": 1})
            >>> comparator.has_changes(diff)
            False
            >>> diff = comparator.compare({"a": 1}, {"a": 2})
            >>> comparator.has_changes(diff)
            True
        """
        return len(diff) > 0

    def get_added_fields(self, diff: Dict[str, Any]) -> List[str]:
        """获取所有新增字段

        Args:
            diff: compare() 方法返回的差异字典

        Returns:
            新增字段路径列表

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1}, {"a": 1, "b": 2})
            >>> comparator.get_added_fields(diff)
            ['b']
        """
        return [path for path, change in diff.items() if change["type"] == self.DIFF_TYPE_ADDED]

    def get_removed_fields(self, diff: Dict[str, Any]) -> List[str]:
        """获取所有删除字段

        Args:
            diff: compare() 方法返回的差异字典

        Returns:
            删除字段路径列表

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1, "b": 2}, {"a": 1})
            >>> comparator.get_removed_fields(diff)
            ['b']
        """
        return [path for path, change in diff.items() if change["type"] == self.DIFF_TYPE_REMOVED]

    def get_modified_fields(self, diff: Dict[str, Any]) -> List[str]:
        """获取所有修改字段

        Args:
            diff: compare() 方法返回的差异字典

        Returns:
            修改字段路径列表

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1}, {"a": 2})
            >>> comparator.get_modified_fields(diff)
            ['a']
        """
        return [path for path, change in diff.items() if change["type"] == self.DIFF_TYPE_MODIFIED]

    def format_diff_summary(self, diff: Dict[str, Any]) -> str:
        """格式化差异摘要

        生成易读的差异摘要信息

        Args:
            diff: compare() 方法返回的差异字典

        Returns:
            格式化的差异摘要字符串

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1}, {"a": 2, "b": 3})
            >>> print(comparator.format_diff_summary(diff))
            差异摘要:
            - 新增字段: 1 个
            - 删除字段: 0 个
            - 修改字段: 1 个
            - 总计: 2 处差异
        """
        added = self.get_added_fields(diff)
        removed = self.get_removed_fields(diff)
        modified = self.get_modified_fields(diff)

        summary_lines = [
            "差异摘要:",
            f"- 新增字段: {len(added)} 个",
            f"- 删除字段: {len(removed)} 个",
            f"- 修改字段: {len(modified)} 个",
            f"- 总计: {len(diff)} 处差异",
        ]

        return "\n".join(summary_lines)
