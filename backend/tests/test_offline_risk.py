from __future__ import annotations

import numpy as np
import pandas as pd

from app.risk.offline import CostConfig, decide, graph_risk, rule_engine, select_policy


def test_rule_engine_is_deterministic() -> None:
    features = pd.DataFrame(
        [
            {
                "returns_24h": 3,
                "returns_7d": 4,
                "refund_ratio_90d": 0.5,
                "account_age_days": 10,
                "orders_30d": 1,
                "weighted_degree": 6,
                "multi_identity_connections": 2,
            }
        ]
    )
    first = rule_engine(features)
    second = rule_engine(features)
    assert np.array_equal(first[0], second[0])
    assert first[1] == second[1]
    assert first[0][0] == 1.0


def test_graph_risk_and_policy_capacity() -> None:
    features = pd.DataFrame(
        {
            "weighted_degree": [0, 10, 20],
            "component_size": [1, 8, 20],
            "risky_neighbor_proportion": [0, 0.5, 1],
            "multi_identity_connections": [0, 1, 3],
            "merchant_spanning_connections": [0, 1, 2],
        }
    )
    assert np.all((graph_risk(features) >= 0) & (graph_risk(features) <= 1))
    decisions = decide(np.array([0.8, 0.9, 0.95]), 0.3, 0.7, CostConfig(max_review_rate=0.34))
    assert (decisions == "MANUAL_REVIEW").sum() == 1


def test_policy_selection_uses_validation_arrays_only() -> None:
    policy = select_policy(
        np.array([0, 1, 0, 1]),
        np.array([10000, 20000, 10000, 20000]),
        np.array([0.1, 0.8, 0.2, 0.9]),
        np.array([0.1, 0.5, 0.2, 0.6]),
        np.array([0.0, 0.4, 0.0, 0.5]),
    )
    assert policy["verify_threshold"] < policy["review_threshold"]
