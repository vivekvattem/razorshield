# RazorShield

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
