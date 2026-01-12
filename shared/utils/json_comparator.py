"""
JSON Deep Comparison Utility Class

Provides deep comparison functionality for JSON data structures,
used to detect configuration changes, data differences, and other scenarios.
"""

from typing import Any, Dict, List


class JSONComparator:
    """JSON Deep Comparison Utility Class

    Supports comparison of arbitrarily complex JSON data structures (dictionaries, lists, nested structures),
    and returns detailed difference information, including added, removed, modified types.

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

    # Difference type constants
    DIFF_TYPE_ADDED = "added"
    DIFF_TYPE_REMOVED = "removed"
    DIFF_TYPE_MODIFIED = "modified"

    def compare(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any],
        path: str = "",
    ) -> Dict[str, Any]:
        """Compare two JSON objects

        Args:
            previous: Historical data
            current: Current data
            path: Current path prefix (used to record difference location)

        Returns:
            Difference dictionary, formatted as {
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
        """Deep comparison of dictionary data

        Recursively compares two dictionary objects, finding all difference fields

        Args:
            previous: Historical dictionary
            current: Current dictionary
            path: Current path (used to record difference location)

        Returns:
            Difference dictionary
        """
        diff = {}

        # Get all keys (including keys from both previous and current)
        all_keys = set(previous.keys()) | set(current.keys())

        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            # Added field
            if key not in previous:
                diff[current_path] = {
                    "type": self.DIFF_TYPE_ADDED,
                    "previous": None,
                    "current": current[key],
                }
                continue

            # Removed field
            if key not in current:
                diff[current_path] = {
                    "type": self.DIFF_TYPE_REMOVED,
                    "previous": previous[key],
                    "current": None,
                }
                continue

            prev_value = previous[key]
            curr_value = current[key]

            # Recursively compare dictionaries
            if isinstance(prev_value, dict) and isinstance(curr_value, dict):
                nested_diff = self._deep_compare_dict(prev_value, curr_value, current_path)
                diff.update(nested_diff)

            # Recursively compare lists
            elif isinstance(prev_value, list) and isinstance(curr_value, list):
                list_diff = self._compare_list(prev_value, curr_value, current_path)
                diff.update(list_diff)

            # Value type differs or values are different
            elif type(curr_value) is not type(prev_value) or prev_value != curr_value:
                diff[current_path] = {
                    "type": self.DIFF_TYPE_MODIFIED,
                    "previous": prev_value,
                    "current": curr_value,
                }

        return diff

    def _compare_list(self, previous: List[Any], current: List[Any], path: str) -> Dict[str, Any]:
        """Compare list data

        Compare two lists item by item, detecting added, removed, and modified items

        Args:
            previous: Historical list
            current: Current list
            path: Current path

        Returns:
            Difference dictionary
        """
        diff = {}

        # List length change
        if len(previous) != len(current):
            diff[f"{path}.length"] = {
                "type": self.DIFF_TYPE_MODIFIED,
                "previous": len(previous),
                "current": len(current),
            }

        # Compare list items
        max_len = max(len(previous), len(current))
        for idx in range(max_len):
            if idx >= len(previous):
                # Added item
                diff[f"{path}[{idx}]"] = {
                    "type": self.DIFF_TYPE_ADDED,
                    "previous": None,
                    "current": current[idx],
                }
            elif idx >= len(current):
                # Removed item
                diff[f"{path}[{idx}]"] = {
                    "type": self.DIFF_TYPE_REMOVED,
                    "previous": previous[idx],
                    "current": None,
                }
            else:
                # Compare item content
                prev_item = previous[idx]
                curr_item = current[idx]

                if isinstance(prev_item, dict) and isinstance(curr_item, dict):
                    # Recursively compare dictionary items
                    item_diff = self._deep_compare_dict(prev_item, curr_item, f"{path}[{idx}]")
                    diff.update(item_diff)
                elif prev_item != curr_item:
                    # Values are different
                    diff[f"{path}[{idx}]"] = {
                        "type": self.DIFF_TYPE_MODIFIED,
                        "previous": prev_item,
                        "current": curr_item,
                    }

        return diff

    def has_changes(self, diff: Dict[str, Any]) -> bool:
        """Check if there are differences

        Args:
            diff: Difference dictionary returned by compare() method

        Returns:
            True if there are differences, otherwise False

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
        """Get all added fields

        Args:
            diff: Difference dictionary returned by compare() method

        Returns:
            List of added field paths

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1}, {"a": 1, "b": 2})
            >>> comparator.get_added_fields(diff)
            ['b']
        """
        return [path for path, change in diff.items() if change["type"] == self.DIFF_TYPE_ADDED]

    def get_removed_fields(self, diff: Dict[str, Any]) -> List[str]:
        """Get all removed fields

        Args:
            diff: Difference dictionary returned by compare() method

        Returns:
            List of removed field paths

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1, "b": 2}, {"a": 1})
            >>> comparator.get_removed_fields(diff)
            ['b']
        """
        return [path for path, change in diff.items() if change["type"] == self.DIFF_TYPE_REMOVED]

    def get_modified_fields(self, diff: Dict[str, Any]) -> List[str]:
        """Get all modified fields

        Args:
            diff: Difference dictionary returned by compare() method

        Returns:
            List of modified field paths

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1}, {"a": 2})
            >>> comparator.get_modified_fields(diff)
            ['a']
        """
        return [path for path, change in diff.items() if change["type"] == self.DIFF_TYPE_MODIFIED]

    def format_diff_summary(self, diff: Dict[str, Any]) -> str:
        """Format difference summary

        Generate human-readable difference summary information

        Args:
            diff: Difference dictionary returned by compare() method

        Returns:
            Formatted difference summary string

        Example:
            >>> comparator = JSONComparator()
            >>> diff = comparator.compare({"a": 1}, {"a": 2, "b": 3})
            >>> print(comparator.format_diff_summary(diff))
            Difference Summary:
            - Added fields: 1
            - Removed fields: 0
            - Modified fields: 1
            - Total: 2 differences
        """
        added = self.get_added_fields(diff)
        removed = self.get_removed_fields(diff)
        modified = self.get_modified_fields(diff)

        summary_lines = [
            "Difference Summary:",
            f"- Added fields: {len(added)}",
            f"- Removed fields: {len(removed)}",
            f"- Modified fields: {len(modified)}",
            f"- Total: {len(diff)} differences",
        ]

        return "\n".join(summary_lines)
