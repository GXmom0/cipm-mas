from __future__ import annotations

import threading
from datetime import datetime, timedelta

from apps.platform_api.core.clock import TZ_EAST8, FixedClock
from apps.platform_api.repository.idempotency_repo import (
    CANCEL_ALREADY_ACKED,
    CANCEL_ALREADY_CANCELLED,
    CANCEL_AMBIGUOUS,
    CANCEL_CANCELLED,
    CANCEL_NOT_FOUND,
    STATUS_ACKED,
    STATUS_CANCELLED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    IdempotencyRepo,
)

FIXED = datetime(2026, 11, 13, 8, 0, tzinfo=TZ_EAST8)


class MutableClock:
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def advance(self, seconds: int) -> None:
        self._moment = self._moment + timedelta(seconds=seconds)


def make_repo(tmp_path, clock=None, ttl: int = 600) -> IdempotencyRepo:
    return IdempotencyRepo(tmp_path / "idempotency.json", clock or FixedClock(FIXED), ttl_seconds=ttl)


def _make_app(tmp_path):
    from apps.platform_api.main import create_app
    from sdk.settings import CipmSettings

    settings = CipmSettings(
        audit_dir=str(tmp_path / "audit"),
        data_dir=str(tmp_path / "data"),
    )
    return create_app(settings, FixedClock(FIXED))


def _fake_agent(monkeypatch, calls: dict[str, int]) -> None:
    """隔离出真实设备/窗口：路由层每次真实下发都自增计数并返回独立工单号。"""
    from agents.execution.agent import DispatchOutcome
    import apps.platform_api.api.v1.execution as execution_module

    class FakeExecutionAgent:
        def dispatch(self, plot_no, prescription, operator="manager_li"):
            calls["n"] += 1
            work_order_no = f"WO-{plot_no}-{calls['n']}"
            return DispatchOutcome(
                work_order_no=work_order_no,
                plot_no=plot_no,
                status="dispatched",
                message="Mock 设备已受理，作业指令进入执行队列。",
                command={"workOrderNo": work_order_no},
                receipt={
                    "accepted": True,
                    "receiptNo": f"RC-{work_order_no}",
                    "deviceNo": "DEV-XJ-01",
                },
                window_conclusion="pass",
            )

    monkeypatch.setattr(execution_module, "ExecutionAgent", FakeExecutionAgent)


# ---------- 仓库层（不依赖端口，沙箱可实跑） ----------


def test_first_dispatch_pending_to_acked(tmp_path) -> None:
    repo = make_repo(tmp_path)
    claim = repo.claim("K1", {"plotNo": "PLOT-0912"})
    assert claim.claimed is True
    assert repo.get("K1").status == STATUS_PENDING

    repo.mark_acked("K1", "WO-0912", result={"status": "dispatched"})

    record = repo.get("K1")
    assert record.status == STATUS_ACKED
    assert record.workOrderNo == "WO-0912"


