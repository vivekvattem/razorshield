from __future__ import annotations

import csv
import gzip
from pathlib import Path

import pytest

from app.data.contracts import MODEL_FEATURE_ALLOWLIST, PROHIBITED_MODEL_COLUMNS
from app.data.generator import GeneratorConfig, generate_dataset
from app.data.validation import DatasetValidationError, read_table, validate_dataset


@pytest.fixture(scope="session")
def generated_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("synthetic-data") / "default"
    generate_dataset(output_dir)
    return output_dir


def test_same_seed_is_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_dataset(first, GeneratorConfig(seed=7))
    generate_dataset(second, GeneratorConfig(seed=7))
    assert (first / "returns.csv.gz").read_bytes() == (second / "returns.csv.gz").read_bytes()
    assert (first / "manifest.json").read_bytes() == (second / "manifest.json").read_bytes()


def test_different_seed_changes_output(tmp_path: Path) -> None:
    first = generate_dataset(tmp_path / "first", GeneratorConfig(seed=7))
    second = generate_dataset(tmp_path / "second", GeneratorConfig(seed=8))
    assert first["checksums"]["returns"] != second["checksums"]["returns"]


def test_default_dataset_contract(generated_dataset: Path) -> None:
    summary = validate_dataset(generated_dataset)
    assert summary["row_counts"]["orders"] >= 25_000
    assert summary["row_counts"]["returns"] >= 5_000
    assert summary["row_counts"]["customers"] >= 3_000
    assert summary["ring_count"] >= 25
    assert 0.03 <= summary["class_prevalence"] <= 0.15


def test_split_chronology_and_ring_isolation(generated_dataset: Path) -> None:
    split_rows = read_table(generated_dataset, "splits")
    rings: dict[str, set[str]] = {}
    for row in split_rows:
        if row["ring_id"]:
            rings.setdefault(row["ring_id"], set()).add(row["split"])
    assert all(len(assignments) == 1 for assignments in rings.values())
    assert {row["split"] for row in split_rows} == {"train", "validation", "test"}


def test_prohibited_features_are_excluded() -> None:
    assert not (set(MODEL_FEATURE_ALLOWLIST) & PROHIBITED_MODEL_COLUMNS)


def test_shared_identity_overlap_and_demo_cases(generated_dataset: Path) -> None:
    returns = read_table(generated_dataset, "returns")
    links = read_table(generated_dataset, "identity_links")
    non_ring_customers = {
        row["customer_id"] for row in read_table(generated_dataset, "customers") if not row["ring_id"]
    }
    token_customers: dict[str, set[str]] = {}
    for row in links:
        if row["customer_id"] in non_ring_customers:
            token_customers.setdefault(row["token_hash"], set()).add(row["customer_id"])
    assert any(len(customers) > 1 for customers in token_customers.values())
    assert {"legitimate_return", "suspicious_individual", "coordinated_ring"}.issubset(
        {row["demo_case"] for row in returns}
    )
    assert {row["order_value_paise"] for row in returns if row["is_abuse"] == "1"} & {
        row["order_value_paise"] for row in returns if row["is_abuse"] == "0"
    }


def test_validator_rejects_corrupted_data(generated_dataset: Path, tmp_path: Path) -> None:
    corrupted = tmp_path / "corrupted"
    corrupted.mkdir()
    for source in generated_dataset.iterdir():
        destination = corrupted / source.name
        destination.write_bytes(source.read_bytes())
    returns_path = corrupted / "returns.csv.gz"
    with gzip.open(returns_path, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["event_time"] = "2020-01-01T00:00:00Z"
    with gzip.open(returns_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(DatasetValidationError):
        validate_dataset(corrupted)
