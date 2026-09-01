from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import error_payload, request_id_for
from app.models import AnalystDecision, AuditEvent, Case, Merchant, Order, ReturnRequest, RiskAssessment
from app.models.enums import AnalystAction, CaseStatus
from app.schemas.scoring import AnalystDecisionRequest, AnalystFeedbackRequest, ReturnScoreRequest
from app.services.artifacts import ArtifactUnavailable
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
    case = session.scalar(select(Case).where(Case.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/api/v1/cases/{case_id}")
def get_case(case_id: str, request: Request) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        case = _get_case(session, case_id)
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.id == case.risk_assessment_id))
        return {
            **_case_payload(session, case),
            "assessment": {
                "decision": assessment.decision.value,
                "final_risk": assessment.final_risk,
                "ml_probability": assessment.ml_probability,
                "graph_risk": assessment.graph_risk,
                "rule_risk": assessment.rule_risk,
                "evidence": assessment.evidence_snapshot,
                "model_version": assessment.model_version_id,
                "policy_version": assessment.policy_version_id,
            },
        }


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


@router.get("/api/v1/cases/{case_id}/graph")
def case_graph(case_id: str, request: Request) -> dict[str, object]:
    with request.app.state.database.transaction() as session:
        case = _get_case(session, case_id)
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.id == case.risk_assessment_id))
        return {
            "nodes": [{"id": "case", "type": "case"}],
            "edges": [],
            "statistics": {
                "degree": assessment.feature_snapshot.get("degree", 0),
                "component_size": assessment.feature_snapshot.get("component_size", 1),
            },
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
    return {
        "policy_version": artifact.evaluation["policy_version"],
        "business": artifact.evaluation.get("business", {}),
        "synthetic_only": True,
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
