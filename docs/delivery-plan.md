# Phase-by-phase delivery plan

Each phase ends with an exact file/change summary, commands, honest test results,
remaining risks, and an approval gate. Work in a later phase does not begin before
approval.

## Phase 0 — architecture and skeleton

Inspect the workspace/toolchain; record assumptions; define component boundaries,
database and dataset plans, leakage/evaluation contract, delivery gates, and an
intentionally non-executable monorepo skeleton.

Exit criteria: documents are internally consistent, required directories exist,
no prior implementation was reused, and no Phase 1 code was started.

## Phase 1 — backend foundation

Create Python packaging/dependencies, typed settings, FastAPI app, request/error
middleware, SQLAlchemy session/unit-of-work, all initial persistence models,
Alembic migration, health/readiness endpoints, container foundation, and tests.

Exit criteria: migrations apply to clean PostgreSQL and SQLite test databases;
health tests, configuration tests, schema constraints, and baseline quality checks
pass.

## Phase 2 — deterministic synthetic data

Implement configurable seeded entity/event generation, at least 25 coordinated
rings, overlapping legitimate behaviour and label noise; emit manifests and seed
the demo persistence layer. Complete the data dictionary and leakage/split tests.

Exit criteria: scale minimums and realistic imbalance hold, reproducibility and
referential integrity pass, and no forbidden label metadata reaches features.

## Phase 3 — features, temporal graph, and rules

Implement shared point-in-time feature contracts, transaction/customer/temporal
features, temporal heterogeneous graph and projections, graph features, transparent
rules/evidence, and extensive boundary fixtures.

Exit criteria: future perturbations do not affect historical features; graph and
rule calculations are deterministic and explainable.

## Phase 4 — modelling, calibration, policy, evaluation

Train four required baselines, perform leakage-safe preprocessing/calibration,
select the primary model/hybrid weights/thresholds with validation only, run the
locked test evaluation once, serialize versioned artifacts, and complete the model
card/evaluation report.

Exit criteria: artifacts reproduce from scripts, all required honest metrics and
costs are reported with the synthetic disclaimer, and the test set did not guide
selection.

## Phase 5 — scoring and workflow APIs

Implement score/batch score, cases, detail/graph/audit, analyst decisions, model
and business metrics, policy simulation, model card, idempotency, persistence,
pagination/filtering, structured failures, and API/service tests.

Exit criteria: complete required journey persists atomically; duplicate, malformed,
partial-batch, unavailable-model, and audit cases are tested.

## Phase 6 — analyst dashboard

Build responsive overview, queue, case detail, graph explorer, performance, and
policy simulator pages through a centralized typed API client. Add accessible
loading, empty, and error states and use seeded backend data.

Exit criteria: TypeScript check and production build pass; the UI remains usable
when APIs fail; critical interactions work against the seeded backend.

## Phase 7 — bounded explanations and graceful failure

Implement deterministic evidence summaries/checklists and an optional narrowly
scoped explanation provider. Demonstrate provider unavailability with fallback.

Exit criteria: provider output cannot modify score/decision/evidence; outage tests
prove the primary workflow continues safely.

## Phase 8 — integration and submission hardening

Complete Compose, Docker images, environment example, Makefile, full documentation,
three memorable demo cases, security review, full backend/frontend/integration
checks, demo script, and submission checklist.

Exit criteria: a new developer can reproduce the demo from documented commands;
all results and limitations are honest; placeholders remain only for links or
screenshots the user must supply.

