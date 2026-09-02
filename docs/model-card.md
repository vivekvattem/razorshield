# RazorShield model card

RazorShield supports defense-only detection of coordinated refund and return abuse. It
combines calibrated supervised probability with point-in-time behavioural, bounded
one-hop identity-network and transparent rule signals. It is not intended for other fraud
classes, customer accusation, automatic rejection or financial penalty.

## Explanation and uncertainty

The serving API derives deterministic explanation factors only from the immutable stored
feature snapshot. It ranks factors by their value relative to documented feature
thresholds and reports the exact weighted ML, network and rule signal contributions. This
is not SHAP, causal proof or an LLM-generated justification.

The data-sufficiency state is `INSUFFICIENT_HISTORY` when fewer than three prior 90-day
orders and no linked account are available, `BORDERLINE` when final risk lies within 0.05
of an operational threshold, and `HIGH_CONFIDENCE` otherwise. The label is a heuristic,
not statistical confidence.

## Feedback and threshold analytics

Feedback remains append-only and does not retrain or alter an assessment. Analytics use
the latest feedback per case. Agreement counts confirmed abuse on `VERIFY` or
`MANUAL_REVIEW`, and legitimate feedback on `APPROVE`; insufficient evidence is excluded
from its denominator. Threshold analytics preserve the validation-selected policy and
locked held-out report separately from `operational-demo-v2`; unavailable values remain
unavailable.

Synthetic held-out performance demonstrates the evaluation pipeline and is not a claim
of production accuracy. Merchant traffic, identity availability, drift, label delay and
human-review consistency may materially change real performance.
