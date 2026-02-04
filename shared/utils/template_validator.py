"""
Template Field Validator Utility Class

Provides recursive validation of whether data meets the required field requirements defined by templates.
"""

import os
import sys
from typing import Any, Dict

# Use try-except to handle path imports
try:
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from shared.common.exceptions import BusinessError
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class TemplateValidator:
    """Template Field Validator

    Used to validate whether data meets the required field requirements defined by templates,
    supporting recursive validation of nested structures.
    """

    def __init__(self, required_marker: str = "required"):
        """Initialize the validator

        Args:
            required_marker: Required field marker (defaults to "required")
        """
        self.required_marker = required_marker

    def validate_required_fields(self, data: Dict[str, Any], template: Dict[str, Any]) -> None:
        """Validate required fields in the data

        Traverse the template to check if fields with required_marker values exist in the data.

        Args:
            data: Data to be validated
            template: Template definition

        Raises:
            BusinessError: Thrown when required fields are missing

        Example:
            >>> validator = TemplateValidator()
            >>> template = {
            ...     "name": "required",
            ...     "email": "required",
            ...     "age": "optional"
            ... }
            >>> data = {"name": "John", "age": 30}
            >>> validator.validate_required_fields(data, template)
            # Throws BusinessError: Missing required field: email
        """

        def check_required(data_item: Any, template_item: Any, path: str = "") -> None:
            """Recursively check required fields

            Args:
                data_item: Current data item
                template_item: Current template item
                path: Current field path (used for error messages)
            """
            if isinstance(template_item, dict):
                for key, value in template_item.items():
                    current_path = f"{path}.{key}" if path else key

                    # If template value is required marker, check if it exists in data
                    if value == self.required_marker:
                        if not isinstance(data_item, dict) or key not in data_item:
                            raise BusinessError(
                                message=f"Missing required field: {current_path}",
                                error_code="MISSING_REQUIRED_FIELD",
                                code=400,
                                details={"field": current_path},
                            )

                    # If template value is a dictionary, recursively check
                    elif isinstance(value, dict):
                        if isinstance(data_item, dict) and key in data_item:
                            check_required(data_item[key], value, current_path)

                    # If template value is a list, check list items in data
                    elif isinstance(value, list) and value:
                        if isinstance(data_item, dict) and key in data_item:
                            if isinstance(data_item[key], list):
                                for idx, item in enumerate(data_item[key]):
                                    check_required(item, value[0], f"{current_path}[{idx}]")

        try:
            check_required(data, template)
            logger.info("Template field validation passed")
        except BusinessError:
            raise
        except Exception as e:
            logger.error(f"Template field validation exception: {e!s}", exc_info=True)
            raise BusinessError(
                message="Template field validation failed",
                error_code="VALIDATION_FAILED",
                code=500,
            )
