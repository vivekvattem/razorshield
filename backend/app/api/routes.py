from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import error_payload, request_id_for
from app.models import (
    AnalystDecision,
    AuditEvent,
    Case,
    IdentityLink,
    Merchant,
    ModelVersion,
    Order,
    PolicyVersion,
    ReturnRequest,
    RiskAssessment,
)
from app.models.enums import AnalystAction, CaseStatus, RiskDecision
from app.schemas.scoring import (
    AnalystDecisionRequest,
    AnalystFeedbackRequest,
    ExplanationResponse,
    FeedbackAnalyticsResponse,
    GraphResponse,
    ReturnScoreRequest,
    ThresholdAnalysisResponse,
)
from app.services.artifacts import ArtifactUnavailable
from app.services.intelligence import deterministic_explanation, feedback_analytics, uncertainty_indicator
from app.services.scoring import score

router = APIRouter()


def _case_payload(session, case: Case) -> dict[str, object]:
    assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.id == case.risk_assessment_id))
    returned = session.scalar(select(ReturnRequest).where(ReturnRequest.id == assessment.return_request_id))
    order = session.scalar(select(Order).where(Order.id == returned.order_id))
    merchant = session.scalar(select(Merchant).where(Merchant.id == case.merchant_id))
    return {
        "case_id": str(case.case_id),
        "status": case.status.value,
        "priority": case.priority,
        "opened_at": case.opened_at.isoformat(),
        "merchant_id": merchant.external_id,
        "return_id": returned.external_id,
        "order_value_paise": order.order_value_paise,
        "final_risk": assessment.final_risk,
        "decision": assessment.decision.value,
        "evidence_count": len(assessment.evidence_snapshot.get("rules", [])),
    }


@router.get("/", tags=["operational"])
def root(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {"service": settings.app_name, "version": settings.app_version, "docs_path": "/docs"}


@router.get("/health", tags=["operational"])
def health(verbose: bool = Query(default=False)) -> dict[str, str]:
    response = {"status": "ok"}
    if verbose:
        response["service"] = "razorshield"
    return response


@router.get("/ready", response_model=None, tags=["operational"])
def ready(request: Request) -> dict[str, str] | JSONResponse:
    database = "available"
    model = "available"
    try:
        request.app.state.database.ping()
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content=error_payload(
                "database_unavailable",
                "Database connectivity check failed",
                request_id_for(request),
            ),
        )
    try:
        request.app.state.artifacts.load()
    except ArtifactUnavailable:
        model = "unavailable"
    body = {
        "status": "ready" if database == model == "available" else "not_ready",
        "database": database,
        "model": model,
    }
    return JSONResponse(status_code=200 if body["status"] == "ready" else 503, content=body)


@router.post("/api/v1/returns/score", response_model=None)
def score_return(request: Request, payload: ReturnScoreRequest, idempotency_key: str | None = Header(default=None)):
    if not idempotency_key:
        return JSONResponse(
            status_code=400,
            content=error_payload("idempotency_key_required", "Idempotency-Key is required", request_id_for(request)),
        )
    try:
        with request.app.state.database.transaction() as session:
            body = score(session, payload, idempotency_key, request_id_for(request), request.app.state.artifacts)
        body["request_id"] = request_id_for(request)
        return body
    except ArtifactUnavailable as exc:
        return JSONResponse(
            status_code=503, content=error_payload("model_unavailable", str(exc), request_id_for(request))
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=409,
            content=error_payload(str(exc), "Idempotency key payload conflict", request_id_for(request)),
        )


