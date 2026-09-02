from __future__ import annotations

from types import SimpleNamespace

from app.services.intelligence import deterministic_explanation, uncertainty_indicator


def assessment(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "ml_probability": 0.6,
        "graph_risk": 0.8,
        "rule_risk": 0.4,
        "final_risk": 0.62,
        "feature_snapshot": {
            "returns_24h": 4,
            "refund_ratio_90d": 0.7,
            "shared_payment_accounts": 3,
            "shared_device_accounts": 2,
            "component_size": 4,
            "multi_identity_connections": 2,
            "orders_90d": 12,
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_explanation_is_ordered_deterministic_and_versioned() -> None:
    result = deterministic_explanation(assessment(), (0.7, 0.2, 0.1), "offline-hgb-v1", "operational-demo-v2")
    strengths = [factor["strength"] for factor in result["top_increasing_factors"]]
    assert strengths == sorted(strengths, reverse=True)
    assert result == deterministic_explanation(assessment(), (0.7, 0.2, 0.1), "offline-hgb-v1", "operational-demo-v2")
    assert result["model_version"] == "offline-hgb-v1"
    assert result["signal_contributions"] == {"model": 0.42, "network": 0.16, "rules": 0.04}
    assert "not causal proof" in result["human_review_notice"]


def test_all_uncertainty_states() -> None:
    insufficient = assessment(feature_snapshot={"orders_90d": 2, "component_size": 1})
    borderline = assessment(final_risk=0.18)
    confident = assessment(final_risk=0.75)
    assert uncertainty_indicator(insufficient, 0.1, 0.2)["state"] == "INSUFFICIENT_HISTORY"
    assert uncertainty_indicator(borderline, 0.1, 0.2)["state"] == "BORDERLINE"
    assert uncertainty_indicator(confident, 0.1, 0.2)["state"] == "HIGH_CONFIDENCE"