def test_duplicate_key_not_reclaimed(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K1", "WO-0912", result={"status": "dispatched"})

    second = repo.claim("K1", {"plotNo": "PLOT-0912"})

    assert second.claimed is False
    assert second.record.status == STATUS_ACKED


def test_failed_can_retry(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0916"})
    repo.mark_failed("K1", "作业窗口校验不通过，转待重新排期")
    assert repo.get("K1").status == "failed"

    retry = repo.claim("K1", {"plotNo": "PLOT-0916"})

    assert retry.claimed is True
    repo.mark_acked("K1", "WO-0916")
    assert repo.get("K1").status == STATUS_ACKED


def test_concurrent_same_key_dispatch_once(tmp_path) -> None:
    repo = make_repo(tmp_path)
    results: list[bool] = []
    barrier = threading.Barrier(16)

    def worker() -> None:
        barrier.wait()
        results.append(repo.claim("K1", {"plotNo": "PLOT-0912"}).claimed)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(True) == 1
    assert results.count(False) == 15


def test_get_returns_none_for_unknown_key(tmp_path) -> None:
    repo = make_repo(tmp_path)
    assert repo.get("UNKNOWN") is None


def test_json_persistence_reload(tmp_path) -> None:
    clock = FixedClock(FIXED)
    repo = make_repo(tmp_path, clock=clock)
    repo.claim("K1", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K1", "WO-0912", result={"status": "dispatched"})

    reloaded = make_repo(tmp_path, clock=clock)

    record = reloaded.get("K1")
    assert record is not None
    assert record.status == STATUS_ACKED
    assert record.workOrderNo == "WO-0912"


# ---------- 1-B：cancel + TTL（仓库层） ----------


def test_cancel_allows_reclaim(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0912"})

    outcome = repo.cancel(key="K1", reason="用户取消")

    assert outcome.outcome == CANCEL_CANCELLED
    assert repo.get("K1").status == STATUS_CANCELLED
    again = repo.claim("K1", {"plotNo": "PLOT-0912"})
    assert again.claimed is True


def test_ttl_expired_allows_reclaim(tmp_path) -> None:
    clock = MutableClock(FIXED)
    repo = make_repo(tmp_path, clock=clock, ttl=600)
    first = repo.claim("K1", {"plotNo": "PLOT-0912"})
    assert first.claimed is True

    clock.advance(601)
    again = repo.claim("K1", {"plotNo": "PLOT-0912"})

    assert again.claimed is True
    assert again.expired is True
    history = repo.history("K1")
    assert history[0].status == STATUS_EXPIRED
    assert history[-1].status == STATUS_PENDING


def test_cancel_not_found(tmp_path) -> None:
    repo = make_repo(tmp_path)
    outcome = repo.cancel(work_order_no="WO-NOT-EXIST", reason="x")
    assert outcome.outcome == CANCEL_NOT_FOUND
    assert outcome.record is None


def test_cancel_acked_returns_already_acked(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K1", "WO-0912")

    outcome = repo.cancel(key="K1", reason="x")

    assert outcome.outcome == CANCEL_ALREADY_ACKED
    assert repo.get("K1").status == STATUS_ACKED


def test_cancel_is_idempotent(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0912"})

    first = repo.cancel(key="K1", reason="用户取消")
    second = repo.cancel(key="K1", reason="用户取消")

    assert first.outcome == CANCEL_CANCELLED
    assert second.outcome == CANCEL_ALREADY_CANCELLED
    assert repo.get("K1").status == STATUS_CANCELLED


def test_cancel_by_unique_key(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0912"})

    outcome = repo.cancel(key="K1", reason="用户取消")

    assert outcome.outcome == CANCEL_CANCELLED
    assert outcome.previous_status == STATUS_PENDING
    assert repo.get("K1").status == STATUS_CANCELLED


def test_cancel_work_order_no_ambiguous(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K1", "WO-SHARED")
    repo.claim("K2", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K2", "WO-SHARED")

    outcome = repo.cancel(work_order_no="WO-SHARED", reason="x")

    assert outcome.outcome == CANCEL_AMBIGUOUS
    assert outcome.record is None
    assert repo.get("K1").status == STATUS_ACKED
    assert repo.get("K2").status == STATUS_ACKED


def test_cancel_prefers_key_over_work_order_no(tmp_path) -> None:
    repo = make_repo(tmp_path)
    repo.claim("K1", {"plotNo": "PLOT-0912"})
    repo.claim("K2", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K2", "WO-SHARED")

    outcome = repo.cancel(key="K1", work_order_no="WO-SHARED", reason="以 key 为准")

    assert outcome.outcome == CANCEL_CANCELLED
    assert repo.get("K1").status == STATUS_CANCELLED
    assert repo.get("K2").status == STATUS_ACKED


# ---------- 路由层（需 TestClient；沙箱禁止 loopback 时自动跳过） ----------


def test_dispatch_same_key_replayed(tmp_path, monkeypatch) -> None:
    from tests.support import open_test_client

    calls = {"n": 0}
    _fake_agent(monkeypatch, calls)

    with open_test_client(_make_app(tmp_path)) as client:
        first = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-1"},
        )
        second = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-1"},
        )

    assert first.status_code == 200
    assert first.json()["data"]["replayed"] is False
    assert second.status_code == 200
    assert second.json()["data"]["replayed"] is True
    assert second.json()["data"]["workOrderNo"] == first.json()["data"]["workOrderNo"]
    assert calls["n"] == 1


def test_dispatch_different_keys_both_execute(tmp_path, monkeypatch) -> None:
    from tests.support import open_test_client

    calls = {"n": 0}
    _fake_agent(monkeypatch, calls)

    with open_test_client(_make_app(tmp_path)) as client:
        first = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "OP-A"},
        )
        second = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "OP-B"},
        )

    assert calls["n"] == 2
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["replayed"] is False
    assert second.json()["data"]["replayed"] is False
    assert first.json()["data"]["workOrderNo"] != second.json()["data"]["workOrderNo"]


def test_dispatch_missing_key_returns_400(tmp_path) -> None:
    from tests.support import open_test_client

    with open_test_client(_make_app(tmp_path)) as client:
        response = client.post("/api/v1/agents/execution/dispatch", json={"plotNo": "PLOT-0912"})

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "CIPM-EXEC-6005"
    assert "幂等键" in payload["message"]


def test_dispatch_accepts_header_key(tmp_path, monkeypatch) -> None:
    from tests.support import open_test_client

    calls = {"n": 0}
    _fake_agent(monkeypatch, calls)

    with open_test_client(_make_app(tmp_path)) as client:
        first = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912"},
            headers={"Idempotency-Key": "HDR-1"},
        )
        second = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912"},
            headers={"Idempotency-Key": "HDR-1"},
        )

    assert first.status_code == 200
    assert second.json()["data"]["replayed"] is True
    assert calls["n"] == 1


def test_cancel_route_not_found(tmp_path) -> None:
    from tests.support import open_test_client

    with open_test_client(_make_app(tmp_path)) as client:
        response = client.post(
            "/api/v1/agents/execution/cancel",
            json={"workOrderNo": "WO-NOT-EXIST", "reason": "x"},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "CIPM-EXEC-6006"


def test_cancel_route_already_acked_409(tmp_path) -> None:
    from tests.support import open_test_client

    app = _make_app(tmp_path)
    app.state.idempotency_repo.claim("K1", {"plotNo": "PLOT-0912"})
    app.state.idempotency_repo.mark_acked("K1", "WO-0912")

    with open_test_client(app) as client:
        response = client.post("/api/v1/agents/execution/cancel", json={"idempotencyKey": "K1"})

    assert response.status_code == 409
    assert response.json()["code"] == "CIPM-EXEC-6007"


def test_cancel_route_idempotent_200(tmp_path) -> None:
    from tests.support import open_test_client

    app = _make_app(tmp_path)
    app.state.idempotency_repo.claim("K1", {"plotNo": "PLOT-0912"})

    with open_test_client(app) as client:
        first = client.post("/api/v1/agents/execution/cancel", json={"idempotencyKey": "K1"})
        second = client.post("/api/v1/agents/execution/cancel", json={"idempotencyKey": "K1"})

    assert first.status_code == 200
    assert first.json()["data"]["status"] == "cancelled"
    assert second.status_code == 200
    assert second.json()["data"]["replayed"] is True

def test_cancel_route_ambiguous_409(tmp_path) -> None:
    from tests.support import open_test_client

    app = _make_app(tmp_path)
    repo = app.state.idempotency_repo
    repo.claim("K1", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K1", "WO-SHARED")
    repo.claim("K2", {"plotNo": "PLOT-0912"})
    repo.mark_acked("K2", "WO-SHARED")

    with open_test_client(app) as client:
        response = client.post("/api/v1/agents/execution/cancel", json={"workOrderNo": "WO-SHARED"})

    assert response.status_code == 409
    assert response.json()["code"] == "CIPM-EXEC-6008"


def test_cancel_route_writes_audit(tmp_path) -> None:
    from pathlib import Path
    from tests.support import open_test_client

    app = _make_app(tmp_path)
    app.state.idempotency_repo.claim("K1", {"plotNo": "PLOT-0912"})

    with open_test_client(app) as client:
        response = client.post(
            "/api/v1/agents/execution/cancel",
            json={"idempotencyKey": "K1", "reason": "窗口变化", "operator": "manager_li"},
        )

    assert response.status_code == 200
    audit_file = Path(tmp_path / "audit" / "2026-11-13.jsonl")
    assert audit_file.exists()
    text = audit_file.read_text(encoding="utf-8")
    assert "workorder.cancel" in text
    assert "manager_li" in text
    assert "窗口变化" in text
    assert "pending" in text
    assert "cancelled" in text

def test_dispatch_route_writes_audit_with_key(tmp_path, monkeypatch) -> None:
    import json
    from pathlib import Path
    from tests.support import open_test_client

    calls = {"n": 0}
    _fake_agent(monkeypatch, calls)
    app = _make_app(tmp_path)

    with open_test_client(app) as client:
        response = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-AUDIT-1"},
        )

    assert response.status_code == 200
    audit_file = Path(tmp_path / "audit" / "2026-11-13.jsonl")
    rows = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    dispatch_rows = [row for row in rows if row["eventType"] == "workorder.dispatch"]
    assert dispatch_rows
    assert dispatch_rows[-1]["afterValue"]["idempotencyKey"] == "KEY-AUDIT-1"
    assert dispatch_rows[-1]["afterValue"]["replayed"] is False


def test_dispatch_route_replay_writes_audit(tmp_path, monkeypatch) -> None:
    import json
    from pathlib import Path
    from tests.support import open_test_client

    calls = {"n": 0}
    _fake_agent(monkeypatch, calls)
    app = _make_app(tmp_path)

    with open_test_client(app) as client:
        client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-REPLAY-1"},
        )
        second = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-REPLAY-1"},
        )

    assert second.json()["data"]["replayed"] is True
    audit_file = Path(tmp_path / "audit" / "2026-11-13.jsonl")
    rows = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    replay_rows = [
        row
        for row in rows
        if row["eventType"] == "workorder.dispatch" and row["afterValue"].get("replayed") is True
    ]
    assert replay_rows
    assert replay_rows[-1]["afterValue"]["idempotencyKey"] == "KEY-REPLAY-1"

def test_claim_record_work_order_no_matches_outcome(tmp_path, monkeypatch) -> None:
    from tests.support import open_test_client

    calls = {"n": 0}
    _fake_agent(monkeypatch, calls)
    app = _make_app(tmp_path)

    with open_test_client(app) as client:
        response = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-SRC"},
        )

    outcome_work_order_no = response.json()["data"]["workOrderNo"]
    record = app.state.idempotency_repo.get("KEY-SRC")
    assert record.workOrderNo == outcome_work_order_no
    assert outcome_work_order_no != ""

