# Synthetic data dictionary

Phase 2 produces deterministic, token-only, compressed CSV source tables in
`data/generated/default`. Amounts use INR paise and all timestamps are UTC ISO-8601.

| Table | Purpose | Key fields |
|---|---|---|
| `merchants` | Synthetic merchant reference | merchant ID, category, scale segment |
| `customers` | Merchant-scoped synthetic accounts | customer ID, account creation, evaluation-only ring ID |
| `products` | Merchant product catalog | product/category, typical paise price |
| `orders` | Raw commerce events | order/delivery time, paise value, opaque identity tokens |
| `returns` | Return event and evaluation metadata | required raw return fields, label metadata, delayed verification timestamp |
| `identity_observations` | Point-in-time identity observations | token type/hash, observed time, source event |
| `identity_links` | Customer/token aggregates | first/last seen, observation count |
| `splits` | Locked evaluation assignment | return ID, event time, split, evaluation-only ring ID |

`ring_id`, `abuse_pattern`, `is_abuse`, `verification_available_at`, and
`label_noise_applied` are prohibited from model inputs. The exact allowed future
model contract is tracked in `data/model-feature-allowlist.json`.
