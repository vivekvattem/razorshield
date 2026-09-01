# Database schema plan

## Conventions

- UUID primary keys; stable external IDs have explicit unique constraints.
- UTC timezone-aware timestamps: `created_at` and `updated_at` where mutation is
  permitted, and immutable event timestamps for observations and audit records.
- INR monetary amounts stored as integer paise (`*_amount_paise`) to avoid
  floating-point currency errors.
- Identity/payment values are opaque synthetic or tokenized strings only.
- JSON is reserved for variable evidence snapshots, metric payloads, and immutable
  configuration; searchable domain fields remain typed columns.
- PostgreSQL is canonical. SQLite compatibility is maintained for unit/API tests
  that do not depend on PostgreSQL-only semantics.

## Planned tables

### `merchants`

`id`, unique `external_id`, `name`, `status`, `timezone`, timestamps. Indexed by
status. Merchant IDs scope orders, returns, cases, and policy visibility.

### `customers`

`id`, `merchant_id` FK, `external_id`, `account_created_at`, timestamps. Unique on
`(merchant_id, external_id)` and indexed by account creation time. A customer is
merchant-scoped; graph linkage across merchants is derived through tokenized
identities, not by merging customer records.

### `orders`

`id`, `merchant_id` FK, `customer_id` FK, unique external `order_id` within a
merchant, `ordered_at`, `delivered_at`, `order_value_paise`, `product_id` or
category, `discount_basis_points`, `promo_code`, and tokenized identity snapshots.
Indexes cover merchant/time and customer/time. Check constraints enforce
non-negative value and discount in `[0, 10000]` basis points.

### `return_requests`

`id`, `merchant_id` FK, `customer_id` FK, `order_id` FK, unique external
`return_id` within a merchant, `event_time`, `reason_code`, `requested_amount_paise`,
normalized status, source, idempotency key, payload fingerprint, timestamps.
Unique constraints cover `(merchant_id, return_id)` and `(merchant_id,
idempotency_key)` when present. Indexes cover event time, merchant/time,
customer/time, and status/time.

### `identity_links`

`id`, `merchant_id` FK nullable only for explicitly global synthetic tokens,
`customer_id` FK, `identity_type`, `token_hash`, `first_seen_at`, `last_seen_at`,
`observation_count`, timestamps. Unique on `(customer_id, identity_type,
token_hash)`; indexes on `(identity_type, token_hash)`, customer, and last-seen
time. No raw identity or payment credential is stored.

### `model_versions`

`id`, unique `version`, `status`, `model_type`, `artifact_uri`, `artifact_sha256`,
`feature_schema_hash`, `trained_at`, `training_data_version`, `metrics_json`,
`created_at`. Activation is explicit; artifacts are immutable.

### `policy_versions`

`id`, unique `version`, `status`, `effective_from`, ML/graph/rule weights,
approval and review thresholds, cost configuration JSON, review capacity,
selection data version, timestamps. Constraints enforce ordered thresholds,
weights in `[0,1]`, and a documented weight-sum tolerance.

### `risk_assessments`

`id`, unique `assessment_id`, `return_request_id` FK, `model_version_id` FK,
`policy_version_id` FK, `request_id`, `correlation_id`, input fingerprint,
`ml_probability`, `graph_risk`, `rule_risk`, `final_risk`, selected `decision`,
feature/evidence snapshots JSON, explanation source/status, `scored_at`, latency.
Indexes cover return, decision/time, final risk, and version pairs. Score checks
enforce `[0,1]`. Rows are append-only at the service boundary.

### `cases`

`id`, unique `case_id`, `risk_assessment_id` FK unique, merchant FK, status,
priority, `assigned_to` nullable, `opened_at`, `resolved_at`, timestamps. Indexes
cover queue filters: merchant/status/priority/opened time and assessment risk.
An assessment can create at most one case.

### `analyst_decisions`

`id`, `case_id` FK, actor identifier, action enum (`APPROVE_CASE`, `DISMISS_CASE`,
`ESCALATE_CASE`), neutral rationale, checklist snapshot JSON, `created_at`.
Append-only; indexed by case/time and actor/time. This records review workflow,
not an automatic financial action.

### `audit_events`

`id`, unique `event_id`, entity type/id, event type, actor type/id, request and
correlation IDs, immutable payload JSON, `occurred_at`. Indexed by entity/time,
request ID, correlation ID, and event type/time. Sensitive tokens are redacted or
hashed before payload creation.

## Transaction and lifecycle rules

- Return persistence, risk assessment, case creation, and corresponding audit
  records commit in one transaction.
- Idempotency is enforced by the database as well as the service. Concurrent
  duplicates converge on the original assessment.
- Model and policy versions referenced by an assessment cannot be deleted.
- Analyst decisions and audit events are never updated through public application
  APIs.
- Alembic owns schema creation and evolution; application startup will not create
  production tables ad hoc.

Exact SQLAlchemy types, deletion policies, partial indexes, and migration syntax
will be finalized in Phase 1 and verified on both supported database modes.

