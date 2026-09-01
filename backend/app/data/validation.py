from __future__ import annotations

import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.data.contracts import MODEL_FEATURE_ALLOWLIST, PROHIBITED_MODEL_COLUMNS, SCHEMA
from app.data.generator import parse_time, sha256_file


class DatasetValidationError(ValueError):
    pass


def read_table(output_dir: Path, table: str) -> list[dict[str, str]]:
    path = output_dir / f"{table}.csv.gz"
    if not path.exists():
        raise DatasetValidationError(f"Missing required table: {path.name}")
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != SCHEMA[table]:
            raise DatasetValidationError(f"Schema mismatch for {table}")
        return list(reader)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise DatasetValidationError(message)


def validate_dataset(output_dir: Path) -> dict[str, object]:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise DatasetValidationError("Missing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tables = {table: read_table(output_dir, table) for table in SCHEMA}
    _assert(len(tables["orders"]) >= 25_000, "Minimum order scale not met")
    _assert(len(tables["returns"]) >= 5_000, "Minimum return scale not met")
    _assert(len(tables["customers"]) >= 3_000, "Minimum customer scale not met")
    _assert(len({row["merchant_id"] for row in tables["merchants"]}) >= 2, "Multiple merchants required")
    _assert(len({row["ring_id"] for row in tables["returns"] if row["ring_id"]}) >= 25, "Minimum ring count not met")
    primary_keys = {
        "merchants": ("merchant_id",),
        "customers": ("customer_id",),
        "products": ("product_id",),
        "orders": ("order_id",),
        "returns": ("return_id",),
        "identity_observations": ("observation_id",),
        "identity_links": ("customer_id", "identity_type", "token_hash"),
        "splits": ("return_id",),
    }
    for table, rows in tables.items():
        identifiers = [tuple(row[field] for field in primary_keys[table]) for row in rows]
        _assert(len(identifiers) == len(set(identifiers)), f"Duplicate primary identifiers in {table}")
    merchants = {row["merchant_id"] for row in tables["merchants"]}
    customers = {row["customer_id"]: row for row in tables["customers"]}
    orders = {row["order_id"]: row for row in tables["orders"]}
    _assert(all(row["merchant_id"] in merchants for row in tables["customers"]), "Customer merchant FK violation")
    _assert(
        all(row["customer_id"] in customers and row["merchant_id"] in merchants for row in tables["orders"]),
        "Order FK violation",
    )
    _assert(
        all(row["order_id"] in orders and row["customer_id"] in customers for row in tables["returns"]),
        "Return FK violation",
    )
    for order in tables["orders"]:
        _assert(int(order["order_value_paise"]) >= 0, "Negative order value")
        _assert(parse_time(order["ordered_at"]) <= parse_time(order["delivered_at"]), "Order delivery precedes order")
    for row in tables["returns"]:
        _assert(int(row["order_value_paise"]) >= 0, "Negative return order value")
        _assert(
            parse_time(orders[row["order_id"]]["delivered_at"]) <= parse_time(row["event_time"]),
            "Return precedes delivery",
        )
        _assert(
            parse_time(customers[row["customer_id"]]["account_created_at"]) <= parse_time(row["event_time"]),
            "Return precedes account",
        )
        if row["verification_available_at"]:
            _assert(
                parse_time(row["verification_available_at"]) > parse_time(row["event_time"]),
                "Verification is not delayed",
            )
    _assert(not (set(MODEL_FEATURE_ALLOWLIST) & PROHIBITED_MODEL_COLUMNS), "Prohibited feature allowlist leak")
    split_rows = tables["splits"]
    _assert(len(split_rows) == len(tables["returns"]), "Split manifest row count mismatch")
    _assert(len({row["return_id"] for row in split_rows}) == len(split_rows), "Duplicate split assignment")
    split_times = defaultdict(list)
    ring_splits = defaultdict(set)
    for row in split_rows:
        split_times[row["split"]].append(parse_time(row["event_time"]))
        if row["ring_id"]:
            ring_splits[row["ring_id"]].add(row["split"])
    _assert(set(split_times) == {"train", "validation", "test"}, "Missing split")
    _assert(max(split_times["train"]) < min(split_times["validation"]), "Train/validation chronology leak")
    _assert(max(split_times["validation"]) < min(split_times["test"]), "Validation/test chronology leak")
    _assert(all(len(splits) == 1 for splits in ring_splits.values()), "Ring crosses split")
    prevalence = sum(int(row["is_abuse"]) for row in tables["returns"]) / len(tables["returns"])
    _assert(0.03 <= prevalence <= 0.15, "Class imbalance outside expected bounds")
    legitimate_customer_ids = {row["customer_id"] for row in tables["customers"] if not row["ring_id"]}
    token_customers = Counter(
        row["token_hash"] for row in tables["identity_links"] if row["customer_id"] in legitimate_customer_ids
    )
    _assert(any(count > 1 for count in token_customers.values()), "No shared identities detected")
    abuse_values = {int(row["order_value_paise"]) for row in tables["returns"] if row["is_abuse"] == "1"}
    legitimate_values = {int(row["order_value_paise"]) for row in tables["returns"] if row["is_abuse"] == "0"}
    _assert(bool(abuse_values & legitimate_values), "Abuse and legitimate distributions do not overlap")
    _assert(
        {"legitimate_return", "suspicious_individual", "coordinated_ring"}.issubset(
            {row["demo_case"] for row in tables["returns"]}
        ),
        "Demo cases missing",
    )
    _assert(any(row["label_noise_applied"] == "1" for row in tables["returns"]), "Label noise missing")
    _assert(any(row["verification_available_at"] for row in tables["returns"]), "Delayed verification missing")
    for table, checksum in manifest["checksums"].items():
        _assert(sha256_file(output_dir / f"{table}.csv.gz") == checksum, f"Checksum mismatch for {table}")
    return {
        "row_counts": {table: len(rows) for table, rows in tables.items()},
        "class_prevalence": prevalence,
        "split_counts": dict(Counter(row["split"] for row in split_rows)),
        "ring_count": len(ring_splits),
        "checksums": manifest["checksums"],
    }