@router.post("/api/v1/returns/batch-score")
def batch_score(
    request: Request, payloads: list[dict[str, object]], idempotency_key: str | None = Header(default=None)
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for index, raw_payload in enumerate(payloads):
        key = f"{idempotency_key or request_id_for(request)}:{index}"
        try:
            payload = ReturnScoreRequest.model_validate(raw_payload)
            with request.app.state.database.transaction() as session:
                results.append(
                    {
                        "index": index,
                        "ok": True,
                        "result": score(session, payload, key, request_id_for(request), request.app.state.artifacts),
                    }
                )
        except (ArtifactUnavailable, ValidationError, ValueError) as exc:
            results.append({"index": index, "ok": False, "error": str(exc)})
        except Exception:
            # Each item owns its transaction; do not let an unexpected item failure
            # discard independent batch results or expose internals to callers.
            results.append({"index": index, "ok": False, "error": "scoring_failed"})
    return {"request_id": request_id_for(request), "results": results}


@router.get("/api/v1/cases")
def list_cases(
    merchant_id: str | None = None,
    status: CaseStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    request: Request = None,
) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        statement = select(Case).join(Merchant, Merchant.id == Case.merchant_id)
        if merchant_id:
            statement = statement.where(Merchant.external_id == merchant_id)
        if status:
            statement = statement.where(Case.status == status)
        total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = session.scalars(
            statement.order_by(Case.priority.desc(), Case.opened_at.desc()).offset((page - 1) * size).limit(size)
        ).all()
        return {"items": [_case_payload(session, row) for row in rows], "page": page, "size": size, "total": total}


def _get_case(session, case_id: str) -> Case:
    try:
        parsed_case_id = UUID(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
    case = session.scalar(select(Case).where(Case.case_id == parsed_case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/api/v1/cases/{case_id}")
def get_case(case_id: str, request: Request) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        case = _get_case(session, case_id)
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.id == case.risk_assessment_id))
        model_version = session.scalar(select(ModelVersion).where(ModelVersion.id == assessment.model_version_id))
        policy_version = session.scalar(select(PolicyVersion).where(PolicyVersion.id == assessment.policy_version_id))
        return {
            **_case_payload(session, case),
            "assessment": {
                "decision": assessment.decision.value,
                "final_risk": assessment.final_risk,
                "ml_probability": assessment.ml_probability,
                "graph_risk": assessment.graph_risk,
                "rule_risk": assessment.rule_risk,
                "evidence": assessment.evidence_snapshot,
                "model_version": model_version.version,
                "policy_version": policy_version.version,
                "explanation": deterministic_explanation(
                    assessment,
                    (policy_version.ml_weight, policy_version.graph_weight, policy_version.rule_weight),
                    model_version.version,
                    policy_version.version,
                ),
                "uncertainty": uncertainty_indicator(
                    assessment, policy_version.approve_max, policy_version.manual_review_min
                ),
            },
        }


@router.get("/api/v1/cases/{case_id}/explanation", response_model=ExplanationResponse)
def case_explanation(case_id: str, request: Request) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        case = _get_case(session, case_id)
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.id == case.risk_assessment_id))
        policy = session.scalar(select(PolicyVersion).where(PolicyVersion.id == assessment.policy_version_id))
        model = session.scalar(select(ModelVersion).where(ModelVersion.id == assessment.model_version_id))
        return deterministic_explanation(
            assessment, (policy.ml_weight, policy.graph_weight, policy.rule_weight), model.version, policy.version
        )


@router.post("/api/v1/cases/{case_id}/decision")
def decide_case(case_id: str, payload: AnalystDecisionRequest, request: Request) -> dict[str, object]:
    statuses = {
        "APPROVE_CASE": CaseStatus.APPROVED,
        "DISMISS_CASE": CaseStatus.DISMISSED,
        "ESCALATE_CASE": CaseStatus.ESCALATED,
    }
    with request.app.state.database.transaction() as session:
        case = _get_case(session, case_id)
        action = AnalystAction(payload.action)
        case.status, case.resolved_at = statuses[payload.action], datetime.now(UTC)
        session.add(
            AnalystDecision(
                case_id=case.id,
                actor_id=request.headers.get("X-Analyst-Id", "analyst"),
                action=action,
                rationale=payload.rationale,
            )
        )
        session.add(
            AuditEvent(
                entity_type="case",
                entity_id=str(case.case_id),
                event_type="ANALYST_DECISION",
                actor_type="analyst",
                request_id=request_id_for(request),
                payload_json={"action": payload.action},
            )
        )
        return _case_payload(session, case)


@router.get("/api/v1/cases/{case_id}/audit")
def case_audit(case_id: str, request: Request) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        _get_case(session, case_id)
        events = session.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == case_id).order_by(AuditEvent.occurred_at)
        ).all()
        return {
            "items": [
                {
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at.isoformat(),
                    "payload": event.payload_json,
                }
                for event in events
            ]
        }


@router.post("/api/v1/cases/{case_id}/feedback")
def case_feedback(case_id: str, payload: AnalystFeedbackRequest, request: Request) -> dict[str, str]:
    """Append a human disposition without changing the original assessment."""
    with request.app.state.database.transaction() as session:
        case = _get_case(session, case_id)
        session.add(
            AuditEvent(
                entity_type="case",
                entity_id=str(case.case_id),
                event_type="ANALYST_FEEDBACK",
                actor_type="analyst",
                actor_id=request.headers.get("X-Analyst-Id", "analyst"),
                request_id=request_id_for(request),
                payload_json={"disposition": payload.disposition, "note": payload.note or ""},
            )
        )
    return {"status": "recorded", "disposition": payload.disposition}


