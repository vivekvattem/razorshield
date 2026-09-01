from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import error_payload, request_id_for
from app.models import AnalystDecision, AuditEvent, Case, Merchant, RiskAssessment
from app.models.enums import AnalystAction, CaseStatus
from app.schemas.scoring import AnalystDecisionRequest, ReturnScoreRequest
from app.services.artifacts import ArtifactUnavailable
from app.services.scoring import score

router = APIRouter()


def _case_payload(case: Case) -> dict[str, object]:
    return {
        "case_id": str(case.case_id),
        "status": case.status.value,
        "priority": case.priority,
        "opened_at": case.opened_at.isoformat(),
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
        return {"items": [_case_payload(row) for row in rows], "page": page, "size": size, "total": total}


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
            **_case_payload(case),
            "assessment": {
                "decision": assessment.decision.value,
                "final_risk": assessment.final_risk,
                "evidence": assessment.evidence_snapshot,
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
        return _case_payload(case)


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
