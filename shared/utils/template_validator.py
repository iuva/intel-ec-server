"""
<<<<<<< HEAD
Template Field Validator Utility Class

Provides recursive validation of whether data meets the required field requirements defined by templates.
=======
模板字段验证器工具类

提供递归验证数据是否符合模板定义的必填字段要求。
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
"""

import os
import sys
from typing import Any, Dict

<<<<<<< HEAD
# Use try-except to handle path imports
=======
# 使用 try-except 方式处理路径导入
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
try:
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class TemplateValidator:
<<<<<<< HEAD
    """Template Field Validator

    Used to validate whether data meets the required field requirements defined by templates,
    supporting recursive validation of nested structures.
    """

    def __init__(self, required_marker: str = "required"):
        """Initialize the validator

        Args:
            required_marker: Required field marker (defaults to "required")
=======
    """模板字段验证器

    用于验证数据是否符合模板定义的必填字段要求，支持递归验证嵌套结构。
    """

    def __init__(self, required_marker: str = "required"):
        """初始化验证器

        Args:
            required_marker: 必填字段标记（默认为 "required"）
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
        """
        self.required_marker = required_marker

    def validate_required_fields(self, data: Dict[str, Any], template: Dict[str, Any]) -> None:
<<<<<<< HEAD
        """Validate required fields in the data

        Traverse the template to check if fields with required_marker values exist in the data.

        Args:
            data: Data to be validated
            template: Template definition

        Raises:
            BusinessError: Thrown when required fields are missing
=======
        """验证数据中的必填字段

        遍历模板，检查值为 required_marker 的字段是否在数据中存在。

        Args:
            data: 待验证的数据
            template: 模板定义

        Raises:
            BusinessError: 缺少必填字段时抛出
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)

        Example:
            >>> validator = TemplateValidator()
            >>> template = {
            ...     "name": "required",
            ...     "email": "required",
            ...     "age": "optional"
            ... }
            >>> data = {"name": "John", "age": 30}
            >>> validator.validate_required_fields(data, template)
<<<<<<< HEAD
            # Throws BusinessError: Missing required field: email
        """

        def check_required(data_item: Any, template_item: Any, path: str = "") -> None:
            """Recursively check required fields

            Args:
                data_item: Current data item
                template_item: Current template item
                path: Current field path (used for error messages)
=======
            # 抛出 BusinessError: 缺少必填字段: email
        """

        def check_required(data_item: Any, template_item: Any, path: str = "") -> None:
            """递归检查必填字段

            Args:
                data_item: 当前数据项
                template_item: 当前模板项
                path: 当前字段路径（用于错误提示）
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
            """
            if isinstance(template_item, dict):
                for key, value in template_item.items():
                    current_path = f"{path}.{key}" if path else key

<<<<<<< HEAD
                    # If template value is required marker, check if it exists in data
                    if value == self.required_marker:
                        if not isinstance(data_item, dict) or key not in data_item:
                            raise BusinessError(
                                message=f"Missing required field: {current_path}",
=======
                    # 如果模板值为必填标记，检查数据中是否存在
                    if value == self.required_marker:
                        if not isinstance(data_item, dict) or key not in data_item:
                            raise BusinessError(
                                message=f"缺少必填字段: {current_path}",
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
                                error_code="MISSING_REQUIRED_FIELD",
                                code=400,
                                details={"field": current_path},
                            )

<<<<<<< HEAD
                    # If template value is a dictionary, recursively check
=======
                    # 如果模板值是字典，递归检查
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
                    elif isinstance(value, dict):
                        if isinstance(data_item, dict) and key in data_item:
                            check_required(data_item[key], value, current_path)

<<<<<<< HEAD
                    # If template value is a list, check list items in data
=======
                    # 如果模板值是列表，检查数据中的列表项
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
                    elif isinstance(value, list) and value:
                        if isinstance(data_item, dict) and key in data_item:
                            if isinstance(data_item[key], list):
                                for idx, item in enumerate(data_item[key]):
                                    check_required(item, value[0], f"{current_path}[{idx}]")

        try:
            check_required(data, template)
<<<<<<< HEAD
            logger.info("Template field validation ***REMOVED***ed")
        except BusinessError:
            raise
        except Exception as e:
            logger.error(f"Template field validation exception: {e!s}", exc_info=True)
            raise BusinessError(
                message="Template field validation failed",
=======
            logger.info("模板字段验证通过")
        except BusinessError:
            raise
        except Exception as e:
            logger.error(f"模板字段验证异常: {str(e)}", exc_info=True)
            raise BusinessError(
                message="模板字段验证失败",
>>>>>>> 0897239 (feat(host): 添加 Agent 硬件信息上报功能，添加 Agent Case 执行结果上报)
                error_code="VALIDATION_FAILED",
                code=500,
            )
