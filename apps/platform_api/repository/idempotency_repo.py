from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from apps.platform_api.core.clock import Clock, iso_now

STATUS_PENDING = "pending"
STATUS_ACKED = "acked"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"

CANCEL_CANCELLED = "cancelled"
CANCEL_ALREADY_CANCELLED = "already_cancelled"
CANCEL_ALREADY_ACKED = "already_acked"
CANCEL_NOT_CANCELLABLE = "not_cancellable"
CANCEL_NOT_FOUND = "not_found"
CANCEL_AMBIGUOUS = "ambiguous"


@dataclass
class IdempotencyRecord:
    key: str
    status: str
    payload: dict[str, Any]
    workOrderNo: str | None
    reason: str | None
    result: dict[str, Any] | None
    createdAt: str
    updatedAt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "status": self.status,
            "payload": self.payload,
            "workOrderNo": self.workOrderNo,
            "reason": self.reason,
            "result": self.result,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "IdempotencyRecord":
        return cls(
            key=raw["key"],
            status=raw["status"],
            payload=raw.get("payload") or {},
            workOrderNo=raw.get("workOrderNo"),
            reason=raw.get("reason"),
            result=raw.get("result"),
            createdAt=raw["createdAt"],
            updatedAt=raw["updatedAt"],
        )


@dataclass(frozen=True)
class ClaimResult:
    claimed: bool
    record: IdempotencyRecord
    expired: bool = False


@dataclass(frozen=True)
class CancelOutcome:
    outcome: str
    record: IdempotencyRecord | None
    previous_status: str | None = None


