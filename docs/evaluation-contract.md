# Evaluation contract

This contract is fixed before data generation and model development so reported
results cannot be shaped by the held-out test set.

## Required disclosure

Every dashboard and document that reports results will display:

> Synthetic held-out performance demonstrates the evaluation pipeline and is not
> a claim of production accuracy.

No numerical performance is reported in Phase 0 because no dataset has been
generated and no model has been trained.

## Split protocol

1. Establish chronological cut points targeting approximately 70% train, 15%
   validation, and 15% test by return event time.
2. Prevent connected synthetic abuse-ring members from crossing partitions where
   practical. Rings spanning a chronological boundary are assigned wholly to the
   later partition or handled with an embargo documented in the split manifest.
3. Never move test examples to improve representation or metrics after examining
   model outcomes. If a rare-pattern reporting cell is too small, report it as
   insufficient rather than changing the split.
4. Fit imputers, encoders, scalers, anomaly models, supervised models, and
   calibration only with permitted training data. Calibration uses training folds
   or a designated training calibration subset, never the test set.
5. Use validation only for model/feature-set selection, hybrid weights, cost
   assumptions sensitivity, and policy thresholds.
6. Lock feature schema, model artifact, hybrid weights, thresholds, and evaluation
   code before one final test evaluation. Corrections to evaluation bugs require a
   documented new evaluation version, never silent reuse.

The split manifest will store record IDs, timestamps, group/ring assignments,
cutoffs, embargo logic, generator version, and checksum.

## Baseline comparison

Validation comparison must include:

1. transparent rule-only baseline;
2. transaction-only calibrated supervised model;
3. transaction plus behavioural/temporal calibrated model;
4. transaction plus behavioural/temporal plus graph calibrated model.

The primary estimator is planned as `HistGradientBoostingClassifier` with a
class-aware training strategy supported through sample weights, inside a
training-only preprocessing pipeline, followed by `CalibratedClassifierCV` or a
documented leakage-safe calibration scheme. An Isolation Forest signal and SHAP
remain optional and cannot delay required functionality.

Selection prioritizes PR-AUC, calibration, validation net savings, recall under
review capacity, and false-positive burden—not accuracy. Model complexity must be
justified by material validation benefit.

## Hybrid and policy selection

The hybrid score has the documented form:

```text
final_risk = w_ml * calibrated_ml_probability
           + w_graph * graph_risk
           + w_rules * rule_risk
```

All components and the final score are bounded to `[0,1]`. Non-negative weights
sum to one. Candidate weights are chosen on validation data and versioned.

The policy searches ordered thresholds `approve_max < manual_review_min` under a
maximum review-capacity constraint. For each request, cost/value simulation uses
INR paise and explicit assumptions for potential refund loss, verification cost,
manual-review cost, legitimate-customer friction, false positives, and expected
recovery. Because realized avoided loss is not observable in synthetic data, it
will be labeled an estimate derived from synthetic ground truth and assumptions.

The policy simulator may recalculate scenarios from locked held-out predictions,
but dashboard edits do not overwrite the validated production policy version.

## Held-out metrics

The untouched test report will include:

- precision, recall, F1, PR-AUC, ROC-AUC, Brier score;
- confusion matrix, precision-recall curve, and calibration curve;
- recall by synthetic abuse pattern and performance by merchant;
- false positives per 1,000 legitimate returns;
- review, approval, and verification rates;
- estimated prevented loss, verification cost, manual-review cost,
  false-positive cost, and net estimated savings in INR;
- single-request inference latency distribution and batch throughput under a
  documented machine/configuration.

Classification metrics require a declared positive action boundary. The primary
detector view treats `VERIFY` plus `MANUAL_REVIEW` as flagged; a separate
manual-review view will be reported to avoid hiding intervention mix.

Where sample size permits, bootstrap 95% confidence intervals will be computed by
resampling at a grouping level that preserves ring/customer dependence. Undefined
or unstable subgroup results will be identified honestly.

## Automated leakage and integrity checks

- Generator reproducibility for a fixed seed/configuration.
- Strict monotonic time and `as_of_time` assertions for history windows.
- Current/future event perturbation cannot change earlier feature snapshots.
- Forbidden columns (`is_abuse`, `ring_id`, `abuse_pattern`, future verification)
  cannot enter model matrices.
- Preprocessor fit IDs are a subset of training IDs.
- No direct abuse-ring group crosses splits under the chosen manifest policy.
- Threshold/model selectors receive no test labels.
- Test evaluation entry point refuses unlocked or mismatched artifacts.
- Feature schema hash matches online serving schema.

## Reproducibility record

The final report will state seed, data/model/policy versions, dependency lock,
commands, hardware, time range, split counts, class prevalence, model artifact
checksum, and evaluation report checksum. Metric tolerances in tests will allow
minor compatible-platform differences; no test will assert fabricated exact
scores.

