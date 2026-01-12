"""Test case related Schema definitions"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TestCaseReportRequest(BaseModel):
    """Test case execution result report request"""

    tc_id: str = Field(..., description="Test case ID", min_length=1, max_length=64)
    state: int = Field(..., description="Execution state;0-free 1-started 2-success 3-failed", ge=0, le=3)
    result_msg: Optional[str] = Field(None, description="Result message", max_length=255)
    log_url: Optional[str] = Field(None, description="Log file URL", max_length=512)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "tc_id": "absdf1234",
                "state": 2,
                "result_msg": '{"code":"200","msg":"ok"}',
                "log_url": "https://www.aaa.com/xxxx.log",
            }
        },
    }


class TestCaseReportResponse(BaseModel):
    """Test case execution result report response"""

    host_id: str = Field(..., description="Host ID")
    tc_id: str = Field(..., description="Test case ID")
    case_state: int = Field(..., description="Case execution state;0-free 1-started 2-success 3-failed")
    result_msg: Optional[str] = Field(None, description="Result message")
    log_url: Optional[str] = Field(None, description="Log file URL")
    updated: bool = Field(..., description="Whether update succeeded")

    model_config = {
        "from_attributes": True,
    }


class TestCaseDueTimeRequest(BaseModel):
    """Test case expected end time report request"""

    tc_id: str = Field(..., description="Test case ID", min_length=1, max_length=64)
    due_time: int = Field(..., description="Expected end time (minutes difference, integer)", ge=0)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "tc_id": "absdf1234",
                "due_time": 60,
            }
        },
    }


class TestCaseDueTimeResponse(BaseModel):
    """Test case expected end time report response"""

    host_id: str = Field(..., description="Host ID")
    tc_id: str = Field(..., description="Test case ID")
    due_time: datetime = Field(..., description="Expected end time")
    updated: bool = Field(..., description="Whether update succeeded")

    model_config = {
        "from_attributes": True,
    }
