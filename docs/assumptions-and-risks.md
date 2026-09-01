# Phase 0 assumptions and risks

## Assumptions

1. The Buildathon submission is a self-contained demonstration using only
   synthetic data; no Razorpay production or test endpoint is assumed.
2. INR is the sole demo currency. Persistence uses integer paise and presentation
   formats rupees.
3. UTC is used internally. Merchant-local time is presentation context only.
4. The application is a modular monolith with offline scripts, not a distributed
   streaming platform. Batch imports are bounded HTTP/file-backed demo workloads.
5. PostgreSQL 15+ is canonical production storage; SQLite supports fast tests
   where dialect behaviour is equivalent.
6. Python will target 3.11-compatible syntax and dependencies even though the
   inspected machine currently has Python 3.14.6. CI/containers will provide the
   supported runtime.
7. Node 20+ will be the frontend support target even though the inspected machine
   currently has Node 24.9.0.
8. Authentication/RBAC may be implemented as a minimal demo boundary if time
   permits, but the absence of production identity integration will be explicit.
9. Optional explanations use deterministic templates by default. No external LLM
   is required for scoring, tests, or the demo.
10. An analyst workflow action changes only case status/audit history; it does not
    execute refunds, reject customers, or impose financial penalties.

## Principal risks and mitigations

| Risk | Impact | Planned mitigation |
|---|---|---|
| Temporal or group leakage | Inflated synthetic metrics | `as_of_time` APIs, split manifest, forbidden feature allowlist, perturbation and group tests |
| Graph computation cost | Slow generation/scoring | Temporal adjacency indexes, bounded subgraphs, cached immutable snapshots only where safe, benchmark gates |
| Calibration with rare positives | Unstable probabilities | Stratified/group-aware training folds where feasible, calibration curves/Brier score, confidence intervals |
| SQLite/PostgreSQL drift | Tests pass but production fails | PostgreSQL Compose integration checks plus dialect-neutral unit tests |
| Python 3.14 dependency incompatibility locally | Installation/training failure | Python 3.11 container/venv contract and conservative pinned dependencies |
| Synthetic generator too easy | Misleading performance | Legitimate shared identities, overlapping distributions, noise, delayed outcomes, subgroup error review |
| Review-capacity policy gaming | Attractive but unusable savings | Validation-only threshold lock, explicit capacity, full cost breakdown and sensitivity simulator |
| Optional explanation outage | Broken case workflow | Downstream timeout/circuit boundary and deterministic evidence-only template fallback |
| Model artifact missing/corrupt | Unsafe or misleading score | Readiness failure, checksum/schema verification, structured 503; no invented probability |
| Duplicate concurrent requests | Double cases/audit | Payload fingerprint, unique idempotency constraint, transactional retrieval |
| Sensitive tokens in logs/UI | Privacy/security exposure | Synthetic/opaque identifiers, hashing/redaction, no raw cards/CVV/secrets |
| Scope creep before deadline | Incomplete core journey | Phase gates; prioritize detector, evidence, audit, dashboard, evaluation over optional AI/SHAP/auth |
| Limited production controls | Demo mistaken for production-ready | Explicit limitations covering SSO, retention, monitoring, rate limits, governance, drift and human review |

## Decisions deferred to later phase gates

- Exact dependency versions after compatibility checks in Phase 1.
- Generator parameters and final class prevalence after validation in Phase 2.
- Graph weighting/recency formulas after fixtures in Phase 3.
- Model/hybrid weights, thresholds, costs, and all numerical metrics after the
  validation protocol in Phase 4.
- Whether optional external explanation integration adds value beyond the required
  deterministic fallback in Phase 7.

