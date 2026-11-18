from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field, field_validator

from sdk.contracts.common import FrozenModel

T = TypeVar("T")


class Envelope(FrozenModel, Generic[T]):
    code: str = Field(default="OK", description="业务码，成功为 OK，失败为 CIPM-<DOMAIN>-<NNNN>")
    message: str = Field(default="成功", description="面向用户的中文提示")
    traceId: str = Field(pattern=r"^[0-9a-f]{32}$", description="32 位小写十六进制链路号")
    agentRunId: str | None = Field(default=None, description="AgentArts 单次运行标识")
    bizId: str | None = Field(default=None, description="业务主键，如作业单号")
    data: T | None = Field(default=None, description="业务载荷")
    timestamp: str = Field(description="ISO8601 时间，必须带 +08:00")
    retryable: bool = Field(default=False, description="是否可重试，由错误码表决定")

    @field_validator("timestamp")
    @classmethod
    def _require_east8(cls, value: str) -> str:
        if not value.endswith("+08:00"):
            raise ValueError("timestamp 必须使用 +08:00 时区")
        return value

    @classmethod
    def ok(cls, data: T, trace_id: str, timestamp: str, **kwargs: object) -> "Envelope[T]":
        return cls(data=data, traceId=trace_id, timestamp=timestamp, **kwargs)  # type: ignore[arg-type]