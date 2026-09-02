"""Deterministic, non-causal intelligence summaries for analyst review."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Case, RiskAssessment

EXPLANATION_VERSION = "deterministic-signals-v1"
UNCERTAINTY_VERSION = "data-sufficiency-v1"


def _finite(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number == number and abs(number) != float("inf") else default


def deterministic_explanation(
    assessment: RiskAssessment,
    weights: tuple[float, float, float],
    model_version: str,
    policy_version: str,
) -> dict[str, Any]:
    """Explain stored signals with documented deterministic heuristics, never fake SHAP."""
    features = assessment.feature_snapshot
    candidates = [
        ("returns_24h", _finite(features.get("returns_24h")), 2.0, "Recent return velocity is elevated"),
        ("refund_ratio_90d", _finite(features.get("refund_ratio_90d")), 0.45, "The recent refund ratio is elevated"),
        (
            "shared_payment_accounts",
            _finite(features.get("shared_payment_accounts")),
            1.0,
            "Multiple accounts share a payment identity",
        ),
        (
            "shared_device_accounts",
            _finite(features.get("shared_device_accounts")),
            1.0,
            "Multiple accounts share a device identity",
        ),
        ("component_size", _finite(features.get("component_size"), 1.0), 3.0, "The connected component is larger"),
        (
            "multi_identity_connections",
            _finite(features.get("multi_identity_connections")),
            1.0,
            "Accounts are connected through multiple identity types",
        ),
    ]
    increasing = [
        {
            "feature": name,
            "value": value,
            "direction": "increases_risk",
            "strength": round(min(1.0, value / threshold), 4),
            "evidence": evidence,
        }
        for name, value, threshold, evidence in candidates
        if value >= threshold
    ]
    increasing.sort(key=lambda factor: (-factor["strength"], factor["feature"]))

    reducing: list[dict[str, Any]] = []
    account_age = _finite(features.get("account_age_days"))
    if account_age >= 365:
        reducing.append(
            {
                "feature": "account_age_days",
                "value": account_age,
                "direction": "reduces_risk",
                "strength": round(min(1.0, account_age / 730), 4),
                "evidence": "The customer account has an established history",
            }
        )
    refund_ratio = _finite(features.get("refund_ratio_90d"))
    if refund_ratio <= 0.15:
        reducing.append(
            {
                "feature": "refund_ratio_90d",
                "value": refund_ratio,
                "direction": "reduces_risk",
                "strength": round(1 - refund_ratio / 0.15, 4),
                "evidence": "The recent refund ratio is low",
            }
        )
    if _finite(features.get("component_size"), 1.0) <= 1:
        reducing.append(
            {
                "feature": "component_size",
                "value": 1.0,
                "direction": "reduces_risk",
                "strength": 0.7,
                "evidence": "No linked customer accounts were observed",
            }
        )
    reducing.sort(key=lambda factor: (-factor["strength"], factor["feature"]))

    components = {
        "model": round(assessment.ml_probability * weights[0], 6),
        "network": round(assessment.graph_risk * weights[1], 6),
        "rules": round(assessment.rule_risk * weights[2], 6),
    }
    summary = (
        "; ".join(factor["evidence"] for factor in increasing[:3])
        or "No elevated deterministic risk factor crossed its documented explanation threshold"
    )
    return {
        "method": "deterministic_signal_explanation_not_shap",
        "explanation_version": EXPLANATION_VERSION,
        "model_version": model_version,
        "policy_version": policy_version,
        "top_increasing_factors": increasing[:5],
        "top_reducing_factors": reducing[:3],
        "signal_contributions": components,
        "summary": summary + ".",
        "human_review_notice": "This explanation supports human review and is not causal proof of abuse.",
    }


def uncertainty_indicator(assessment: RiskAssessment, approve_max: float, manual_review_min: float) -> dict[str, str]:
    """Return a data-sufficiency heuristic; this is not statistical confidence."""
    features = assessment.feature_snapshot
    orders_90d = _finite(features.get("orders_90d"))
    component_size = _finite(features.get("component_size"), 1.0)
    if orders_90d < 3 and component_size <= 1:
        state = "INSUFFICIENT_HISTORY"
        reason = "Fewer than three prior 90-day orders and no linked accounts are available."
    elif min(abs(assessment.final_risk - approve_max), abs(assessment.final_risk - manual_review_min)) <= 0.05:
        state = "BORDERLINE"
        reason = "The final risk is within 0.05 of an operational policy threshold."
    else:
        state = "HIGH_CONFIDENCE"
        reason = "The score is more than 0.05 from policy thresholds and sufficient history or graph context exists."
    return {
        "state": state,
        "reason": reason,
        "method": "heuristic_not_statistical_confidence",
        "version": UNCERTAINTY_VERSION,
    }


def feedback_analytics(session: Session) -> dict[str, Any]:
    """Summarize the latest append-only feedback event per case."""
    events = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.event_type == "ANALYST_FEEDBACK")
        .order_by(AuditEvent.occurred_at, AuditEvent.id)
    ).all()
    latest = {event.entity_id: event for event in events}
    counts = Counter(str(event.payload_json.get("disposition", "")) for event in latest.values())
    total_cases = session.scalar(select(func.count()).select_from(Case)) or 0
    agreement_numerator = 0
    agreement_denominator = 0
    potential_false_positives = 0
    for case_id, event in latest.items():
        try:
            parsed_case_id = UUID(case_id)
        except ValueError:
            continue
        case = session.scalar(select(Case).where(Case.case_id == parsed_case_id))
        if case is None:
            continue
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.id == case.risk_assessment_id))
        disposition = event.payload_json.get("disposition")
        if disposition == "INSUFFICIENT_EVIDENCE":
            continue
        agreement_denominator += 1
        flagged = assessment.decision.value in {"VERIFY", "MANUAL_REVIEW"}
        agreed = (disposition == "CONFIRMED_ABUSE" and flagged) or (disposition == "LEGITIMATE_RETURN" and not flagged)
        agreement_numerator += int(agreed)
        potential_false_positives += int(disposition == "LEGITIMATE_RETURN" and flagged)
    total_labelled = len(latest)
    return {
        "confirmed_abuse_count": counts["CONFIRMED_ABUSE"],
        "legitimate_return_count": counts["LEGITIMATE_RETURN"],
        "insufficient_evidence_count": counts["INSUFFICIENT_EVIDENCE"],
        "total_labelled_cases": total_labelled,
        "analyst_model_agreement_rate": (
            round(agreement_numerator / agreement_denominator, 6) if agreement_denominator else None
        ),
        "agreement_denominator": agreement_denominator,
        "potential_false_positive_count": potential_false_positives,
        "feedback_coverage_percentage": round(100 * total_labelled / total_cases, 4) if total_cases else 0.0,
        "definition": (
            "Latest feedback per case; agreement means CONFIRMED_ABUSE on VERIFY/MANUAL_REVIEW or "
            "LEGITIMATE_RETURN on APPROVE. INSUFFICIENT_EVIDENCE is excluded from the agreement denominator."
        ),
        "automatic_retraining": False,
        "generated_at": datetime.now(UTC).isoformat(),
    }
