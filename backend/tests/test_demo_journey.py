from __future__ import annotations

import runpy
from pathlib import Path

from sqlalchemy import func

from app.core.config import get_settings
from app.models import Case, RiskAssessment
from app.models.enums import RiskDecision


def seed_demo() -> None:
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/seed_demo.py"), run_name="__main__")


def test_seeded_case_contract_feedback_and_export(client, session, database_url, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    seed_demo()
    seed_demo()
    session.expire_all()

    counts = dict(
        session.query(RiskAssessment.decision, func.count(RiskAssessment.assessment_id))
        .group_by(RiskAssessment.decision)
        .all()
    )
    assert counts == {
        RiskDecision.APPROVE: 6,
        RiskDecision.VERIFY: 4,
        RiskDecision.MANUAL_REVIEW: 1,
    }
    case = session.query(Case).join(RiskAssessment).filter(RiskAssessment.decision == RiskDecision.MANUAL_REVIEW).one()
    case_id = str(case.case_id)
    detail = client.get(f"/api/v1/cases/{case_id}")
    assert detail.status_code == 200
    assert detail.json()["assessment"]["decision"] in {"VERIFY", "MANUAL_REVIEW"}
    feedback = client.post(
        f"/api/v1/cases/{case_id}/feedback",
        json={"disposition": "INSUFFICIENT_EVIDENCE", "note": "Needs more merchant evidence"},
    )
    assert feedback.status_code == 200
    audit = client.get(f"/api/v1/cases/{case_id}/audit")
    assert any(item["event_type"] == "ANALYST_FEEDBACK" for item in audit.json()["items"])
    exported = client.get(f"/api/v1/cases/{case_id}/export")
    assert exported.status_code == 200
    payload = exported.json()
    assert payload["synthetic_demo"] is True
    assert "token_hash" not in str(payload)
    get_settings.cache_clear()


def test_business_metrics_have_live_counts(client) -> None:
    response = client.get("/api/v1/metrics/business")
    assert response.status_code == 200
    assert set(response.json()["live"]["decision_counts"]) == {"APPROVE", "VERIFY", "MANUAL_REVIEW"}
