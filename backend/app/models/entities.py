from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.models.enums import (
    AnalystAction,
    CaseStatus,
    IdentityType,
    MerchantStatus,
    ReturnStatus,
    RiskDecision,
    VersionStatus,
)


def portable_enum(enum_type: type) -> SqlEnum:
    return SqlEnum(enum_type, native_enum=False, create_constraint=True, validate_strings=True)


class Merchant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "merchants"

    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[MerchantStatus] = mapped_column(portable_enum(MerchantStatus), default=MerchantStatus.ACTIVE)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("merchant_id", "external_id", name="uq_customers_merchant_external"),
        Index("ix_customers_merchant_account_created", "merchant_id", "account_created_at"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"), index=True)
    external_id: Mapped[str] = mapped_column(String(64))
    account_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("merchant_id", "external_id", name="uq_orders_merchant_external"),
        CheckConstraint("order_value_paise >= 0", name="ck_orders_value_nonnegative"),
        CheckConstraint(
            "discount_basis_points >= 0 AND discount_basis_points <= 10000",
            name="ck_orders_discount_range",
        ),
        Index("ix_orders_merchant_ordered", "merchant_id", "ordered_at"),
        Index("ix_orders_customer_ordered", "customer_id", "ordered_at"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    external_id: Mapped[str] = mapped_column(String(64))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_value_paise: Mapped[int] = mapped_column(Integer)
    product_category: Mapped[str] = mapped_column(String(80))
    discount_basis_points: Mapped[int] = mapped_column(Integer, default=0)
    promo_code: Mapped[str | None] = mapped_column(String(80), nullable=True)


class ReturnRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "return_requests"
    __table_args__ = (
        UniqueConstraint("merchant_id", "external_id", name="uq_returns_merchant_external"),
        UniqueConstraint("merchant_id", "idempotency_key", name="uq_returns_merchant_idempotency"),
        CheckConstraint("requested_amount_paise >= 0", name="ck_returns_amount_nonnegative"),
        Index("ix_returns_merchant_event", "merchant_id", "event_time"),
        Index("ix_returns_customer_event", "customer_id", "event_time"),
        Index("ix_returns_status_event", "status", "event_time"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True)
    external_id: Mapped[str] = mapped_column(String(64))
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason_code: Mapped[str] = mapped_column(String(80))
    requested_amount_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReturnStatus] = mapped_column(portable_enum(ReturnStatus), default=ReturnStatus.RECEIVED)
    source: Mapped[str] = mapped_column(String(40), default="api")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IdentityLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "identity_links"
    __table_args__ = (
        UniqueConstraint("customer_id", "identity_type", "token_hash", name="uq_identity_link"),
        CheckConstraint("observation_count >= 1", name="ck_identity_observations_positive"),
        Index("ix_identity_type_token", "identity_type", "token_hash"),
        Index("ix_identity_customer_last_seen", "customer_id", "last_seen_at"),
    )

    merchant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    identity_type: Mapped[IdentityType] = mapped_column(portable_enum(IdentityType))
    token_hash: Mapped[str] = mapped_column(String(128))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observation_count: Mapped[int] = mapped_column(Integer, default=1)


class ModelVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "model_versions"

    version: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[VersionStatus] = mapped_column(portable_enum(VersionStatus), default=VersionStatus.DRAFT)
    model_type: Mapped[str] = mapped_column(String(80))
    artifact_uri: Mapped[str] = mapped_column(String(500))
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    feature_schema_hash: Mapped[str] = mapped_column(String(64))
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    training_data_version: Mapped[str] = mapped_column(String(64))
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PolicyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        CheckConstraint("ml_weight >= 0 AND ml_weight <= 1", name="ck_policy_ml_weight"),
        CheckConstraint("graph_weight >= 0 AND graph_weight <= 1", name="ck_policy_graph_weight"),
        CheckConstraint("rule_weight >= 0 AND rule_weight <= 1", name="ck_policy_rule_weight"),
        CheckConstraint("approve_max < manual_review_min", name="ck_policy_threshold_order"),
        CheckConstraint("review_capacity >= 0", name="ck_policy_capacity_nonnegative"),
    )

    version: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[VersionStatus] = mapped_column(portable_enum(VersionStatus), default=VersionStatus.DRAFT)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ml_weight: Mapped[float] = mapped_column(default=1.0)
    graph_weight: Mapped[float] = mapped_column(default=0.0)
    rule_weight: Mapped[float] = mapped_column(default=0.0)
    approve_max: Mapped[float] = mapped_column(default=0.3)
    manual_review_min: Mapped[float] = mapped_column(default=0.7)
    cost_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    review_capacity: Mapped[int] = mapped_column(Integer, default=0)
    selection_data_version: Mapped[str] = mapped_column(String(64))


class RiskAssessment(UUIDPrimaryKeyMixin, Base):
    """Append-only score snapshot; services never update rows after insertion."""

    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("ml_probability >= 0 AND ml_probability <= 1", name="ck_assessment_ml_range"),
        CheckConstraint("graph_risk >= 0 AND graph_risk <= 1", name="ck_assessment_graph_range"),
        CheckConstraint("rule_risk >= 0 AND rule_risk <= 1", name="ck_assessment_rule_range"),
        CheckConstraint("final_risk >= 0 AND final_risk <= 1", name="ck_assessment_final_range"),
        Index("ix_assessments_decision_scored", "decision", "scored_at"),
        Index("ix_assessments_final_risk", "final_risk"),
    )

    assessment_id: Mapped[UUID] = mapped_column(default=uuid4, unique=True, index=True)
    return_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("return_requests.id", ondelete="RESTRICT"), index=True
    )
    model_version_id: Mapped[UUID] = mapped_column(ForeignKey("model_versions.id", ondelete="RESTRICT"))
    policy_version_id: Mapped[UUID] = mapped_column(ForeignKey("policy_versions.id", ondelete="RESTRICT"))
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    ml_probability: Mapped[float]
    graph_risk: Mapped[float]
    rule_risk: Mapped[float]
    final_risk: Mapped[float]
    decision: Mapped[RiskDecision] = mapped_column(portable_enum(RiskDecision))
    feature_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    explanation_source: Mapped[str] = mapped_column(String(40), default="deterministic")
    explanation_status: Mapped[str] = mapped_column(String(40), default="not_requested")
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    latency_ms: Mapped[int] = mapped_column(Integer)


