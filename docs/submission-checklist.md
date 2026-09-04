# Deployment and submission checklist

## Render

- [ ] Connect GitHub and select the `render.yaml` Blueprint.
- [ ] Confirm `backend/Dockerfile` and managed PostgreSQL.
- [ ] Set exact HTTPS Vercel origin in `CORS_ORIGINS`; confirm generated `SECRET_KEY`.
- [ ] Inspect artifact generation, Alembic migration and idempotent demo-seed logs.
- [ ] Verify `/health`, `/ready`, and `/docs` over HTTPS.

## Vercel

- [ ] Root `frontend`; install `npm ci`; build `npm run build`; output `dist`.
- [ ] Set `VITE_API_BASE_URL` to the Render HTTPS URL and deploy.
- [ ] Add the exact Vercel origin to backend CORS and redeploy the backend.
- [ ] Refresh `/risk-center`, `/cases`, `/networks`, `/model`, and `/safety` directly.

## Post-deployment

- [ ] Confirm all seeded outcomes, manual-review detail and safe one-hop graph.
- [ ] Submit feedback, verify audit order and download a masked evidence export.
- [ ] Confirm no raw token appears in responses or the browser console.
- [ ] Test desktop/mobile, navigation, API recovery and direct SPA URLs.
- [ ] Record deployed URLs, final commit hash and demo-video link in README.
- [ ] Reconfirm the synthetic disclaimer and no-automatic-rejection boundary.
