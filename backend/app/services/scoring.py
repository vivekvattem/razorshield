"""Transactional, bounded scoring workflow for the offline detector."""

from __future__ import annotations

import hashlib
from datetime import UTC, timedelta
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    Case,
    Customer,
    IdentityLink,
    Merchant,
    ModelVersion,
    Order,
    PolicyVersion,
    ReturnRequest,
    RiskAssessment,
)
from app.models.enums import CaseStatus, IdentityType, MerchantStatus, ReturnStatus, RiskDecision, VersionStatus
from app.risk.offline import ALL_FEATURES, MODEL_VERSION, CostConfig, decide, graph_risk, rule_engine
from app.schemas.scoring import ReturnScoreRequest
from app.services.artifacts import ArtifactService
from app.services.intelligence import deterministic_explanation, uncertainty_indicator

OPERATIONAL_POLICY_VERSION = "operational-demo-v2"


def online_features(session: Session, request: ReturnScoreRequest, customer: Customer) -> pd.DataFrame:
    """Build point-in-time features from persisted observations strictly before the event."""
    event_time = request.event_time.astimezone(UTC)

    def utc(value):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    values: dict[str, object] = {name: 0.0 for name in ALL_FEATURES}
    prior_orders = session.scalars(
        select(Order).where(Order.customer_id == customer.id, Order.ordered_at < event_time)
    ).all()
    prior_returns = session.scalars(
        select(ReturnRequest).where(ReturnRequest.customer_id == customer.id, ReturnRequest.event_time < event_time)
    ).all()

    def count_orders(days: int) -> int:
        return sum(utc(order.ordered_at) >= event_time - timedelta(days=days) for order in prior_orders)

    def prior_in(days: int) -> list[ReturnRequest]:
        return [item for item in prior_returns if utc(item.event_time) >= event_time - timedelta(days=days)]

    token_hashes = {
        key.upper(): hashlib.sha256(value.encode()).hexdigest() for key, value in request.identity_tokens.items()
    }
    neighbors: dict[object, int] = {}
    shared_counts = {
        name: 0
        for name in (
            "shared_device_accounts",
            "shared_payment_accounts",
            "shared_address_accounts",
            "shared_phone_accounts",
            "shared_ip_accounts",
        )
    }
    identity_map = {
        "DEVICE": "shared_device_accounts",
        "PAYMENT": "shared_payment_accounts",
        "ADDRESS": "shared_address_accounts",
        "PHONE": "shared_phone_accounts",
        "IP": "shared_ip_accounts",
    }
    recent_activity = 0
    for kind, column in identity_map.items():
        token = token_hashes.get(kind)
        if not token:
            continue
        links = session.scalars(
            select(IdentityLink).where(IdentityLink.token_hash == token, IdentityLink.first_seen_at < event_time)
        ).all()
        members = {link.customer_id for link in links if link.customer_id != customer.id}
        shared_counts[column] = len(members)
        recent_activity += sum(utc(link.last_seen_at) >= event_time - timedelta(days=7) for link in links)
        for member in members:
            neighbors[member] = neighbors.get(member, 0) + 1
    order_values = [order.order_value_paise for order in prior_orders]
    prior_1h, prior_24h, prior_7d, prior_30d, prior_90d = (
        prior_in(1 / 24),
        prior_in(1),
        prior_in(7),
        prior_in(30),
        prior_in(90),
    )
    # The stored schema has no verification-label table: do not infer one at serving time.
    baseline = float(np.mean(order_values)) if order_values else float(request.order_value_paise)
    values.update(
        {
            "order_value_paise": float(request.order_value_paise),
            "discount_percentage": request.discount_percentage,
            "hours_from_delivery_to_return": request.hours_from_delivery_to_return,
            "account_age_days": max(0.0, (event_time - utc(customer.account_created_at)).total_seconds() / 86400),
            "product_category": request.product_category,
            "reason_code": request.reason_code,
            "orders_7d": count_orders(7),
            "orders_30d": count_orders(30),
            "orders_90d": count_orders(90),
            "returns_7d": len(prior_7d),
            "returns_30d": len(prior_30d),
            "returns_90d": len(prior_90d),
            "refund_ratio_90d": len(prior_90d) / max(1, count_orders(90)),
            "average_order_value_prior": baseline,
            "order_value_deviation": request.order_value_paise - baseline,
            "returns_1h": len(prior_1h),
            "returns_24h": len(prior_24h),
            "time_since_previous_return_hours": (
                event_time - max(utc(item.event_time) for item in prior_returns)
            ).total_seconds()
            / 3600
            if prior_returns
            else 9999.0,
            "shared_identity_activity_7d": recent_activity,
            "distance_to_verified_abuse": 4.0,
            **shared_counts,
        }
    )
    shared = len(neighbors)
    values.update(
        {
            "degree": float(shared),
            "weighted_degree": float(sum(neighbors.values())),
            "component_size": float(shared + 1),
            "multi_identity_connections": float(sum(count >= 2 for count in neighbors.values())),
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
    policy_row = session.scalar(select(PolicyVersion).where(PolicyVersion.version == OPERATIONAL_POLICY_VERSION))
    if policy_row is None:
        policy_row = PolicyVersion(
            # Operational thresholds are a separate, capacity-bounded demo policy.
            # The immutable validation policy remains only in the evaluation artifact.
            version=OPERATIONAL_POLICY_VERSION,
            status=VersionStatus.ACTIVE,
            ml_weight=weights[0],
            graph_weight=weights[1],
            rule_weight=weights[2],
            approve_max=0.10,
            manual_review_min=0.20,
            cost_config_json=policy["costs"],
            review_capacity=int(policy["costs"]["max_review_rate"] * 100),
            selection_data_version="validation-derived-capacity-guardrail",
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
        "policy_version": OPERATIONAL_POLICY_VERSION,
        "explanation": deterministic_explanation(
            assessment, (0.7, 0.2, 0.1), MODEL_VERSION, OPERATIONAL_POLICY_VERSION
        ),
        "uncertainty": uncertainty_indicator(assessment, 0.1, 0.2),
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
    features = online_features(session, request, customer)
    for raw_type, raw_token in request.identity_tokens.items():
        try:
            identity_type = IdentityType(raw_type.upper())
        except ValueError:
            continue
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        link = session.scalar(
            select(IdentityLink).where(
                IdentityLink.customer_id == customer.id,
                IdentityLink.identity_type == identity_type,
                IdentityLink.token_hash == token_hash,
            )
        )
        if link is None:
            session.add(
                IdentityLink(
                    merchant_id=merchant.id,
                    customer_id=customer.id,
                    identity_type=identity_type,
                    token_hash=token_hash,
                    first_seen_at=request.event_time,
                    last_seen_at=request.event_time,
                    observation_count=1,
                )
            )
        else:
            # Requests are accepted in chronological order for a given observation;
            # avoid mixing SQLite's naive readback with timezone-aware input here.
            link.last_seen_at = request.event_time
            link.observation_count += 1
    ml_probability = float(artifact.model.predict_proba(features)[0, 1])
    rule_scores, evidence = rule_engine(features)
    graph_score = float(graph_risk(features)[0])
    policy = artifact.metadata["policy"]
    weights = policy["weights"]
    final_risk = float(weights[0] * ml_probability + weights[1] * graph_score + weights[2] * rule_scores[0])
    decision = RiskDecision(
        decide(
            np.array([final_risk]),
            0.10,
            0.20,
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
            payload_json={"decision": decision.value, "policy_version": OPERATIONAL_POLICY_VERSION},
        )
    )
    return _response(assessment, evidence[0], replay=False)
