"""测试用例相关 Schema 定义"""

from typing import Optional

from pydantic import BaseModel, Field


class TestCaseReportRequest(BaseModel):
    """测试用例执行结果上报请求"""

    tc_id: str = Field(..., description="测试用例ID", min_length=1, max_length=64)
    state: int = Field(..., description="执行状态;0-空闲 1-启动 2-成功 3-失败", ge=0, le=3)
    result_msg: Optional[str] = Field(None, description="结果消息", max_length=255)
    log_url: Optional[str] = Field(None, description="日志文件URL", max_length=512)

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
    """测试用例执行结果上报响应"""

    host_id: str = Field(..., description="主机ID")
    tc_id: str = Field(..., description="测试用例ID")
    case_state: int = Field(..., description="case执行状态;0-空闲 1-启动 2-成功 3-失败")
    result_msg: Optional[str] = Field(None, description="结果消息")
    log_url: Optional[str] = Field(None, description="日志文件URL")
    updated: bool = Field(..., description="是否成功更新")

    model_config = {
        "from_attributes": True,
    }


class TestCaseReportSuccessResponse(BaseModel):
    """测试用例执行结果上报成功响应包装模型

    用于 FastAPI 文档展示，明确指定 data 字段的类型
    """

    code: int = Field(default=200, description="响应码")
    message: str = Field(default="测试用例结果上报成功", description="响应消息")
    data: TestCaseReportResponse = Field(description="测试用例上报结果数据")
    timestamp: str = Field(description="响应时间戳")

    model_config = {"from_attributes": True}
