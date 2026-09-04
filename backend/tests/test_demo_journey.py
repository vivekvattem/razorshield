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
    explanation = client.get(f"/api/v1/cases/{case_id}/explanation")
    assert explanation.status_code == 200
    assert explanation.json()["model_version"] == "offline-hgb-v1"
    graph = client.get(f"/api/v1/cases/{case_id}/graph")
    assert graph.status_code == 200
    graph_payload = graph.json()
    assert len(graph_payload["nodes"]) <= graph_payload["bounded"]["max_nodes"]
    assert len(graph_payload["edges"]) <= graph_payload["bounded"]["max_edges"]
    assert graph_payload["statistics"]["linked_account_count"] == 4
    assert set(graph_payload["statistics"]["connection_types"]) == {"address", "device", "ip", "payment"}
    assert "ring-device" not in str(graph_payload)

    populated = client.get("/api/v1/metrics/feedback")
    assert populated.status_code == 200
    assert populated.json()["insufficient_evidence_count"] == 1
    assert populated.json()["analyst_model_agreement_rate"] is None

    client.post(f"/api/v1/cases/{case_id}/feedback", json={"disposition": "CONFIRMED_ABUSE"})
    updated = client.get("/api/v1/metrics/feedback").json()
    assert updated["total_labelled_cases"] == 1
    assert updated["analyst_model_agreement_rate"] == 1
    get_settings.cache_clear()


def test_business_metrics_have_live_counts(client) -> None:
    response = client.get("/api/v1/metrics/business")
    assert response.status_code == 200
    assert set(response.json()["live"]["decision_counts"]) == {"APPROVE", "VERIFY", "MANUAL_REVIEW"}
    empty_feedback = client.get("/api/v1/metrics/feedback").json()
    assert empty_feedback["total_labelled_cases"] == 0
    assert empty_feedback["feedback_coverage_percentage"] == 0


def test_threshold_report_matches_locked_artifact(client) -> None:
    response = client.get("/api/v1/metrics/thresholds")
    assert response.status_code == 200
    rows = {row["source"]: row for row in response.json()["rows"]}
    assert rows["validation"]["verify_threshold"] == 0.3
    assert rows["locked_test"]["precision"] == 0.1836734693877551
    assert rows["locked_test"]["manual_review_rate"] == 0
    assert rows["operational"]["precision"] is None