@router.get("/api/v1/cases/{case_id}/export")
def export_case(case_id: str, request: Request) -> dict[str, object]:
    """Safe evidence export: graph summaries and audit records exclude raw tokens."""
    with request.app.state.database.transaction() as session:
        _get_case(session, case_id)
        detail = get_case(case_id, request)
        audit = case_audit(case_id, request)
        graph = case_graph(case_id, request)
        return {
            "synthetic_demo": True,
            "exported_at": datetime.now(UTC).isoformat(),
            "case": detail,
            "masked_graph": graph,
            "audit": audit["items"],
        }


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.get("/api/v1/cases/{case_id}/graph", response_model=GraphResponse)
def case_graph(case_id: str, request: Request) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        case = _get_case(session, case_id)
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.id == case.risk_assessment_id))
        returned = session.scalar(select(ReturnRequest).where(ReturnRequest.id == assessment.return_request_id))
        event_time = _as_utc(returned.event_time)
        origin_links = session.scalars(
            select(IdentityLink).where(
                IdentityLink.customer_id == returned.customer_id,
                IdentityLink.merchant_id == case.merchant_id,
                IdentityLink.first_seen_at <= event_time,
            )
        ).all()
        tokens = {(link.identity_type, link.token_hash) for link in origin_links}
        linked_identity_rows: list[IdentityLink] = []
        for identity_type, token_hash in sorted(tokens, key=lambda item: (item[0].value, item[1])):
            linked_identity_rows.extend(
                session.scalars(
                    select(IdentityLink).where(
                        IdentityLink.merchant_id == case.merchant_id,
                        IdentityLink.identity_type == identity_type,
                        IdentityLink.token_hash == token_hash,
                        IdentityLink.first_seen_at <= event_time,
                    )
                ).all()
            )
        customer_ids = sorted({returned.customer_id, *(row.customer_id for row in linked_identity_rows)}, key=str)[:40]
        account_ids = {customer_id: f"linked-account-{index + 1}" for index, customer_id in enumerate(customer_ids)}
        linked_cases = session.execute(
            select(Case, RiskAssessment, ReturnRequest, Order)
            .join(RiskAssessment, RiskAssessment.id == Case.risk_assessment_id)
            .join(ReturnRequest, ReturnRequest.id == RiskAssessment.return_request_id)
            .join(Order, Order.id == ReturnRequest.order_id)
            .where(
                Case.merchant_id == case.merchant_id,
                ReturnRequest.customer_id.in_(customer_ids),
                ReturnRequest.event_time <= event_time,
            )
            .order_by(RiskAssessment.final_risk.desc())
            .limit(50)
        ).all()
        case_by_customer: dict[object, tuple[Case, RiskAssessment]] = {}
        for linked_case, linked_assessment, linked_return, _ in linked_cases:
            case_by_customer.setdefault(linked_return.customer_id, (linked_case, linked_assessment))
        nodes: list[dict[str, object]] = [{"id": "case", "type": "case", "label": "Current case"}]
        edges: list[dict[str, str]] = []
        for customer_id, account_id in account_ids.items():
            linked = case_by_customer.get(customer_id)
            node: dict[str, object] = {
                "id": account_id,
                "type": "customer",
                "label": account_id.replace("-", " ").title(),
            }
            if linked:
                node["case_id"] = str(linked[0].case_id)
                node["risk"] = linked[1].final_risk
            nodes.append(node)
        identity_nodes: dict[tuple[object, str], str] = {}
        for row in linked_identity_rows:
            if row.customer_id not in account_ids:
                continue
            key = (row.identity_type, row.token_hash)
            if key not in identity_nodes:
                identity_id = f"masked-{row.identity_type.value.lower()}-{len(identity_nodes) + 1}"
                identity_nodes[key] = identity_id
                nodes.append(
                    {
                        "id": identity_id,
                        "type": row.identity_type.value.lower(),
                        "label": f"Shared {row.identity_type.value.lower()}",
                    }
                )
            edges.append(
                {
                    "source": account_ids[row.customer_id],
                    "target": identity_nodes[key],
                    "type": row.identity_type.value.lower(),
                }
            )
        nodes = nodes[:50]
        allowed_node_ids = {str(node["id"]) for node in nodes}
        edges = [edge for edge in edges if edge["source"] in allowed_node_ids and edge["target"] in allowed_node_ids][
            :100
        ]
        connection_types = sorted({edge["type"] for edge in edges})
        risks = [linked_assessment.final_risk for _, linked_assessment, _, _ in linked_cases]
        highest = linked_cases[0] if linked_cases else None
        timestamps = [row.first_seen_at for row in linked_identity_rows] + [
            min(_as_utc(row.last_seen_at), event_time) for row in linked_identity_rows
        ]
        timestamps = [_as_utc(value) for value in timestamps]
        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "degree": assessment.feature_snapshot.get("degree", 0),
                "component_size": len(customer_ids),
                "linked_account_count": max(0, len(customer_ids) - 1),
                "shared_connection_count": len(edges),
                "identity_types": len(connection_types),
                "connection_types": connection_types,
                "total_connected_return_value_paise": sum(row[3].order_value_paise for row in linked_cases),
                "highest_risk_linked_case": (
                    {"case_id": str(highest[0].case_id), "risk": highest[1].final_risk} if highest else None
                ),
                "first_seen_at": min(timestamps).isoformat() if timestamps else None,
                "last_seen_at": max(timestamps).isoformat() if timestamps else None,
                "risk_distribution": {
                    "low": sum(risk < 0.1 for risk in risks),
                    "medium": sum(0.1 <= risk < 0.2 for risk in risks),
                    "high": sum(risk >= 0.2 for risk in risks),
                },
            },
            "bounded": {"max_nodes": 50, "max_edges": 100, "hop_depth": 1},
        }


