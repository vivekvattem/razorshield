from __future__ import annotations


def _payload(return_id: str = "ret-phase5") -> dict[str, object]:
    return {
        "merchant_id": "merchant-phase5",
        "customer_id": "customer-phase5",
        "order_id": "order-phase5",
        "return_id": return_id,
        "event_time": "2025-06-01T12:00:00Z",
        "order_value_paise": 125000,
        "product_category": "electronics",
        "reason_code": "DAMAGED",
        "discount_percentage": 5,
        "hours_from_delivery_to_return": 48,
        "account_age_days": 400,
        "identity_tokens": {"device": "synthetic-device-token"},
    }


def test_score_and_idempotent_replay(client) -> None:
    headers = {"Idempotency-Key": "phase5-score"}
    first = client.post("/api/v1/returns/score", json=_payload(), headers=headers)
    assert first.status_code == 200
    assert first.json()["decision"] in {"APPROVE", "VERIFY", "MANUAL_REVIEW"}
    replay = client.post("/api/v1/returns/score", json=_payload(), headers=headers)
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True


def test_idempotency_conflict_and_batch_partial_failure(client) -> None:
    headers = {"Idempotency-Key": "phase5-conflict"}
    assert client.post("/api/v1/returns/score", json=_payload(), headers=headers).status_code == 200
    altered = _payload()
    altered["order_value_paise"] = 999999
    assert client.post("/api/v1/returns/score", json=altered, headers=headers).status_code == 409
    batch = client.post(
        "/api/v1/returns/batch-score",
        json=[_payload("batch-one"), {"merchant_id": "invalid"}, _payload("batch-two")],
    )
    assert batch.status_code == 200
    assert [item["ok"] for item in batch.json()["results"]] == [True, False, True]
