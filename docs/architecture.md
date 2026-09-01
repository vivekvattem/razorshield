# RazorShield architecture

## Goals and boundaries

RazorShield is a merchant-facing decision-support system for coordinated refund
and return abuse. It is not a general fraud platform, payment processor, automated
rejection system, or source of offensive fraud simulations. Its outputs are
bounded interventions: `APPROVE`, `VERIFY`, and `MANUAL_REVIEW`.

The initial implementation is a modular monolith. This keeps transactions,
idempotency, auditability, and local reproducibility straightforward while
preserving clear extraction seams if individual workloads later need to scale.

## System context

```text
Merchant / analyst
       |
       v
React risk dashboard ---- centralized typed API client
       |
       v
FastAPI routes -- request validation / correlation ID / structured errors
       |
       v
Application services -- scoring, case workflow, metrics, policy simulation
       |                         |
       v                         v
Deterministic risk pipeline      Optional explanation adapter
  features -> ML -> graph          evidence in, summary/checklist out
  -> rules -> hybrid -> policy     unavailable => template fallback
       |
       v
Repositories / SQLAlchemy unit of work
       |
       v
PostgreSQL (production) / SQLite (fast tests where compatible)
```

Offline jobs generate the synthetic dataset, train/calibrate models, select policy
thresholds on validation data, evaluate once on held-out test data, and publish
versioned artifacts plus reports. Online services load those immutable artifacts;
they do not train models in request paths.

## Backend responsibilities

| Layer | Responsibility | Must not do |
|---|---|---|
| `api` | HTTP contracts, auth boundary, pagination, request IDs, error mapping | Business logic or direct SQL |
| `schemas` | Pydantic v2 request/response contracts | Persistence behaviour |
| `services` | Use cases and transaction orchestration | Framework-specific rendering |
| `repositories` | Query and persistence operations | Risk scoring or policy choices |
| `models` | SQLAlchemy persistence mappings | API serialization policy |
| `risk` | Point-in-time features, graph, rules, ML, hybrid score, policy, evaluation | HTTP or database session ownership |
| `core` | Configuration, logging, security, errors, request context | Domain workflows |
| `db` | Engine/session/unit-of-work wiring | Route behaviour |

The risk package will expose typed inputs and outputs so training and online
scoring share the same deterministic feature definitions. Model artifacts will
carry a feature schema hash and version; incompatible artifacts fail readiness
and return a safe service-unavailable scoring response rather than silently using
an untrained substitute. Rules and graph evidence may support explicitly designed
fallback behaviour, but no fallback will be represented as an ML probability.

## Planned API surface

The versioned application API will expose exactly the required core surface:

- liveness/readiness: `GET /health`, `GET /ready`;
- scoring: `POST /api/v1/returns/score` and
  `POST /api/v1/returns/batch-score`;
- case workflow: `GET /api/v1/cases`, `GET /api/v1/cases/{case_id}`,
  `POST /api/v1/cases/{case_id}/decision`,
  `GET /api/v1/cases/{case_id}/graph`, and
  `GET /api/v1/cases/{case_id}/audit`;
- evidence and governance: `GET /api/v1/metrics/model`,
  `GET /api/v1/metrics/business`, `POST /api/v1/policies/simulate`, and
  `GET /api/v1/model-card`.

List responses will use stable cursor or page/size pagination with documented
sorting and filters. Errors share a structured envelope containing a machine code,
safe message, details, and request/correlation ID. Authentication, if included,
will be enforced through route dependencies rather than business services.

## Online scoring sequence

1. Accept a score request with an `Idempotency-Key` and correlation ID.
2. Validate the API schema and normalize enums, tokens, currency, and UTC time.
3. Find or create the return request within a database transaction.
4. Construct point-in-time transaction, customer, temporal, and graph features.
5. Obtain the calibrated ML probability from the immutable model artifact.
6. Calculate deterministic graph risk and transparent rule risk.
7. Combine components using a versioned, validation-selected hybrid formula.
8. Apply a versioned cost-sensitive policy and review-capacity constraint.
9. Persist assessment, case (when intervention is needed), evidence, versions,
   and an audit event atomically.
10. Return the stored response. A repeated idempotency key with the same request
    fingerprint returns the original result; a different payload is a conflict.
11. Ask the optional explanation adapter to summarize only stored evidence. Its
    failure never changes the score, decision, or core response.

## Offline ML and data flow

```text
seeded generator -> immutable raw synthetic tables -> validation
 -> chronological/group-aware split manifest
 -> training-only preprocessing and point-in-time feature snapshots
 -> four baselines and calibration
 -> validation-only model/hybrid/threshold selection
 -> locked configuration
 -> exactly-once test evaluation
 -> versioned model, policy, metrics, model card
```

Raw synthetic event tables and split manifests are the reproducibility source.
Large generated CSV/Parquet and binary artifacts are ignored by default and
recreated by scripts. Small manifests, metadata, checksums, and reports may be
versioned.

## Graph design

The operational graph is heterogeneous and temporal:

- Customer nodes connect to tokenized device, payment, address, phone, and IP
  identity nodes through observations with `first_seen_at` and `last_seen_at`.
- Customer-to-customer projections are derived for graph features and display;
  edges retain shared identity types and recency-aware weights.
- For a return at time `t`, only identity observations and verified-abuse outcomes
  strictly available before `t` may contribute.
- Labels, `ring_id`, and `abuse_pattern` are generator/evaluation metadata and are
  never online graph attributes or model features.
- The analyst graph API returns a bounded component/subgraph, redacted token labels,
  evidence timestamps, and truncation metadata.

## Audit and safety invariants

- Every assessment records request/correlation IDs, inputs fingerprint, component
  scores, final score, decision, deterministic evidence, model version, policy
  version, and UTC timestamp.
- Assessment records are append-only in application behaviour. Analyst actions
  append decisions and audit events rather than rewriting risk history.
- Human actions are `APPROVE_CASE`, `DISMISS_CASE`, or `ESCALATE_CASE`; escalation
  remains a review workflow state, not an automatic customer penalty.
- Optional LLM input is limited to calculated evidence and neutral context. It
  cannot write any numerical risk field or decision field.
- Secrets come from environment variables. Logs redact identity tokens and never
  contain raw payment credentials.

## Deployment shape

Docker Compose will eventually run PostgreSQL, the FastAPI backend, and the Vite
frontend production image. Readiness will check database connectivity and model
artifact compatibility; liveness will not depend on optional explanations.
Production concerns such as TLS termination, managed secret storage, durable
backups, SSO/RBAC, rate limiting, monitoring, and data-retention enforcement are
deployment responsibilities and will be documented as limitations unless actually
implemented.

## Frontend composition

The React application will use a centralized typed API client and route-level
loading/error boundaries. Its pages are executive overview, case queue, case
detail, abuse-ring explorer, model performance, and policy simulator. Recharts
will render business/model charts and Cytoscape.js will render bounded interactive
identity subgraphs. All values come from backend APIs or seeded persistence—never
from frontend-only fabricated metrics.
