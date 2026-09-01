# Synthetic dataset schema plan

## Scale and reproducibility

The generator will use a fixed default seed and explicit configuration version.
The minimum target is 25,000 orders, 5,000 returns, 3,000 customers, multiple
merchants, and at least 25 coordinated abuse rings. Generation will be deterministic
for the same Python/dependency contract, seed, and configuration. Tests will compare
row counts, stable key columns, label prevalence bounds, ring counts, and content
hashes of canonicalized samples rather than relying only on a single binary file.

Generated bulk data and trained binaries will not be committed by default. A small
metadata manifest will record generator version, seed, configuration, counts,
time range, class balance, and checksums.

## Source event tables

The reproducibility source will be normalized event tables, later exported as
Parquet where practical:

- `merchants`: merchant ID, category, scale segment, created time.
- `customers`: merchant/customer IDs, account creation time, latent generator-only
  segment and ring metadata.
- `products`: product ID, merchant ID, category, typical price band.
- `orders`: IDs, ordered/delivered times, value, category/product, discount,
  promotion, and identity tokens observed at order time.
- `returns`: IDs, event time, requested amount, reason, linked order/customer,
  identity tokens observed at return time, generator-only label metadata.
- `identity_observations`: customer, token type/value, observed time, merchant,
  and originating event.

Generator-only latent fields are kept in an evaluation metadata boundary and are
not exposed to online feature code.

## Return-level modelling table

Required identifiers and event attributes:

`return_id`, `event_time`, `merchant_id`, `customer_id`, `order_id`, `order_value`,
`product_category`, `account_age_days`, `hours_from_delivery_to_return`,
`discount_percentage`, `payment_token`, `device_token`, `address_token`,
`phone_token`, `ip_token`, `promo_code`, `reason_code`.

Point-in-time historical features:

`orders_7d`, `orders_30d`, `orders_90d`, `returns_7d`, `returns_30d`,
`returns_90d`, `refund_ratio_90d`, prior average order value, deviation from
customer baseline, returns in 1 hour and 24 hours, time since prior return,
shared-identity activity windows, and burst/velocity measures.

Evaluation-only metadata:

`prior_verified_abuse` is usable only when it represents an outcome whose
verification timestamp is before the scored event. `abuse_pattern`, `ring_id`, and
`is_abuse` are labels/stratifiers and are never model inputs. To avoid ambiguity,
the feature snapshot will name the safe field `known_verified_abuse_before_event`;
the raw label metadata remains separate.

## Graph feature snapshot

For each return at event time `t`, graph construction may use only observations
strictly before or at the documented event boundary for `t`, and verified outcomes
recorded before `t`. Planned fields include:

- unique accounts sharing device, payment, address, phone, and IP tokens;
- component size, customer degree, weighted degree, component density;
- risky-neighbour count and proportion based only on prior verified outcomes;
- maximum identity-type multiplicity connecting customer pairs;
- distance to previously verified abuse (sentinel/capped when unreachable);
- merchant-spanning connection count;
- recent shared-identity activity and component return velocity.

Features will use stable definitions for self-exclusion, window inclusivity,
missing values, capped counts, and token recency. Those definitions become unit-test
fixtures in Phase 3.

## Synthetic population assumptions

- Legitimate customers can share households, IP ranges, addresses, devices, or
  promotions, ensuring graph linkage alone is insufficient.
- Abuse labels are imbalanced and include at least 25 coordinated rings across
  multi-account coordination, linked-device/payment reuse, promotion/refund
  cycling, bursts, address clusters, and recently created coordinated accounts.
- Abuse and legitimate feature distributions overlap; controlled label noise and
  delayed verification prevent a trivially separable problem.
- Merchant sizes, product categories, values, seasonality, delivery delays, return
  reasons, and return propensities vary.
- Synthetic patterns describe defensive signals and will not document practical
  evasion procedures or real credentials.

## Leakage boundary

Every derived feature accepts an `as_of_time`. Historical aggregates exclude the
current label/outcome and future events. Preprocessing is fit on training only.
Ring metadata, labels, abuse-pattern fields, post-event outcomes, and globally
calculated target rates are prohibited features. A feature allowlist and a
forbidden-column test will enforce this boundary.

