from __future__ import annotations

import csv
import gzip
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.data.contracts import (
    DEFAULT_SEED,
    GENERATOR_VERSION,
    MODEL_FEATURE_ALLOWLIST,
    PROHIBITED_MODEL_COLUMNS,
    SCHEMA,
)


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = DEFAULT_SEED
    merchant_count: int = 5
    customer_count: int = 3200
    orders_per_customer: int = 8
    return_count: int = 5200
    ring_count: int = 25
    ring_members: int = 8


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def token(kind: str, value: str) -> str:
    digest = hashlib.blake2s(value.encode("utf-8"), digest_size=10).hexdigest()
    return f"{kind}_tok_{digest}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
            with open_text(zipped) as text:
                writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n", extrasaction="raise")
                writer.writeheader()
                writer.writerows(rows)


def open_text(handle):  # type: ignore[no-untyped-def]
    import io

    return io.TextIOWrapper(handle, encoding="utf-8", newline="")


def _identity_bundle(customer_number: int, ring_number: int | None, rng: random.Random) -> dict[str, str]:
    if ring_number is not None:
        household = f"ring-{ring_number:02d}-cluster"
        return {
            "device_token": token("device", household),
            "payment_token": token("payment", f"{household}-payment-{customer_number % 2}"),
            "address_token": token("address", household),
            "phone_token": token("phone", f"{household}-phone-{customer_number % 3}"),
            "ip_token": token("ip", household),
        }
    household = f"household-{customer_number // 3}" if rng.random() < 0.30 else f"customer-{customer_number}"
    payment_group = household if rng.random() < 0.12 else f"payment-{customer_number}"
    return {
        "device_token": token("device", household),
        "payment_token": token("payment", payment_group),
        "address_token": token("address", household),
        "phone_token": token("phone", household),
        "ip_token": token("ip", f"ip-pool-{customer_number // 6}"),
    }


def _ring_start(ring_number: int) -> datetime:
    safe_days = [
        8,
        20,
        34,
        48,
        62,
        76,
        90,
        104,
        118,
        132,
        146,
        160,
        174,
        188,
        202,
        216,
        230,
        244,
        270,
        282,
        294,
        326,
        338,
        350,
        362,
    ]
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=safe_days[ring_number - 1])


def _safe_boundary(events: list[dict[str, Any]], target: int) -> datetime:
    ranges: dict[str, tuple[datetime, datetime]] = {}
    for event in events:
        ring_id = event["ring_id"]
        if not ring_id:
            continue
        current = ranges.get(ring_id)
        event_time = parse_time(event["event_time"])
        ranges[ring_id] = (
            event_time if current is None else min(current[0], event_time),
            event_time if current is None else max(current[1], event_time),
        )
    for offset in range(len(events)):
        candidate_indexes = [target] if offset == 0 else [target - offset, target + offset]
        for index in candidate_indexes:
            if not 0 <= index < len(events):
                continue
            candidate = parse_time(events[index]["event_time"])
            if all(not (start < candidate <= end) for start, end in ranges.values()):
                return candidate
    raise ValueError("Could not find a group-safe chronological split boundary")


def _assign_splits(returns: list[dict[str, Any]]) -> tuple[list[dict[str, str]], dict[str, str]]:
    ordered = sorted(returns, key=lambda row: (row["event_time"], row["return_id"]))
    first = _safe_boundary(ordered, round(len(ordered) * 0.70))
    second = _safe_boundary(ordered, round(len(ordered) * 0.85))
    if second <= first:
        raise ValueError("Split boundaries are not chronological")
    assignments: list[dict[str, str]] = []
    return_splits: dict[str, str] = {}
    for row in ordered:
        event_time = parse_time(row["event_time"])
        split = "train" if event_time < first else "validation" if event_time < second else "test"
        assignments.append(
            {"return_id": row["return_id"], "event_time": row["event_time"], "split": split, "ring_id": row["ring_id"]}
        )
        return_splits[row["return_id"]] = split
    return assignments, {"train_end_exclusive": iso(first), "validation_end_exclusive": iso(second)}


