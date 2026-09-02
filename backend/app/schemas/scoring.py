from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReturnScoreRequest(BaseModel):
    merchant_id: str = Field(min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    order_id: str = Field(min_length=1, max_length=64)
    return_id: str = Field(min_length=1, max_length=64)
    event_time: datetime
    order_value_paise: int = Field(ge=0)
    product_category: str
    reason_code: str
    discount_percentage: float = Field(ge=0, le=100)
    hours_from_delivery_to_return: float = Field(ge=0)
    account_age_days: float = Field(ge=0)
    identity_tokens: dict[str, str] = Field(default_factory=dict)


class AnalystDecisionRequest(BaseModel):
    action: Literal["APPROVE_CASE", "DISMISS_CASE", "ESCALATE_CASE"]
    rationale: str | None = Field(default=None, max_length=2000)


class AnalystFeedbackRequest(BaseModel):
    disposition: Literal["CONFIRMED_ABUSE", "LEGITIMATE_RETURN", "INSUFFICIENT_EVIDENCE"]
    note: str | None = Field(default=None, max_length=2000)


class ExplanationFactor(BaseModel):
    feature: str
    value: float
    direction: Literal["increases_risk", "reduces_risk"]
    strength: float = Field(ge=0, le=1)
    evidence: str


class SignalContributions(BaseModel):
    model: float = Field(ge=0, le=1)
    network: float = Field(ge=0, le=1)
    rules: float = Field(ge=0, le=1)


class ExplanationResponse(BaseModel):
    method: Literal["deterministic_signal_explanation_not_shap"]
    explanation_version: str
    model_version: str
    policy_version: str
    top_increasing_factors: list[ExplanationFactor]
    top_reducing_factors: list[ExplanationFactor]
    signal_contributions: SignalContributions
    summary: str
    human_review_notice: str


class UncertaintyResponse(BaseModel):
    state: Literal["HIGH_CONFIDENCE", "BORDERLINE", "INSUFFICIENT_HISTORY"]
    reason: str
    method: Literal["heuristic_not_statistical_confidence"]
    version: str


class FeedbackAnalyticsResponse(BaseModel):
    confirmed_abuse_count: int = Field(ge=0)
    legitimate_return_count: int = Field(ge=0)
    insufficient_evidence_count: int = Field(ge=0)
    total_labelled_cases: int = Field(ge=0)
    analyst_model_agreement_rate: float | None = Field(default=None, ge=0, le=1)
    agreement_denominator: int = Field(ge=0)
    potential_false_positive_count: int = Field(ge=0)
    feedback_coverage_percentage: float = Field(ge=0, le=100)
    definition: str
    automatic_retraining: Literal[False]
    generated_at: datetime


class ThresholdAnalysisRow(BaseModel):
    label: str
    source: Literal["validation", "locked_test", "operational"]
    policy_version: str
    verify_threshold: float = Field(ge=0, le=1)
    manual_review_threshold: float = Field(ge=0, le=1)
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    false_positives_per_1000_legitimate: float | None = None
    verification_rate: float | None = None
    manual_review_rate: float | None = None
    estimated_prevented_loss_paise: int | float | None = None
    false_positive_cost_paise: int | float | None = None
    net_estimated_savings_paise: int | float | None = None
    note: str


class ThresholdAnalysisResponse(BaseModel):
    rows: list[ThresholdAnalysisRow]
    read_only: Literal[True]
    synthetic_only: Literal[True]
    disclosure: str


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    case_id: str | None = None
    risk: float | None = Field(default=None, ge=0, le=1)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str


class GraphStatistics(BaseModel):
    degree: int | float
    component_size: int
    linked_account_count: int
    shared_connection_count: int
    identity_types: int
    connection_types: list[str]
    total_connected_return_value_paise: int
    highest_risk_linked_case: dict[str, str | float] | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    risk_distribution: dict[str, int]


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    statistics: GraphStatistics
    bounded: dict[str, int]
