from __future__ import annotations

from typing import Any

from sdk.contracts.error_codes import ErrorCode, message_of, retryable_of


class BizError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool | None = None,
        http_status: int = 400,
    ) -> None:
        self.code = code
        self.message = message or message_of(code)
        self.details = details or {}
        self.retryable = retryable_of(code) if retryable is None else retryable
        self.http_status = http_status
        super().__init__(self.message)