def test_dispatch_route_rejected_writes_audit(tmp_path) -> None:
    import json
    from pathlib import Path
    from tests.support import open_test_client

    app = _make_app(tmp_path)

    with open_test_client(app) as client:
        response = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-REJ"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rejected"
    audit_file = Path(tmp_path / "audit" / "2026-11-13.jsonl")
    rows = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    rejected_rows = [
        row for row in rows if row["eventType"] == "workorder.dispatch" and row["afterValue"].get("status") == "rejected"
    ]
    assert rejected_rows
    assert rejected_rows[-1]["afterValue"]["idempotencyKey"] == "KEY-REJ"
    assert rejected_rows[-1]["afterValue"]["reason"]


def test_dispatch_route_rescheduled_writes_audit(tmp_path) -> None:
    import json
    from pathlib import Path
    from tests.support import open_test_client

    app = _make_app(tmp_path)

    with open_test_client(app) as client:
        response = client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0916", "idempotencyKey": "KEY-RES"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rescheduled"
    audit_file = Path(tmp_path / "audit" / "2026-11-13.jsonl")
    rows = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    rescheduled_rows = [
        row for row in rows if row["eventType"] == "workorder.dispatch" and row["afterValue"].get("status") == "rescheduled"
    ]
    assert rescheduled_rows
    assert rescheduled_rows[-1]["afterValue"]["idempotencyKey"] == "KEY-RES"
    assert rescheduled_rows[-1]["afterValue"]["workOrderNo"]
    assert rescheduled_rows[-1]["afterValue"]["reason"]

def test_dispatch_route_rejected_audit_queryable_by_plot_no(tmp_path) -> None:
    from tests.support import open_test_client

    app = _make_app(tmp_path)

    with open_test_client(app) as client:
        client.post(
            "/api/v1/agents/execution/dispatch",
            json={"plotNo": "PLOT-0912", "idempotencyKey": "KEY-REJ-BIZ"},
        )

    rows = app.state.audit_repo.query_by_biz_id("PLOT-0912")
    assert rows
    assert rows[-1]["eventType"] == "workorder.dispatch"
    assert rows[-1]["afterValue"]["status"] == "rejected"
    assert rows[-1]["afterValue"]["reason"]