"""Transactional, bounded scoring workflow for the offline detector."""

from __future__ import annotations

import hashlib
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    Case,
    Customer,
    Merchant,
    ModelVersion,
    Order,
    PolicyVersion,
    ReturnRequest,
    RiskAssessment,
)
from app.models.enums import CaseStatus, MerchantStatus, ReturnStatus, RiskDecision, VersionStatus
from app.risk.offline import ALL_FEATURES, MODEL_VERSION, POLICY_VERSION, CostConfig, decide, graph_risk, rule_engine
from app.schemas.scoring import ReturnScoreRequest
from app.services.artifacts import ArtifactService


def online_features(request: ReturnScoreRequest) -> pd.DataFrame:
    """Build the immutable artifact's exact label-free feature contract."""
    values: dict[str, object] = {name: 0.0 for name in ALL_FEATURES}
    values.update(
        {
            "order_value_paise": float(request.order_value_paise),
            "discount_percentage": request.discount_percentage,
            "hours_from_delivery_to_return": request.hours_from_delivery_to_return,
            "account_age_days": request.account_age_days,
            "product_category": request.product_category,
            "reason_code": request.reason_code,
            "time_since_previous_return_hours": 9999.0,
            "distance_to_verified_abuse": 4.0,
        }
    )
    shared = max(0, len(set(request.identity_tokens.values())) - 1)
    values.update(
        {
            "degree": float(shared),
            "weighted_degree": float(shared),
            "component_size": float(shared + 1),
            "multi_identity_connections": float(shared // 2),
            "shared_identity_activity_7d": float(shared),
        }
    )
    return pd.DataFrame([values], columns=ALL_FEATURES)


def _ensure_versions(
    session: Session, request: ReturnScoreRequest, artifact: object
) -> tuple[ModelVersion, PolicyVersion]:
    metadata = artifact.metadata
    policy = metadata["policy"]
    weights = policy["weights"]
    model = session.scalar(select(ModelVersion).where(ModelVersion.version == MODEL_VERSION))
    if model is None:
        model = ModelVersion(
            version=MODEL_VERSION,
            status=VersionStatus.ACTIVE,
            model_type="HistGradientBoostingClassifier",
            artifact_uri="artifacts/generated/offline-hgb-v1/model.joblib",
            artifact_sha256=metadata["model_checksum"],
            feature_schema_hash=metadata["feature_schema_hash"],
            trained_at=request.event_time,
            training_data_version="synthetic-2.0.0",
            metrics_json={},
        )
        session.add(model)
        session.flush()
    policy_row = session.scalar(select(PolicyVersion).where(PolicyVersion.version == POLICY_VERSION))
    if policy_row is None:
        policy_row = PolicyVersion(
            version=POLICY_VERSION,
            status=VersionStatus.ACTIVE,
            ml_weight=weights[0],
            graph_weight=weights[1],
            rule_weight=weights[2],
            approve_max=policy["verify_threshold"],
            manual_review_min=policy["review_threshold"],
            cost_config_json=policy["costs"],
            review_capacity=int(policy["costs"]["max_review_rate"] * 100),
            selection_data_version="validation-only",
        )
        session.add(policy_row)
        session.flush()
    return model, policy_row


def _response(assessment: RiskAssessment, evidence: list[dict[str, object]], *, replay: bool) -> dict[str, object]:
    return {
        "assessment_id": str(assessment.assessment_id),
        "decision": assessment.decision.value,
        "final_risk": assessment.final_risk,
        "ml_probability": assessment.ml_probability,
        "graph_risk": assessment.graph_risk,
        "rule_risk": assessment.rule_risk,
        "evidence": evidence or assessment.evidence_snapshot.get("rules", []),
        "model_version": MODEL_VERSION,
        "policy_version": POLICY_VERSION,
        "idempotent_replay": replay,
    }


def score(
    session: Session, request: ReturnScoreRequest, idempotency_key: str, request_id: str, artifacts: ArtifactService
) -> dict[str, object]:
    """Persist a score atomically; replay returns the original immutable snapshot."""
    fingerprint = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
    existing = session.scalar(
        select(ReturnRequest)
        .join(Merchant, Merchant.id == ReturnRequest.merchant_id)
        .where(Merchant.external_id == request.merchant_id, ReturnRequest.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if existing.payload_fingerprint != fingerprint:
            raise ValueError("idempotency_conflict")
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.return_request_id == existing.id))
        if assessment is None:
            raise RuntimeError("idempotency record has no assessment")
        return _response(assessment, [], replay=True)
    artifact = artifacts.load()
    merchant = session.scalar(select(Merchant).where(Merchant.external_id == request.merchant_id))
    if merchant is None:
        merchant = Merchant(
            external_id=request.merchant_id, name=f"Merchant {request.merchant_id}", status=MerchantStatus.ACTIVE
        )
        session.add(merchant)
        session.flush()
    customer = session.scalar(
        select(Customer).where(Customer.merchant_id == merchant.id, Customer.external_id == request.customer_id)
    )
    if customer is None:
        customer = Customer(
            merchant_id=merchant.id, external_id=request.customer_id, account_created_at=request.event_time
        )
        session.add(customer)
        session.flush()
    order = session.scalar(select(Order).where(Order.merchant_id == merchant.id, Order.external_id == request.order_id))
    if order is None:
        order = Order(
            merchant_id=merchant.id,
            customer_id=customer.id,
            external_id=request.order_id,
            ordered_at=request.event_time,
            delivered_at=request.event_time,
            order_value_paise=request.order_value_paise,
            product_category=request.product_category,
            discount_basis_points=round(request.discount_percentage * 100),
        )
        session.add(order)
        session.flush()
    returned = ReturnRequest(
        merchant_id=merchant.id,
        customer_id=customer.id,
        order_id=order.id,
        external_id=request.return_id,
        event_time=request.event_time,
        reason_code=request.reason_code,
        requested_amount_paise=request.order_value_paise,
        status=ReturnStatus.SCORED,
        idempotency_key=idempotency_key,
        payload_fingerprint=fingerprint,
    )
    session.add(returned)
    session.flush()
    features = online_features(request)
    ml_probability = float(artifact.model.predict_proba(features)[0, 1])
    rule_scores, evidence = rule_engine(features)
    graph_score = float(graph_risk(features)[0])
    policy = artifact.metadata["policy"]
    weights = policy["weights"]
    final_risk = float(weights[0] * ml_probability + weights[1] * graph_score + weights[2] * rule_scores[0])
    decision = RiskDecision(
        decide(
            np.array([final_risk]),
            policy["verify_threshold"],
            policy["review_threshold"],
            CostConfig(**policy["costs"]),
        )[0]
    )
    model, policy_row = _ensure_versions(session, request, artifact)
    assessment = RiskAssessment(
        assessment_id=uuid4(),
        return_request_id=returned.id,
        model_version_id=model.id,
        policy_version_id=policy_row.id,
        request_id=request_id,
        correlation_id=request_id,
        input_fingerprint=fingerprint,
        ml_probability=ml_probability,
        graph_risk=graph_score,
        rule_risk=float(rule_scores[0]),
        final_risk=final_risk,
        decision=decision,
        feature_snapshot=features.to_dict(orient="records")[0],
        evidence_snapshot={"rules": evidence[0]},
        latency_ms=0,
    )
    session.add(assessment)
    session.flush()
    if decision is not RiskDecision.APPROVE:
        session.add(
            Case(
                case_id=uuid4(),
                risk_assessment_id=assessment.id,
                merchant_id=merchant.id,
                status=CaseStatus.OPEN,
                priority=round(final_risk * 100),
            )
        )
    session.add(
        AuditEvent(
            event_id=uuid4(),
            entity_type="risk_assessment",
            entity_id=str(assessment.assessment_id),
            event_type="SCORED",
            actor_type="system",
            request_id=request_id,
            correlation_id=request_id,
            payload_json={"decision": decision.value, "policy_version": POLICY_VERSION},
        )
    )
    return _response(assessment, evidence[0], replay=False)
