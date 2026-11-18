from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pytest


@contextmanager
def open_test_client(app) -> Iterator[object]:
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    try:
        client.__enter__()
    except OSError as exc:
        pytest.skip(f"当前执行环境限制本地套接字，跳过 ASGI 用例：{exc}")
    try:
        yield client
    finally:
        try:
            client.__exit__(None, None, None)
        except Exception:
            pass