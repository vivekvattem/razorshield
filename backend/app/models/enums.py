from __future__ import annotations

from enum import Enum


class MerchantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ReturnStatus(str, Enum):
    RECEIVED = "RECEIVED"
    SCORED = "SCORED"


class IdentityType(str, Enum):
    DEVICE = "DEVICE"
    PAYMENT = "PAYMENT"
    ADDRESS = "ADDRESS"
    PHONE = "PHONE"
    IP = "IP"


class VersionStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class RiskDecision(str, Enum):
    APPROVE = "APPROVE"
    VERIFY = "VERIFY"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    DISMISSED = "DISMISSED"
    ESCALATED = "ESCALATED"


class AnalystAction(str, Enum):
    APPROVE_CASE = "APPROVE_CASE"
    DISMISS_CASE = "DISMISS_CASE"
    ESCALATE_CASE = "ESCALATE_CASE"
