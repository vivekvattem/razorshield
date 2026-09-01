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