class IdempotencyRepo:
    """进程内 + JSON 文件持久化的幂等仓库（按 key 保留历史轮次，供审计）。

    状态机固定：pending → acked | failed | cancelled | expired，终态不回退。
    同一 key 的新一轮 claim 会追加一条新记录，旧记录（失败/取消/过期）原样保留。
    对外接口与存储解耦，可平滑替换为 PostgreSQL。
    """

    def __init__(self, path: str | Path, clock: Clock, ttl_seconds: int = 600) -> None:
        self._path = Path(path)
        self._clock = clock
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._records: dict[str, list[IdempotencyRecord]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(raw, dict):
            return
        for key, value in raw.items():
            if isinstance(value, list):
                records = [IdempotencyRecord.from_dict(item) for item in value if isinstance(item, dict)]
            elif isinstance(value, dict):
                records = [IdempotencyRecord.from_dict(value)]
            else:
                records = []
            if records:
                self._records[key] = records

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: [record.to_dict() for record in records] for key, records in self._records.items()}
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self._path)

    def _expired(self, record: IdempotencyRecord) -> bool:
        try:
            created = datetime.fromisoformat(record.createdAt)
        except ValueError:
            return False
        return (self._clock.now() - created).total_seconds() >= self._ttl

    def _active(self, key: str) -> IdempotencyRecord | None:
        records = self._records.get(key)
        return records[-1] if records else None

    def _append(self, record: IdempotencyRecord) -> None:
        self._records.setdefault(record.key, []).append(record)

    def _new_pending(self, key: str, payload: dict[str, Any], now: str) -> IdempotencyRecord:
        return IdempotencyRecord(
            key=key,
            status=STATUS_PENDING,
            payload=dict(payload),
            workOrderNo=None,
            reason=None,
            result=None,
            createdAt=now,
            updatedAt=now,
        )

    def get(self, key: str) -> IdempotencyRecord | None:
        with self._lock:
            return self._active(key)

    def history(self, key: str) -> list[IdempotencyRecord]:
        with self._lock:
            return list(self._records.get(key, []))

    def claim(self, key: str, payload: dict[str, Any]) -> ClaimResult:
        with self._lock:
            now = iso_now(self._clock)
            active = self._active(key)
            if active is None:
                record = self._new_pending(key, payload, now)
                self._append(record)
                self._persist()
                return ClaimResult(claimed=True, record=record)
            if active.status == STATUS_ACKED:
                return ClaimResult(claimed=False, record=active)
            if active.status == STATUS_PENDING:
                if self._expired(active):
                    active.status = STATUS_EXPIRED
                    active.updatedAt = now
                    record = self._new_pending(key, payload, now)
                    self._append(record)
                    self._persist()
                    return ClaimResult(claimed=True, record=record, expired=True)
                return ClaimResult(claimed=False, record=active)
            record = self._new_pending(key, payload, now)
            self._append(record)
            self._persist()
            return ClaimResult(claimed=True, record=record)

    def mark_acked(self, key: str, workOrderNo: str, *, result: dict[str, Any] | None = None) -> None:
        self._finish(key, STATUS_ACKED, work_order_no=workOrderNo, reason=None, result=result)

    def mark_failed(
        self,
        key: str,
        reason: str,
        *,
        work_order_no: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        self._finish(key, STATUS_FAILED, work_order_no=work_order_no, reason=reason, result=result)

    def mark_cancelled(self, key: str, reason: str) -> None:
        self._finish(key, STATUS_CANCELLED, work_order_no=None, reason=reason, result=None)

    def _finish(
        self,
        key: str,
        status: str,
        *,
        work_order_no: str | None,
        reason: str | None,
        result: dict[str, Any] | None,
    ) -> None:
        with self._lock:
            now = iso_now(self._clock)
            active = self._active(key)
            if active is None:
                record = IdempotencyRecord(
                    key=key,
                    status=status,
                    payload={},
                    workOrderNo=work_order_no,
                    reason=reason,
                    result=result,
                    createdAt=now,
                    updatedAt=now,
                )
                self._append(record)
            elif active.status == STATUS_PENDING:
                active.status = status
                if work_order_no is not None:
                    active.workOrderNo = work_order_no
                active.reason = reason
                active.result = result
                active.updatedAt = now
            self._persist()

    def cancel(
        self,
        *,
        key: str | None = None,
        work_order_no: str | None = None,
        reason: str = "",
    ) -> CancelOutcome:
        with self._lock:
            record, ambiguous = self._locate(key=key, work_order_no=work_order_no)
            if ambiguous:
                return CancelOutcome(CANCEL_AMBIGUOUS, None)
            if record is None:
                return CancelOutcome(CANCEL_NOT_FOUND, None)
            previous = record.status
            if previous == STATUS_ACKED:
                return CancelOutcome(CANCEL_ALREADY_ACKED, record, previous)
            if previous == STATUS_CANCELLED:
                return CancelOutcome(CANCEL_ALREADY_CANCELLED, record, previous)
            if previous == STATUS_PENDING:
                now = iso_now(self._clock)
                record.status = STATUS_CANCELLED
                record.reason = reason
                record.updatedAt = now
                self._persist()
                return CancelOutcome(CANCEL_CANCELLED, record, previous)
            return CancelOutcome(CANCEL_NOT_CANCELLABLE, record, previous)

    def _locate(
        self, key: str | None, work_order_no: str | None
    ) -> tuple[IdempotencyRecord | None, bool]:
        # 定位优先级：idempotencyKey > workOrderNo；key 命中则忽略 workOrderNo（冲突以 key 为准）
        if key:
            active = self._active(key)
            if active is not None:
                return active, False
        if work_order_no:
            matches = self._all_by_work_order_no(work_order_no)
            if len(matches) > 1:
                return None, True
            if len(matches) == 1:
                return matches[0], False
        return None, False

    def _all_by_work_order_no(self, work_order_no: str) -> list[IdempotencyRecord]:
        matches: list[IdempotencyRecord] = []
        for records in self._records.values():
            for record in records:  # 含 pending/acked/cancelled/expired/历史，全部参与定位
                if record.workOrderNo == work_order_no:
                    matches.append(record)
        return matches