"""Unit tests for fulfillment helpers (no DB)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.fulfillment import AWAITING, mark_awaiting_delivery


def test_mark_awaiting_delivery_sets_deadline(monkeypatch):
    monkeypatch.setenv("DELIVERY_SLA_HOURS", "48")
    from app.config import get_settings

    get_settings.cache_clear()
    txn = SimpleNamespace(
        fulfillment_status="none",
        delivery_deadline_at=None,
    )
    before = datetime.now(timezone.utc)
    mark_awaiting_delivery(txn)  # type: ignore[arg-type]
    assert txn.fulfillment_status == AWAITING
    assert txn.delivery_deadline_at is not None
    assert txn.delivery_deadline_at >= before + timedelta(hours=47)
    get_settings.cache_clear()
