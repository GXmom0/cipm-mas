from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from sdk.settings import CipmSettings


class LlmClientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class LlmOutputFormatError(LlmClientError):
    pass


@dataclass(frozen=True)
class LlmMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LlmResponse:
    content: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class LlmClient(Protocol):
    def chat(self, messages: list[LlmMessage], temperature: float | None = None) -> LlmResponse: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        temperature: float = 0.2,
        extra_headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.temperature = temperature
        self.extra_headers = extra_headers or {}
        self._transport = transport

    @property
    def chat_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        return headers

    def _payload(self, messages: list[LlmMessage], temperature: float | None) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "temperature": self.temperature if temperature is None else temperature,
            "stream": False,
        }

    def chat(self, messages: list[LlmMessage], temperature: float | None = None) -> LlmResponse:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds, transport=self._transport) as client:
                    response = client.post(
                        self.chat_url,
                        headers=self._headers(),
                        json=self._payload(messages, temperature),
                    )
                if response.status_code >= 500:
                    raise LlmClientError(
                        f"LLM 服务端错误：HTTP {response.status_code}",
                        status_code=response.status_code,
                    )
                if response.status_code >= 400:
                    raise LlmClientError(
                        f"LLM 请求失败：HTTP {response.status_code}",
                        status_code=response.status_code,
                    )
                return self._parse_response(response.json())
            except (httpx.HTTPError, LlmClientError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(0.5 * (2**attempt), 2.0))
        raise LlmClientError(f"LLM 调用失败：{last_error}") from last_error

    def _parse_response(self, payload: dict[str, Any]) -> LlmResponse:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmOutputFormatError("LLM 响应缺少 choices[0].message.content") from exc
        return LlmResponse(
            content=content,
            model=str(payload.get("model", self.model)),
            usage=payload.get("usage") or {},
            raw=payload,
        )


class PanguClient(OpenAICompatibleClient):
    """华为云盘古/ModelArts 推理服务客户端（OpenAI 兼容路径）。"""


class MockLlmClient:
    def __init__(self, content: str | dict[str, Any], model: str = "mock-llm") -> None:
        self._content = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        self.model = model

    def chat(self, messages: list[LlmMessage], temperature: float | None = None) -> LlmResponse:
        return LlmResponse(content=self._content, model=self.model, usage={}, raw={})


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise LlmOutputFormatError("LLM 输出中未找到 JSON 对象")
    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LlmOutputFormatError(f"LLM 输出 JSON 解析失败：{exc}") from exc
    if not isinstance(payload, dict):
        raise LlmOutputFormatError("LLM 输出 JSON 顶层必须为对象")
    return payload


def build_llm_client(settings: CipmSettings) -> LlmClient:
    if not settings.llm_endpoint or not settings.llm_model:
        raise LlmClientError("运行时模式缺少 CIPM_LLM_ENDPOINT 或 CIPM_LLM_MODEL")
    return OpenAICompatibleClient(
        base_url=settings.llm_endpoint,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
        extra_headers={"X-Cipm-Runtime": settings.runtime},
    )