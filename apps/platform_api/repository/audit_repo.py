from __future__ import annotations

import json
import secrets
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from apps.platform_api.core.clock import Clock, iso_now
from sdk.observability import redact


@dataclass(frozen=True)
class AuditEvent:
    auditId: str
    eventType: str
    operator: str
    occurredAt: str
    bizId: str | None
    beforeValue: Any
    afterValue: Any
    result: str
    traceId: str | None
    agentRunId: str | None


class AuditRepo:
    def __init__(self, audit_dir: str | Path, clock: Clock) -> None:
        self._dir = Path(audit_dir)
        self._clock = clock
        self._lock = threading.Lock()

    @property
    def directory(self) -> Path:
        return self._dir

    def append(
        self,
        event_type: str,
        operator: str,
        biz_id: str | None = None,
        before: Any = None,
        after: Any = None,
        result: str = "success",
        trace_id: str | None = None,
        agent_run_id: str | None = None,
    ) -> str:
        occurred_at = iso_now(self._clock)
        audit_id = f"AUD-{secrets.token_hex(6)}"
        event = AuditEvent(
            auditId=audit_id,
            eventType=event_type,
            operator=operator,
            occurredAt=occurred_at,
            bizId=biz_id,
            beforeValue=before,
            afterValue=after,
            result=result,
            traceId=trace_id,
            agentRunId=agent_run_id,
        )
        line = json.dumps(redact(asdict(event)), ensure_ascii=False, sort_keys=True)
        day = occurred_at[:10]
        path = self._dir / f"{day}.jsonl"
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
        return audit_id

    def query_by_biz_id(self, biz_id: str) -> list[dict[str, Any]]:
        if not self._dir.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self._dir.glob("*.jsonl")):
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                record = json.loads(raw)
                if record.get("bizId") == biz_id:
                    rows.append(record)
        return rows

    def all_events(self) -> list[dict[str, Any]]:
        if not self._dir.exists():
            return []
        rows = []
        for path in sorted(self._dir.glob("*.jsonl")):
            for raw in path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    rows.append(json.loads(raw))
        return rows