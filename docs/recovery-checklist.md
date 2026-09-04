# Demo recovery checklist

Use the project-local Python 3.11 environment for artifact generation and serving.

1. Run `make setup` after a fresh checkout.
2. Run `make bootstrap` to migrate, regenerate the compatible model artifact, and seed the demo database idempotently.
3. Run `make preflight` and confirm:
   - the active interpreter belongs to `.venv`;
   - Python, scikit-learn, Node, and npm versions are reported;
   - the model checksum and Alembic revision are valid;
   - demo decisions include at least 6 APPROVE, 4 VERIFY, and 1 MANUAL_REVIEW.
4. Start the API with `make backend` and the dashboard with `make frontend`.
5. Verify `/ready`, `/api/v1/metrics/business`, `/api/v1/metrics/model`, and `/api/v1/cases` before the demo.
6. Run `make test` before submission.

If the local SQLite database contains stale demo outcomes, move `backend/razorshield.db` to a backup location and rerun `make bootstrap`. Do not delete a database whose contents have not been inspected.

The dashboard must show actionable errors when the API or model is unavailable. It must never substitute innocent-looking zeroes or dashes for failed requests.
