from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.platform_api.core.clock import iso_now
from apps.platform_api.core.errors import BizError
from apps.platform_api.core.trace import agent_run_id_of, trace_id_of
from domain.rules.types import RuleInputError
from sdk.contracts.envelope import Envelope
from sdk.contracts.error_codes import ErrorCode, message_of, retryable_of
from sdk.observability import redact


def _envelope_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
    data: Any = None,
    biz_id: str | None = None,
) -> JSONResponse:
    clock = request.app.state.clock
    current_trace = trace_id_of(request)
    envelope = Envelope[Any](
        code=code,
        message=message,
        traceId=current_trace,
        agentRunId=agent_run_id_of(request),
        bizId=biz_id,
        data=redact(data),
        timestamp=iso_now(clock),
        retryable=retryable,
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
        headers={"X-Trace-Id": current_trace},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def _biz_error(request: Request, exc: BizError) -> JSONResponse:
        return _envelope_response(
            request,
            exc.http_status,
            exc.code.value,
            exc.message,
            exc.retryable,
        )

    @app.exception_handler(RuleInputError)
    async def _rule_input_error(request: Request, exc: RuleInputError) -> JSONResponse:
        code = ErrorCode.RULE_INVALID_INPUT
        return _envelope_response(
            request,
            400,
            code.value,
            str(exc),
            retryable_of(code),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        code = ErrorCode.CONTRACT_VALIDATION_FAILED
        return _envelope_response(
            request,
            422,
            code.value,
            "请求参数校验失败，请检查字段格式与必填项。",
            retryable_of(code),
            data={"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ErrorCode.CONTRACT_VALIDATION_FAILED
        message = "接口不存在。" if exc.status_code == 404 else message_of(code)
        return _envelope_response(
            request,
            exc.status_code,
            code.value,
            message,
            retryable_of(code),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        code = ErrorCode.SYSTEM_UNAVAILABLE
        return _envelope_response(
            request,
            500,
            code.value,
            message_of(code),
            retryable_of(code),
        )