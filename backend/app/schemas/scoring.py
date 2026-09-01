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
