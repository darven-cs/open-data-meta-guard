"""
统一响应模型。

v2.0 调整：原样搬自 v1.0。
"""
from pydantic import BaseModel, Field
from typing import Any, Optional


class ResponseModel(BaseModel):
    code: int = Field(default=200, description="状态码")
    data: Optional[Any] = Field(default=None, description="数据")
    msg: str = Field(default="success", description="消息描述")

    @staticmethod
    def success(data: Any = None, msg: str = "操作成功") -> "ResponseModel":
        return ResponseModel(code=200, msg=msg, data=data)

    @staticmethod
    def fail(code: int = 500, msg: str = "系统忙碌中...") -> "ResponseModel":
        return ResponseModel(code=code, msg=msg)
