from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from time import perf_counter
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.data.contracts import PROHIBITED_MODEL_COLUMNS
from app.data.generator import parse_time, sha256_file

MODEL_VERSION = "offline-hgb-v1"
POLICY_VERSION = "validation-policy-v1"
DISCLOSURE = (
    "Synthetic held-out performance demonstrates the evaluation pipeline and is not a claim of production accuracy."
)
TRANSACTION = [
    "order_value_paise",
    "discount_percentage",
    "hours_from_delivery_to_return",
    "account_age_days",
    "product_category",
    "reason_code",
]
BEHAVIOURAL = [
    "orders_7d",
    "orders_30d",
    "orders_90d",
    "returns_7d",
    "returns_30d",
    "returns_90d",
    "refund_ratio_90d",
    "average_order_value_prior",
    "order_value_deviation",
    "returns_1h",
    "returns_24h",
    "time_since_previous_return_hours",
    "shared_identity_activity_7d",
    "known_verified_abuse_before_event",
]
GRAPH = [
    "shared_device_accounts",
    "shared_payment_accounts",
    "shared_address_accounts",
    "shared_phone_accounts",
    "shared_ip_accounts",
    "degree",
    "weighted_degree",
    "component_size",
    "component_density",
    "risky_neighbor_proportion",
    "multi_identity_connections",
    "distance_to_verified_abuse",
    "merchant_spanning_connections",
]
ALL_FEATURES = TRANSACTION + BEHAVIOURAL + GRAPH