class Case(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint("risk_assessment_id", name="uq_cases_assessment"),
        Index("ix_cases_merchant_status_priority_opened", "merchant_id", "status", "priority", "opened_at"),
    )

    case_id: Mapped[UUID] = mapped_column(default=uuid4, unique=True, index=True)
    risk_assessment_id: Mapped[UUID] = mapped_column(ForeignKey("risk_assessments.id", ondelete="RESTRICT"))
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"), index=True)
    status: Mapped[CaseStatus] = mapped_column(portable_enum(CaseStatus), default=CaseStatus.OPEN)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalystDecision(UUIDPrimaryKeyMixin, Base):
    """Append-only human workflow action; never a direct financial action."""

    __tablename__ = "analyst_decisions"
    __table_args__ = (Index("ix_analyst_decisions_case_created", "case_id", "created_at"),)

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="RESTRICT"), index=True)
    actor_id: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[AnalystAction] = mapped_column(portable_enum(AnalystAction))
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only event log; payloads must already be redacted by services."""

    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_audit_events_event_id"),
        Index("ix_audit_entity_occurred", "entity_type", "entity_id", "occurred_at"),
        Index("ix_audit_request", "request_id"),
        Index("ix_audit_correlation", "correlation_id"),
        Index("ix_audit_type_occurred", "event_type", "occurred_at"),
    )

    event_id: Mapped[UUID] = mapped_column(default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(80))
    actor_type: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