def generate_dataset(output_dir: Path, config: GeneratorConfig | None = None) -> dict[str, Any]:
    config = config or GeneratorConfig()
    if config.customer_count < config.ring_count * config.ring_members:
        raise ValueError("customer_count must accommodate every ring member")
    if config.return_count > config.customer_count * config.orders_per_customer:
        raise ValueError("return_count cannot exceed available orders")
    rng = random.Random(config.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    merchant_categories = ["fashion", "electronics", "beauty", "home", "marketplace"]
    product_categories = ["apparel", "accessories", "devices", "skincare", "homeware"]
    merchants = [
        {
            "merchant_id": f"merchant-{number:02d}",
            "merchant_name": f"Demo Merchant {number:02d}",
            "category": merchant_categories[(number - 1) % len(merchant_categories)],
            "scale_segment": ("enterprise", "growth", "emerging")[number % 3],
            "created_at": iso(start - timedelta(days=365 + number)),
        }
        for number in range(1, config.merchant_count + 1)
    ]
    products = [
        {
            "product_id": f"product-{merchant:02d}-{product:02d}",
            "merchant_id": f"merchant-{merchant:02d}",
            "product_category": product_categories[(merchant + product) % len(product_categories)],
            "typical_price_paise": str(50000 + product * 17500),
        }
        for merchant in range(1, config.merchant_count + 1)
        for product in range(1, 6)
    ]
    customers: list[dict[str, str]] = []
    identities: dict[str, dict[str, str]] = {}
    ring_for_customer: dict[str, str] = {}
    for number in range(1, config.customer_count + 1):
        ring_number = (
            (number - 1) // config.ring_members + 1 if number <= config.ring_count * config.ring_members else None
        )
        ring_id = f"ring-{ring_number:02d}" if ring_number else ""
        merchant_id = f"merchant-{((number - 1) % config.merchant_count) + 1:02d}"
        customer_id = f"customer-{number:05d}"
        account_created = start - timedelta(days=rng.randint(30, 720))
        customers.append(
            {
                "customer_id": customer_id,
                "merchant_id": merchant_id,
                "account_created_at": iso(account_created),
                "customer_segment": "coordinated_evaluation"
                if ring_id
                else ("household" if number % 3 == 0 else "standard"),
                "ring_id": ring_id,
            }
        )
        identities[customer_id] = _identity_bundle(number, ring_number, rng)
        if ring_id:
            ring_for_customer[customer_id] = ring_id
    orders: list[dict[str, str]] = []
    orders_by_customer: dict[str, list[dict[str, str]]] = {customer["customer_id"]: [] for customer in customers}
    order_counter = 0
    for customer in customers:
        customer_id = customer["customer_id"]
        ring_id = customer["ring_id"]
        for ordinal in range(config.orders_per_customer):
            order_counter += 1
            if ring_id:
                ring_number = int(ring_id.split("-")[1])
                ordered_at = _ring_start(ring_number) - timedelta(days=rng.randint(2, 6), hours=rng.randint(0, 20))
            else:
                ordered_at = start + timedelta(
                    days=rng.randint(0, 364), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
                )
            delivered_at = ordered_at + timedelta(days=rng.randint(1, 7), hours=rng.randint(0, 12))
            product = products[(order_counter + ordinal) % len(products)]
            discount = rng.choice([0, 0, 0, 500, 1000, 1500, 2000])
            row = {
                "order_id": f"order-{order_counter:06d}",
                "merchant_id": customer["merchant_id"],
                "customer_id": customer_id,
                "product_id": product["product_id"],
                "ordered_at": iso(ordered_at),
                "delivered_at": iso(delivered_at),
                "order_value_paise": str(rng.randint(45000, 240000)),
                "product_category": product["product_category"],
                "discount_basis_points": str(discount),
                "promo_code": token("promo", f"promo-{discount}-{order_counter % 45}"),
                **identities[customer_id],
            }
            orders.append(row)
            orders_by_customer[customer_id].append(row)
    ring_orders = [order for order in orders if order["customer_id"] in ring_for_customer]
    non_ring_orders = [order for order in orders if order["customer_id"] not in ring_for_customer]
    rng.shuffle(ring_orders)
    rng.shuffle(non_ring_orders)
    selected: list[tuple[dict[str, str], int, str, str]] = []
    used_orders: set[str] = set()
    for ring_number in range(1, config.ring_count + 1):
        ring_id = f"ring-{ring_number:02d}"
        ring_selection = [row for row in ring_orders if ring_for_customer[row["customer_id"]] == ring_id][:10]
        patterns = ["linked_identity_cluster", "return_velocity_cluster", "promotion_return_pattern", "address_cluster"]
        for index, order in enumerate(ring_selection):
            selected.append((order, 1, patterns[index % len(patterns)], ring_id))
            used_orders.add(order["order_id"])
    demo_legitimate = non_ring_orders.pop(0)
    demo_suspicious = non_ring_orders.pop(0)
    demo_ring = next(row for row, _, _, ring in selected if ring == "ring-01")
    for order in (demo_legitimate, demo_suspicious):
        used_orders.add(order["order_id"])
    selected.extend(
        [
            (demo_legitimate, 0, "none", ""),
            (demo_suspicious, 1, "high_return_velocity", ""),
        ]
    )
    remaining_abuse = 145
    for order in non_ring_orders:
        if len([item for item in selected if item[1] == 1]) >= config.ring_count * 10 + 1 + remaining_abuse:
            break
        if order["order_id"] not in used_orders:
            selected.append((order, 1, "high_return_velocity", ""))
            used_orders.add(order["order_id"])
    for order in ring_orders + non_ring_orders:
        if len(selected) >= config.return_count:
            break
        if order["order_id"] not in used_orders:
            selected.append((order, 0, "none", ring_for_customer.get(order["customer_id"], "")))
            used_orders.add(order["order_id"])
    if len(selected) != config.return_count:
        raise ValueError("Unable to select the configured number of return requests")
    returns: list[dict[str, str]] = []
    verified_by_customer: dict[str, list[datetime]] = {}
    for number, (order, latent_abuse, pattern, ring_id) in enumerate(selected, start=1):
        delivered_at = parse_time(order["delivered_at"])
        if ring_id:
            event_time = max(
                delivered_at + timedelta(hours=12), _ring_start(int(ring_id[-2:])) + timedelta(hours=number % 72)
            )
        elif latent_abuse:
            event_time = delivered_at + timedelta(hours=rng.randint(4, 48))
        else:
            event_time = delivered_at + timedelta(hours=rng.randint(12, 24 * 75))
        customer_id = order["customer_id"]
        account_created = next(row["account_created_at"] for row in customers if row["customer_id"] == customer_id)
        known_verified = any(at <= event_time for at in verified_by_customer.get(customer_id, []))
        noisy = rng.random() < (0.025 if latent_abuse else 0.004)
        label = 1 - latent_abuse if noisy else latent_abuse
        verification_available = event_time + timedelta(days=rng.randint(7, 21)) if label else None
        if label and verification_available:
            verified_by_customer.setdefault(customer_id, []).append(verification_available)
        return_id = f"return-{number:06d}"
        demo_case = ""
        if order["order_id"] == demo_legitimate["order_id"]:
            return_id, demo_case = "demo-legitimate-return", "legitimate_return"
        elif order["order_id"] == demo_suspicious["order_id"]:
            return_id, demo_case = "demo-suspicious-return", "suspicious_individual"
        elif order["order_id"] == demo_ring["order_id"]:
            return_id, demo_case = "demo-ring-return", "coordinated_ring"
        returns.append(
            {
                "return_id": return_id,
                "event_time": iso(event_time),
                "merchant_id": order["merchant_id"],
                "customer_id": customer_id,
                "order_id": order["order_id"],
                "order_value_paise": order["order_value_paise"],
                "product_category": order["product_category"],
                "account_age_days": str(max(0, (event_time - parse_time(account_created)).days)),
                "hours_from_delivery_to_return": str(round((event_time - delivered_at).total_seconds() / 3600, 2)),
                "discount_percentage": str(round(int(order["discount_basis_points"]) / 100, 2)),
                "payment_token": order["payment_token"],
                "device_token": order["device_token"],
                "address_token": order["address_token"],
                "phone_token": order["phone_token"],
                "ip_token": order["ip_token"],
                "promo_code": order["promo_code"],
                "reason_code": rng.choice(["SIZE", "DAMAGED", "NOT_AS_DESCRIBED", "CHANGED_MIND"]),
                "prior_verified_abuse": str(int(known_verified)),
                "known_verified_abuse_before_event": str(int(known_verified)),
                "ring_id": ring_id,
                "abuse_pattern": pattern if label else "none",
                "is_abuse": str(label),
                "label_noise_applied": str(int(noisy)),
                "verification_available_at": iso(verification_available) if verification_available else "",
                "demo_case": demo_case,
            }
        )
    returns.sort(key=lambda row: (row["event_time"], row["return_id"]))
    observations: list[dict[str, str]] = []
    event_rows = [("order", row["order_id"], row["ordered_at"], row) for row in orders] + [
        ("return", row["return_id"], row["event_time"], row) for row in returns
    ]
    identity_names = ["device_token", "payment_token", "address_token", "phone_token", "ip_token"]
    for source_type, source_id, observed_at, row in event_rows:
        for identity_name in identity_names:
            observations.append(
                {
                    "observation_id": f"obs-{len(observations) + 1:08d}",
                    "customer_id": row["customer_id"],
                    "merchant_id": row["merchant_id"],
                    "identity_type": identity_name.removesuffix("_token").upper(),
                    "token_hash": row[identity_name],
                    "observed_at": observed_at,
                    "source_event_type": source_type,
                    "source_event_id": source_id,
                }
            )
    link_buckets: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for observation in observations:
        key = (observation["customer_id"], observation["identity_type"], observation["token_hash"])
        link_buckets.setdefault(key, []).append(observation)
    links = [
        {
            "customer_id": customer_id,
            "merchant_id": rows[0]["merchant_id"],
            "identity_type": identity_type,
            "token_hash": token_hash,
            "first_seen_at": min(row["observed_at"] for row in rows),
            "last_seen_at": max(row["observed_at"] for row in rows),
            "observation_count": str(len(rows)),
        }
        for (customer_id, identity_type, token_hash), rows in sorted(link_buckets.items())
    ]
    splits, boundaries = _assign_splits(returns)
    tables = {
        "merchants": merchants,
        "customers": customers,
        "products": products,
        "orders": orders,
        "returns": returns,
        "identity_observations": observations,
        "identity_links": links,
        "splits": splits,
    }
    checksums: dict[str, str] = {}
    for table, rows in tables.items():
        filename = output_dir / f"{table}.csv.gz"
        write_csv(filename, SCHEMA[table], rows)
        checksums[table] = sha256_file(filename)
    split_counts = {split: sum(row["split"] == split for row in splits) for split in ("train", "validation", "test")}
    abuse_count = sum(int(row["is_abuse"]) for row in returns)
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": config.seed,
        "configuration": asdict(config),
        "row_counts": {table: len(rows) for table, rows in tables.items()},
        "time_range": {"start": returns[0]["event_time"], "end": returns[-1]["event_time"]},
        "split_boundaries": boundaries,
        "split_counts": split_counts,
        "class_prevalence": abuse_count / len(returns),
        "abuse_return_count": abuse_count,
        "ring_count": config.ring_count,
        "ring_distribution": {
            split: len({row["ring_id"] for row in splits if row["split"] == split and row["ring_id"]})
            for split in ("train", "validation", "test")
        },
        "checksums": checksums,
        "model_feature_allowlist": list(MODEL_FEATURE_ALLOWLIST),
        "prohibited_model_columns": sorted(PROHIBITED_MODEL_COLUMNS),
        "split_policy": (
            "Chronological boundaries are selected outside ring event ranges; ring members never cross a split."
        ),
        "demo_cases": ["demo-legitimate-return", "demo-suspicious-return", "demo-ring-return"],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def write_static_contracts(data_root: Path) -> None:
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "schema.json").write_text(json.dumps(SCHEMA, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (data_root / "model-feature-allowlist.json").write_text(
        json.dumps({"allowlist": MODEL_FEATURE_ALLOWLIST, "prohibited": sorted(PROHIBITED_MODEL_COLUMNS)}, indent=2)
        + "\n",
        encoding="utf-8",
    )