def _read_csv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_features(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = _read_csv(data_dir / "orders.csv.gz")
    returns = sorted(_read_csv(data_dir / "returns.csv.gz"), key=lambda row: (row["event_time"], row["return_id"]))
    observations = sorted(
        _read_csv(data_dir / "identity_observations.csv.gz"),
        key=lambda row: (row["observed_at"], row["observation_id"]),
    )
    customers = {row["customer_id"]: row for row in _read_csv(data_dir / "customers.csv.gz")}
    splits = {row["return_id"]: row["split"] for row in _read_csv(data_dir / "splits.csv.gz")}
    orders_by_customer: dict[str, list[dict[str, str]]] = defaultdict(list)
    for order in sorted(orders, key=lambda row: row["ordered_at"]):
        orders_by_customer[order["customer_id"]].append(order)
    return_history: dict[str, list[dict[str, str]]] = defaultdict(list)
    token_customers: dict[str, set[str]] = defaultdict(set)
    customer_tokens: dict[str, set[str]] = defaultdict(set)
    token_recent: dict[str, deque] = defaultdict(deque)
    verified: set[str] = set()
    pending_verification: list[tuple[Any, str]] = sorted(
        [
            (parse_time(row["verification_available_at"]), row["customer_id"])
            for row in returns
            if row["verification_available_at"]
        ],
        key=lambda pair: pair[0],
    )
    observation_index = 0
    verification_index = 0
    rows: list[dict[str, Any]] = []
    identity_columns = {
        "DEVICE": "shared_device_accounts",
        "PAYMENT": "shared_payment_accounts",
        "ADDRESS": "shared_address_accounts",
        "PHONE": "shared_phone_accounts",
        "IP": "shared_ip_accounts",
    }
    for ret in returns:
        event_time = parse_time(ret["event_time"])
        while (
            verification_index < len(pending_verification) and pending_verification[verification_index][0] <= event_time
        ):
            verified.add(pending_verification[verification_index][1])
            verification_index += 1
        while (
            observation_index < len(observations)
            and parse_time(observations[observation_index]["observed_at"]) < event_time
        ):
            observation = observations[observation_index]
            identity = observation["token_hash"]
            customer = observation["customer_id"]
            token_customers[identity].add(customer)
            customer_tokens[customer].add(identity)
            token_recent[identity].append(parse_time(observation["observed_at"]))
            observation_index += 1
        customer_id = ret["customer_id"]
        prior_orders = [
            order for order in orders_by_customer[customer_id] if parse_time(order["ordered_at"]) < event_time
        ]
        prior_returns = return_history[customer_id]

        def window(items: list[dict[str, str]], hours: int, as_of=event_time) -> list[dict[str, str]]:
            return [item for item in items if parse_time(item["event_time"]) >= as_of - timedelta(hours=hours)]

        prior_values = [int(order["order_value_paise"]) for order in prior_orders]
        recent_1h, recent_24h, recent_7d = (
            window(prior_returns, 1),
            window(prior_returns, 24),
            window(prior_returns, 24 * 7),
        )
        neighbor_counts: Counter[str] = Counter()
        shared_counts = {column: 0 for column in identity_columns.values()}
        for identity_type, token_column in [
            ("DEVICE", "device_token"),
            ("PAYMENT", "payment_token"),
            ("ADDRESS", "address_token"),
            ("PHONE", "phone_token"),
            ("IP", "ip_token"),
        ]:
            members = token_customers.get(ret[token_column], set()) - {customer_id}
            shared_counts[identity_columns[identity_type]] = len(members)
            neighbor_counts.update(members)
        neighbors = set(neighbor_counts)
        components = {customer_id, *neighbors}
        local_tokens = set(customer_tokens.get(customer_id, set()))
        for neighbor in neighbors:
            local_tokens.update(customer_tokens.get(neighbor, set()))
        token_count = len(local_tokens)
        recent_activity = 0
        for token_value in [
            ret[key] for key in ("device_token", "payment_token", "address_token", "phone_token", "ip_token")
        ]:
            cutoff = event_time - timedelta(days=7)
            recent_activity += sum(seen >= cutoff for seen in token_recent[token_value])
        component_edges = sum(len(customer_tokens[member]) for member in components)
        possible_edges = max(1, len(components) * max(1, token_count))
        risky = neighbors & verified
        distance = 0 if customer_id in verified else (1 if risky else 4)
        merchant_spanning = len(
            {customers[member]["merchant_id"] for member in neighbors if member in customers} - {ret["merchant_id"]}
        )
        account_created = parse_time(customers[customer_id]["account_created_at"])
        row = {
            "return_id": ret["return_id"],
            "event_time": ret["event_time"],
            "split": splits[ret["return_id"]],
            "merchant_id": ret["merchant_id"],
            "is_abuse": int(ret["is_abuse"]),
            "abuse_pattern": ret["abuse_pattern"],
            "order_value_paise": float(ret["order_value_paise"]),
            "discount_percentage": float(ret["discount_percentage"]),
            "hours_from_delivery_to_return": float(ret["hours_from_delivery_to_return"]),
            "account_age_days": float((event_time - account_created).days),
            "product_category": ret["product_category"],
            "reason_code": ret["reason_code"],
            "orders_7d": sum(
                parse_time(order["ordered_at"]) >= event_time - timedelta(days=7) for order in prior_orders
            ),
            "orders_30d": sum(
                parse_time(order["ordered_at"]) >= event_time - timedelta(days=30) for order in prior_orders
            ),
            "orders_90d": sum(
                parse_time(order["ordered_at"]) >= event_time - timedelta(days=90) for order in prior_orders
            ),
            "returns_7d": len(recent_7d),
            "returns_30d": len(window(prior_returns, 24 * 30)),
            "returns_90d": len(window(prior_returns, 24 * 90)),
            "refund_ratio_90d": len(window(prior_returns, 24 * 90))
            / max(1, sum(parse_time(order["ordered_at"]) >= event_time - timedelta(days=90) for order in prior_orders)),
            "average_order_value_prior": float(np.mean(prior_values))
            if prior_values
            else float(ret["order_value_paise"]),
            "order_value_deviation": float(ret["order_value_paise"])
            - (float(np.mean(prior_values)) if prior_values else float(ret["order_value_paise"])),
            "returns_1h": len(recent_1h),
            "returns_24h": len(recent_24h),
            "time_since_previous_return_hours": (
                event_time - parse_time(prior_returns[-1]["event_time"])
            ).total_seconds()
            / 3600
            if prior_returns
            else 9999.0,
            "shared_identity_activity_7d": recent_activity,
            "known_verified_abuse_before_event": int(customer_id in verified),
            **shared_counts,
            "degree": len(neighbors),
            "weighted_degree": sum(neighbor_counts.values()),
            "component_size": len(components),
            "component_density": component_edges / possible_edges,
            "risky_neighbor_proportion": len(risky) / max(1, len(neighbors)),
            "multi_identity_connections": sum(count >= 2 for count in neighbor_counts.values()),
            "distance_to_verified_abuse": distance,
            "merchant_spanning_connections": merchant_spanning,
        }
        rows.append(row)
        return_history[customer_id].append(ret)
    frame = pd.DataFrame(rows)
    if set(frame.columns) & (PROHIBITED_MODEL_COLUMNS - {"is_abuse", "abuse_pattern"}):
        raise ValueError("Prohibited columns leaked into feature frame")
    metadata = frame[["return_id", "event_time", "split", "merchant_id", "is_abuse", "abuse_pattern"]].copy()
    return frame[ALL_FEATURES].copy(), metadata


def rule_engine(features: pd.DataFrame) -> tuple[np.ndarray, list[list[dict[str, str]]]]:
    scores, evidence = [], []
    for _, row in features.iterrows():
        triggers: list[dict[str, str]] = []
        score = 0.0
        if row["returns_24h"] >= 2 or row["returns_7d"] >= 4:
            score += 0.35
            triggers.append({"rule_id": "RETURN_VELOCITY", "evidence": "Recent return activity is elevated."})
        if row["refund_ratio_90d"] >= 0.45:
            score += 0.20
            triggers.append({"rule_id": "REFUND_RATIO", "evidence": "Historical return-to-order ratio is elevated."})
        if row["account_age_days"] < 45 and row["orders_30d"] <= 2:
            score += 0.15
            triggers.append({"rule_id": "NEW_ACCOUNT", "evidence": "New account has limited purchase history."})
        if row["weighted_degree"] >= 5 or row["multi_identity_connections"] >= 2:
            score += 0.40
            triggers.append(
                {
                    "rule_id": "IDENTITY_CONNECTIVITY",
                    "evidence": "Multiple tokenized identities connect this account to others.",
                }
            )
        scores.append(min(1.0, score))
        evidence.append(triggers)
    return np.asarray(scores), evidence


def graph_risk(features: pd.DataFrame) -> np.ndarray:
    return np.clip(
        0.20 * np.tanh(features["weighted_degree"] / 4)
        + 0.25 * np.tanh(features["component_size"] / 8)
        + 0.25 * features["risky_neighbor_proportion"]
        + 0.20 * np.tanh(features["multi_identity_connections"] / 2)
        + 0.10 * np.tanh(features["merchant_spanning_connections"] / 2),
        0,
        1,
    ).to_numpy()


def _pipeline(columns: list[str]) -> Pipeline:
    categorical = [column for column in columns if column in {"product_category", "reason_code"}]
    numeric = [column for column in columns if column not in categorical]
    preprocess = ColumnTransformer(
        [
            ("numeric", SimpleImputer(strategy="median"), numeric),
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
            (
                "model",
                HistGradientBoostingClassifier(
                    max_iter=150, learning_rate=0.08, max_leaf_nodes=15, l2_regularization=1.0, random_state=20260901
                ),
            ),
        ]
    )


def train_models(features: pd.DataFrame, metadata: pd.DataFrame) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    train = metadata["split"] == "train"
    validation = metadata["split"] == "validation"
    test = metadata["split"] == "test"
    labels = metadata["is_abuse"].to_numpy()
    models: dict[str, Any] = {}
    probabilities: dict[str, np.ndarray] = {}
    groups = {"transaction": TRANSACTION, "behavioral": TRANSACTION + BEHAVIOURAL, "graph": ALL_FEATURES}
    for name, columns in groups.items():
        calibrated = CalibratedClassifierCV(_pipeline(columns), method="sigmoid", cv=3)
        calibrated.fit(features.loc[train, columns], labels[train])
        models[name] = {
            "columns": columns,
            "estimator": calibrated,
            "fit_return_ids": metadata.loc[train, "return_id"].tolist(),
        }
        probabilities[f"{name}_validation"] = calibrated.predict_proba(features.loc[validation, columns])[:, 1]
        probabilities[f"{name}_test"] = calibrated.predict_proba(features.loc[test, columns])[:, 1]
    return models, probabilities


@dataclass(frozen=True)
class CostConfig:
    verification_cost_paise: int = 1500
    manual_review_cost_paise: int = 3500
    false_positive_cost_paise: int = 7000
    recovery_rate: float = 0.65
    max_review_rate: float = 0.12


def decide(scores: np.ndarray, verify_threshold: float, review_threshold: float, costs: CostConfig) -> np.ndarray:
    decisions = np.where(scores < verify_threshold, "APPROVE", "VERIFY").astype(object)
    capacity = max(1, int(len(scores) * costs.max_review_rate))
    candidates = np.where(scores >= review_threshold)[0]
    for index in candidates[np.argsort(scores[candidates])[::-1][:capacity]]:
        decisions[index] = "MANUAL_REVIEW"
    return decisions


def business_value(labels: np.ndarray, amounts: np.ndarray, decisions: np.ndarray, costs: CostConfig) -> float:
    prevented = amounts * costs.recovery_rate * ((decisions == "VERIFY") | (decisions == "MANUAL_REVIEW")) * labels
    intervention = (decisions == "VERIFY") * costs.verification_cost_paise + (
        decisions == "MANUAL_REVIEW"
    ) * costs.manual_review_cost_paise
    false_positive = ((decisions != "APPROVE") & (labels == 0)) * costs.false_positive_cost_paise
    return float(prevented.sum() - intervention.sum() - false_positive.sum())


def select_policy(
    validation_labels: np.ndarray, validation_amounts: np.ndarray, ml: np.ndarray, graph: np.ndarray, rules: np.ndarray
) -> dict[str, Any]:
    costs = CostConfig()
    best: dict[str, Any] | None = None
    for weights in [(0.7, 0.2, 0.1), (0.6, 0.25, 0.15), (0.5, 0.3, 0.2)]:
        scores = weights[0] * ml + weights[1] * graph + weights[2] * rules
        for verify in (0.20, 0.30, 0.40):
            for review in (0.55, 0.65, 0.75):
                decisions = decide(scores, verify, review, costs)
                value = business_value(validation_labels, validation_amounts, decisions, costs)
                candidate = {
                    "weights": weights,
                    "verify_threshold": verify,
                    "review_threshold": review,
                    "costs": asdict(costs),
                    "validation_net_savings_paise": value,
                }
                if best is None or value > best["validation_net_savings_paise"]:
                    best = candidate
    if best is None:
        raise RuntimeError("Policy selection failed")
    return best


def _metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    decisions: np.ndarray,
    amounts: np.ndarray,
    costs: CostConfig,
    metadata: pd.DataFrame,
) -> dict[str, Any]:
    flagged = decisions != "APPROVE"
    precision_curve, recall_curve, thresholds = precision_recall_curve(labels, scores)
    calibration_true, calibration_pred = calibration_curve(labels, scores, n_bins=10, strategy="quantile")
    prevented = float((amounts * costs.recovery_rate * flagged * labels).sum())
    verification_cost = int((decisions == "VERIFY").sum() * costs.verification_cost_paise)
    review_cost = int((decisions == "MANUAL_REVIEW").sum() * costs.manual_review_cost_paise)
    fp_cost = int(((flagged & (labels == 0)).sum()) * costs.false_positive_cost_paise)
    by_pattern = {
        pattern: float(
            recall_score(
                labels[metadata["abuse_pattern"].to_numpy() == pattern],
                flagged[metadata["abuse_pattern"].to_numpy() == pattern],
                zero_division=0,
            )
        )
        for pattern in sorted(set(metadata["abuse_pattern"]) - {"none"})
    }
    by_merchant = {
        merchant: float(
            recall_score(
                labels[metadata["merchant_id"].to_numpy() == merchant],
                flagged[metadata["merchant_id"].to_numpy() == merchant],
                zero_division=0,
            )
        )
        for merchant in sorted(set(metadata["merchant_id"]))
    }
    return {
        "precision": float(precision_score(labels, flagged, zero_division=0)),
        "recall": float(recall_score(labels, flagged, zero_division=0)),
        "f1": float(f1_score(labels, flagged, zero_division=0)),
        "pr_auc": float(average_precision_score(labels, scores)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "brier_score": float(brier_score_loss(labels, scores)),
        "confusion_matrix": confusion_matrix(labels, flagged).tolist(),
        "precision_recall_curve": {
            "precision": precision_curve.tolist(),
            "recall": recall_curve.tolist(),
            "thresholds": thresholds.tolist(),
        },
        "calibration_curve": {"observed": calibration_true.tolist(), "predicted": calibration_pred.tolist()},
        "recall_by_abuse_pattern": by_pattern,
        "recall_by_merchant": by_merchant,
        "false_positives_per_1000_legitimate": float(
            (flagged & (labels == 0)).sum() / max(1, (labels == 0).sum()) * 1000
        ),
        "decision_rates": {
            decision: float((decisions == decision).mean()) for decision in ("APPROVE", "VERIFY", "MANUAL_REVIEW")
        },
        "estimated_prevented_loss_paise": prevented,
        "verification_cost_paise": verification_cost,
        "manual_review_cost_paise": review_cost,
        "false_positive_cost_paise": fp_cost,
        "net_estimated_savings_paise": prevented - verification_cost - review_cost - fp_cost,
    }


def run_offline_pipeline(data_dir: Path, artifact_dir: Path) -> dict[str, Any]:
    started = perf_counter()
    features, metadata = build_features(data_dir)
    rules, _ = rule_engine(features)
    graph = graph_risk(features)
    models, probabilities = train_models(features, metadata)
    validation = metadata["split"].to_numpy() == "validation"
    test = metadata["split"].to_numpy() == "test"
    labels = metadata["is_abuse"].to_numpy()
    amounts = features["order_value_paise"].to_numpy()
    policy = select_policy(
        labels[validation], amounts[validation], probabilities["graph_validation"], graph[validation], rules[validation]
    )
    weights = policy["weights"]
    scores = weights[0] * probabilities["graph_test"] + weights[1] * graph[test] + weights[2] * rules[test]
    costs = CostConfig(**policy["costs"])
    decisions = decide(scores, policy["verify_threshold"], policy["review_threshold"], costs)
    test_metadata = metadata.loc[test].reset_index(drop=True)
    metrics = _metrics(labels[test], scores, decisions, amounts[test], costs, test_metadata)
    ablations = {
        "rule_only": float(average_precision_score(labels[validation], rules[validation])),
        "transaction_only": float(average_precision_score(labels[validation], probabilities["transaction_validation"])),
        "transaction_behavioral": float(
            average_precision_score(labels[validation], probabilities["behavioral_validation"])
        ),
        "transaction_behavioral_graph": float(
            average_precision_score(labels[validation], probabilities["graph_validation"])
        ),
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.joblib"
    joblib.dump(models["graph"], model_path)
    feature_hash = hashlib.sha256(json.dumps(ALL_FEATURES).encode()).hexdigest()
    model_checksum = sha256_file(model_path)
    report = {
        "disclosure": DISCLOSURE,
        "model_version": MODEL_VERSION,
        "policy_version": POLICY_VERSION,
        "feature_allowlist": ALL_FEATURES,
        "feature_schema_hash": feature_hash,
        "policy": policy,
        "test_metrics": metrics,
        "validation_ablation_pr_auc": ablations,
        "test_split_return_ids": test_metadata["return_id"].tolist(),
        "inference_latency_ms_per_return": (perf_counter() - started) * 1000 / len(features),
        "batch_throughput_returns_per_second": len(features) / max(0.001, perf_counter() - started),
    }
    metadata_artifact = {
        "model_version": MODEL_VERSION,
        "model_checksum": model_checksum,
        "feature_schema_hash": feature_hash,
        "training_return_ids": models["graph"]["fit_return_ids"],
        "policy": policy,
        "locked_test_evaluation": True,
    }
    (artifact_dir / "evaluation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata_artifact, indent=2, sort_keys=True) + "\n")
    (artifact_dir / "model_card.md").write_text(
        f"# RazorShield {MODEL_VERSION}\n\n{DISCLOSURE}\n\n"
        "Intended use: offline, defense-only coordinated refund-abuse decision support. "
        "Out of scope: automatic rejection or financial penalty.\n",
        encoding="utf-8",
    )
    return report
