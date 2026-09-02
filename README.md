# RazorShield

## Reproducible local demo

Use Python 3.11 and Node 20+ from the repository root:

```bash
make setup
make bootstrap
make backend   # terminal 1
make frontend  # terminal 2
make test
```

`make bootstrap` deterministically generates data, trains the artifact with the
same pinned scikit-learn runtime, migrates the database, idempotently seeds the
three demo outcomes, and runs a strict environment/artifact/database preflight.
If preflight reports stale SQLite demo outcomes, preserve `backend/razorshield.db`
as a backup and bootstrap a fresh local database.

## Approved problem statement

“Merchants typically assess returns individually, allowing coordinated refund-abuse rings to hide across multiple accounts sharing devices, payment instruments and addresses. Transaction-only systems miss this network context, while aggressive fraud rules create false positives and delay legitimate refunds.”

## Approved solution statement

“RazorShield combines calibrated machine learning, point-in-time customer behaviour, identity-graph intelligence and transparent rules to detect coordinated abuse. It routes every return to APPROVE, VERIFY or MANUAL REVIEW with explainable evidence, measured false-positive cost and a complete audit trail.”

RazorShield is a defense-only risk-operations application for detecting coordinated
refund and return abuse. It connects fragmented customer identities and return
behaviour so merchants can identify suspicious networks that transaction-only
models miss, while minimizing friction for legitimate customers.

> Current status: Phase 0 architecture and project skeleton only. No detector,
> API, user interface, generated dataset, trained model, or performance result is
> implemented yet.

## Safety boundary

RazorShield is scoped only to coordinated refund and return abuse. It will produce
only `APPROVE`, `VERIFY`, or `MANUAL_REVIEW`; an adverse final action always
requires a human. Numerical scoring will remain deterministic and independent of
any language model. Payment identities will be synthetic or tokenized, never raw
card data or CVVs.

## Planned architecture

The backend will use FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, and a
SQLite-compatible test configuration. The risk pipeline will use pandas, NumPy,
scikit-learn, and NetworkX. The frontend will use React, Vite, TypeScript,
Recharts, and Cytoscape.js. See [the architecture](docs/architecture.md) for
component boundaries and data flow.

## Phase 0 contracts

- [Assumptions and risks](docs/assumptions-and-risks.md)
- [Database schema plan](docs/database-schema-plan.md)
- [Dataset schema plan](docs/dataset-schema-plan.md)
- [Evaluation contract](docs/evaluation-contract.md)
- [Delivery plan](docs/delivery-plan.md)
- [Current and planned repository structure](docs/repository-structure.md)

Setup, data generation, training, test, Docker, API, demo, and metric instructions
will be added in the phases in which those capabilities become executable. No
commands or results are claimed before then.

## Phase 1 backend setup

Python 3.11 is required. From the repository root:

```bash
make setup
make test
make lint
make migrate
make run
```

The service exposes `GET /health` for process liveness and `GET /ready` for
database readiness. The latter deliberately reports `model: not_configured` until
the model-training phase.

For PostgreSQL via Docker Compose:

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
curl http://localhost:8000/health
curl http://localhost:8000/ready
docker compose down
```

Copy `.env.example` to `.env` only for local overrides; do not commit it. The
application never creates tables at startup—apply schema changes through Alembic.

## Phase 2 synthetic data

Generate and validate the deterministic default dataset (compressed CSV under the
ignored `data/generated/default` directory) with:

```bash
make data-generate
make data-validate
```

`data/schema.json`, `data/model-feature-allowlist.json`, and `data/manifest.json`
record the dataset contract, prohibited model fields, seed, split boundaries, and
checksums. The generator contains no model fitting or threshold selection.

## Offline detector evaluation

```bash
make features
make train
```

This writes versioned, checksummed model/policy/evaluation artifacts to the ignored
`artifacts/generated/offline-hgb-v1` directory. Validation selects the hybrid policy;
the held-out test set is evaluated only after those choices are locked.

## Phase 5 demo workflow

Run `make migrate` then `make demo-seed` to create the deterministic bounded demo journeys.
`validation-policy-v1` remains the locked evaluation policy; serving uses the separately
versioned, validation-derived capacity-guardrail policy `operational-demo-v2` and never
uses held-out labels to choose thresholds.

## Deployment (Render + Vercel)

Render: create a Blueprint from this repository; `render.yaml` provisions the API and
PostgreSQL. Set `CORS_ORIGINS` to the exact Vercel HTTPS origin (a JSON array), and keep
the generated `SECRET_KEY` private. The container deterministically generates and verifies
the model artifact at build time, then runs Alembic and the idempotent demo seed before
binding Render's `PORT`. Use `/health` for liveness and `/ready` for database/model readiness.

Vercel: import the same repository with root directory `frontend`, set
`VITE_API_BASE_URL` to the Render API HTTPS URL, and deploy. `vercel.json` preserves SPA
routes on refresh. Roll back by redeploying a prior Git commit; database migrations are
forward-only, so take a managed PostgreSQL backup before schema-changing releases.

## Explainable network intelligence

Case responses and `GET /api/v1/cases/{case_id}/explanation` expose a deterministic,
non-causal explanation from the stored point-in-time feature snapshot. Factors are
ordered by normalized documented threshold strength; hybrid contributions are exactly
`ML probability × 0.70`, `graph risk × 0.20`, and `rule risk × 0.10` for the versioned
policy. No SHAP or LLM attribution is implied.

The case graph is a bounded (50 nodes, 100 edges), merchant-scoped one-hop view using
identity observations no later than the return timestamp. Only masked identifiers leave
the API. `GET /api/v1/metrics/thresholds` presents immutable validation, locked-test and
operational-demo policies; missing persisted metrics are `null`, never reconstructed from
test labels. `GET /api/v1/metrics/feedback` uses the latest append-only feedback per case.
Agreement means confirmed abuse on a flagged case or legitimate feedback on an approved
case; insufficient evidence is excluded.

Data sufficiency is explicitly heuristic, not statistical confidence: fewer than three
prior 90-day orders with no linked account is `INSUFFICIENT_HISTORY`; a score within 0.05
of either operational threshold is `BORDERLINE`; otherwise it is `HIGH_CONFIDENCE`.
These signals support human review only and never produce automatic rejection or
retraining. All reported performance remains synthetic.
