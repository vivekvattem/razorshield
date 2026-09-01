"""Idempotently seed three bounded RazorShield demo journeys."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.db.session import Database
from app.schemas.scoring import ReturnScoreRequest
from app.services.artifacts import ArtifactService
from app.services.scoring import score


def request(case: str, when: datetime, **overrides: object) -> ReturnScoreRequest:
    base: dict[str, object] = {
        "merchant_id": "demo-merchant",
        "customer_id": f"demo-{case}",
        "order_id": f"order-{case}",
        "return_id": f"return-{case}",
        "event_time": when,
        "order_value_paise": 85000,
        "product_category": "electronics",
        "reason_code": "DAMAGED",
        "discount_percentage": 5.0,
        "hours_from_delivery_to_return": 72.0,
        "account_age_days": 365.0,
        "identity_tokens": {"DEVICE": f"device-{case}", "PAYMENT": f"payment-{case}"},
    }
    base.update(overrides)
    return ReturnScoreRequest.model_validate(base)


def main() -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    artifacts = ArtifactService(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "artifacts/generated/offline-hgb-v1"
    )
    now = datetime(2025, 6, 20, 12, tzinfo=UTC)
    journeys = [request("legitimate", now, order_value_paise=24000, product_category="apparel")]
    for index in range(4):
        journeys.append(
            request(
                f"velocity-{index}",
                now - timedelta(hours=16 - index),
                customer_id="demo-velocity",
                identity_tokens={"DEVICE": "velocity-device"},
            )
        )
    journeys.append(
        request("velocity-final", now, customer_id="demo-velocity", identity_tokens={"DEVICE": "velocity-device"})
    )
    for index in range(4):
        journeys.append(
            request(
                f"ring-{index}",
                now - timedelta(days=1),
                identity_tokens={
                    "DEVICE": "ring-device",
                    "PAYMENT": "ring-payment",
                    "ADDRESS": "ring-address",
                    "IP": "ring-ip",
                },
            )
        )
    journeys.append(
        request(
            "ring-final",
            now,
            identity_tokens={
                "DEVICE": "ring-device",
                "PAYMENT": "ring-payment",
                "ADDRESS": "ring-address",
                "IP": "ring-ip",
            },
        )
    )
    for item in journeys:
        with database.transaction() as session:
            score(session, item, f"demo:{item.return_id}", f"seed:{item.return_id}", artifacts)
    print("Seeded RazorShield demo journeys idempotently.")


if __name__ == "__main__":
    main()
