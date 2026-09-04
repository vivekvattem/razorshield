# RazorShield

RazorShield is a defense-only AI risk manager for coordinated refund and return abuse.

**Problem:** Merchants typically assess returns individually, allowing coordinated refund-abuse rings to hide across multiple accounts sharing devices, payment instruments and addresses. Transaction-only systems miss this network context, while aggressive fraud rules create false positives and delay legitimate refunds.

**Solution:** RazorShield combines calibrated machine learning, point-in-time customer behaviour, identity-graph intelligence and transparent rules to detect coordinated abuse. It routes every return to APPROVE, VERIFY or MANUAL REVIEW with explainable evidence, measured false-positive cost and a complete audit trail.

## Architecture

The React/Vite operations dashboard calls a typed FastAPI API. HTTP routes delegate to transactional services and SQLAlchemy persistence backed by PostgreSQL in production (SQLite for local tests). The risk service loads one checksummed artifact, builds point-in-time transaction, behavioural, temporal and bounded one-hop graph features, then combines calibrated ML, graph and rule signals through a versioned policy. Alembic owns schema changes; analyst decisions and feedback are append-only audit events.

## Reproducible local demo

Prerequisites: Python 3.11 and Node.js 20+.

```bash
make setup
make bootstrap
make backend   # terminal 1: http://127.0.0.1:8000
make frontend  # terminal 2: http://127.0.0.1:5173
```

`make bootstrap` deterministically generates and validates synthetic data, trains and checksums the artifact with pinned scikit-learn 1.6.1, applies migrations, seeds the demo idempotently and runs preflight. Use `make test`, `make lint`, and `make migration-check` for verification. API documentation is at `http://127.0.0.1:8000/docs`.

Demo journeys produce real scoring outcomes:

- Established legitimate return → `APPROVE`
- High-velocity individual return → `VERIFY`
- Multi-account linked network → `MANUAL_REVIEW`

Open `/risk-center`, inspect the coordinated case and network, record analyst feedback, then export its masked evidence JSON. Explanations are deterministic; the primary detector has no LLM dependency.

## Locked synthetic evaluation

| Metric | Result |
| --- | ---: |
| Precision | 18.37% |
| Recall | 64.29% |
| F1 | 28.57% |
| PR-AUC | 16.57% |
| ROC-AUC | 84.20% |
| Brier score | 0.0649 |
| False positives / 1,000 legitimate returns | 153.85 |
| Verification / manual-review rate | 17.88% / 0.00% |
| Estimated prevented loss | ₹27,261.66 |
| Verification cost | ₹2,205.00 |
| False-positive cost | ₹8,400.00 |
| Net estimated savings | ₹16,656.66 |

Precision is approximately **2.35×** the dataset’s 7.83% abuse prevalence. This is lift within a synthetic held-out evaluation, not a production accuracy claim. Prevented loss and savings are estimates under documented synthetic cost assumptions; false-positive cost shows why human review and conservative interventions remain necessary.

> Synthetic held-out performance demonstrates the evaluation pipeline and is not a claim of production accuracy.

## Explainability and safety

Explanations use only the stored point-in-time feature snapshot. Factors are ranked by documented deterministic threshold strength; contributions are exactly ML probability × 0.70, graph risk × 0.20 and rule risk × 0.10. They are not SHAP, causal proof or an LLM justification. Graph responses are merchant-scoped, one-hop, bounded to 50 nodes and 100 edges, and expose masked identifiers only.

RazorShield covers coordinated refund/return abuse only. It never automatically rejects, accuses or financially penalizes a customer. Allowed recommendations are `APPROVE`, `VERIFY` and `MANUAL_REVIEW`; adverse action requires a human. Raw card data, CVVs and personal information are out of scope. Feedback does not automatically retrain or alter assessments.

## Render deployment

Create a Blueprint from this GitHub repository using `render.yaml`. It provisions the Docker web service and managed PostgreSQL. The image deterministically generates and verifies the deployment artifact. Startup fails if Alembic migration or idempotent seeding fails, then binds Uvicorn to `0.0.0.0:$PORT`.

Required Render variables:

- `ENVIRONMENT=production` (provided by Blueprint)
- `DATABASE_URL` (provided by Render PostgreSQL; normalized for psycopg v3)
- `SECRET_KEY` (generated secret, at least 32 characters)
- `CORS_ORIGINS=["https://YOUR-VERCEL-PROJECT.vercel.app"]`
- `CORS_ALLOW_CREDENTIALS=false`

Verify `/health`, `/ready`, and `/docs`. `/health` is process liveness; `/ready` separately checks database connectivity and model integrity. Roll back by redeploying a prior commit; back up PostgreSQL before any future schema-changing release.

## Vercel deployment

Import the repository with root directory `frontend`, install command `npm ci`, build command `npm run build`, and output directory `dist`. Set:

- `VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com`

`frontend/vercel.json` rewrites direct SPA routes to `index.html`. After the final Vercel hostname is known, set that exact HTTPS origin in Render `CORS_ORIGINS` and redeploy the backend.

Deployed frontend: `TBD`

Deployed backend: `TBD`

Submission/demo video: `TBD`

See [architecture](docs/architecture.md), [model card](docs/model-card.md), and the [deployment checklist](docs/submission-checklist.md).
