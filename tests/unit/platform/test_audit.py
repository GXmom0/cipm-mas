from __future__ import annotations

from datetime import datetime
from pathlib import Path

from apps.platform_api.core.clock import TZ_EAST8, FixedClock
from apps.platform_api.repository.audit_repo import AuditRepo
from sdk.observability import redact

ROOT = Path(__file__).resolve().parents[3]
FIXED = datetime(2026, 11, 13, 8, 0, tzinfo=TZ_EAST8)


def test_p09_append_and_query(tmp_path) -> None:
    repo = AuditRepo(tmp_path / "audit", FixedClock(FIXED))
    first = repo.append("prescription.review", "manager_li", biz_id="WO-001", after={"status": "approved"})
    second = repo.append("workorder.dispatch", "executor", biz_id="WO-001", result="success")
    assert first != second
    rows = repo.query_by_biz_id("WO-001")
    assert len(rows) == 2
    assert rows[0]["eventType"] == "prescription.review"
    assert rows[1]["eventType"] == "workorder.dispatch"
    assert rows[0]["occurredAt"].endswith("+08:00")
    assert Path(tmp_path / "audit" / "2026-11-13.jsonl").exists()


def test_p10_append_only(tmp_path) -> None:
    repo = AuditRepo(tmp_path / "audit", FixedClock(FIXED))
    repo.append("first", "operator")
    path = tmp_path / "audit" / "2026-11-13.jsonl"
    before = path.read_bytes()
    repo.append("second", "operator")
    after = path.read_bytes()
    assert after.startswith(before)
    assert after != before


def test_p11_redaction_samples() -> None:
    samples = [
        ({"authorization": "Bearer abc"}, None),
        ({"headers": {"x-obs-security-token": "obs-secret"}}, None),
        ({"apiKey": "plain-key"}, None),
        ({"url": "https://bucket.obs/x?Signature=abc123"}, "abc123"),
        ({"url": "https://bucket.obs/x?X-Amz-Signature=deadbeef"}, "deadbeef"),
        ({"callback": "cred://super-secret"}, "super-secret"),
        ({"llm_api_key": "sk-12345"}, "sk-12345"),
        ({"nested": [{"token": "tok-abc"}]}, "tok-abc"),
    ]
    for payload, forbidden in samples:
        cleaned = redact(payload)
        assert "***" in repr(cleaned)
        if forbidden:
            assert forbidden not in repr(cleaned)


def test_p12_data_dir_ignored() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/" in text


def test_audit_sensitive_value_redacted(tmp_path) -> None:
    repo = AuditRepo(tmp_path / "audit", FixedClock(FIXED))
    repo.append(
        "config.update",
        "admin",
        biz_id="CFG-1",
        after={"api_key": "sk-should-not-appear", "endpoint": "https://x?Signature=abc"},
    )
    text = (tmp_path / "audit" / "2026-11-13.jsonl").read_text(encoding="utf-8")
    assert "sk-should-not-appear" not in text
    assert "Signature=abc" not in text