@router.get("/api/v1/metrics/model")
def model_metrics(request: Request) -> dict[str, object]:
    artifact = request.app.state.artifacts.load()
    return {
        "model_version": artifact.metadata["model_version"],
        "evaluation": artifact.evaluation,
        "synthetic_only": True,
    }


@router.get("/api/v1/metrics/business")
def business_metrics(request: Request) -> dict[str, object]:
    artifact = request.app.state.artifacts.load()
    test_metrics = artifact.evaluation["test_metrics"]
    with request.app.state.database.transaction() as session:
        decision_counts = {
            decision.value: session.scalar(
                select(func.count()).select_from(RiskAssessment).where(RiskAssessment.decision == decision)
            )
            or 0
            for decision in RiskDecision
        }
    return {
        "policy_version": artifact.evaluation["policy_version"],
        "business": {
            key: test_metrics[key]
            for key in (
                "estimated_prevented_loss_paise",
                "net_estimated_savings_paise",
                "false_positive_cost_paise",
                "false_positives_per_1000_legitimate",
            )
        },
        "live": {"assessments": sum(decision_counts.values()), "decision_counts": decision_counts},
        "synthetic_only": True,
    }


@router.get("/api/v1/metrics/feedback", response_model=FeedbackAnalyticsResponse)
def feedback_metrics(request: Request) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        return feedback_analytics(session)


@router.get("/api/v1/metrics/thresholds", response_model=ThresholdAnalysisResponse)
def threshold_metrics(request: Request) -> dict[str, object]:
    """Expose immutable artifact analytics; unavailable values remain null."""
    artifact = request.app.state.artifacts.load()
    policy = artifact.metadata["policy"]
    metrics = artifact.evaluation["test_metrics"]
    rates = metrics["decision_rates"]
    rows = [
        {
            "label": "Validation-selected policy",
            "source": "validation",
            "policy_version": artifact.evaluation["policy_version"],
            "verify_threshold": policy["verify_threshold"],
            "manual_review_threshold": policy["review_threshold"],
            "net_estimated_savings_paise": policy.get("validation_net_savings_paise"),
            "note": "Thresholds selected on validation data; other row metrics were not persisted.",
        },
        {
            "label": "Locked held-out report",
            "source": "locked_test",
            "policy_version": artifact.evaluation["policy_version"],
            "verify_threshold": policy["verify_threshold"],
            "manual_review_threshold": policy["review_threshold"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "false_positives_per_1000_legitimate": metrics["false_positives_per_1000_legitimate"],
            "verification_rate": rates.get("VERIFY"),
            "manual_review_rate": rates.get("MANUAL_REVIEW"),
            "estimated_prevented_loss_paise": metrics["estimated_prevented_loss_paise"],
            "false_positive_cost_paise": metrics["false_positive_cost_paise"],
            "net_estimated_savings_paise": metrics["net_estimated_savings_paise"],
            "note": "Reported exactly once on the untouched synthetic test split.",
        },
        {
            "label": "Operational demo policy",
            "source": "operational",
            "policy_version": "operational-demo-v2",
            "verify_threshold": 0.1,
            "manual_review_threshold": 0.2,
            "note": "Validation-derived demo guardrails; no held-out performance claim is available.",
        },
    ]
    return {
        "rows": rows,
        "read_only": True,
        "synthetic_only": True,
        "disclosure": artifact.evaluation["disclosure"],
    }


@router.get("/api/v1/model-card")
def model_card(request: Request) -> dict[str, object]:
    artifact = request.app.state.artifacts.load()
    return {
        "model_version": artifact.metadata["model_version"],
        "feature_allowlist": artifact.evaluation["feature_allowlist"],
        "disclosure": (
            "Synthetic held-out performance demonstrates the evaluation pipeline "
            "and is not a claim of production accuracy."
        ),
    }
