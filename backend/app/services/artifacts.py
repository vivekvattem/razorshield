from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import joblib

from app.risk.offline import ALL_FEATURES, MODEL_VERSION, POLICY_VERSION


class ArtifactUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadedArtifact:
    model: object
    metadata: dict
    evaluation: dict


class ArtifactService:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._cached: LoadedArtifact | None = None

    def load(self) -> LoadedArtifact:
        if self._cached:
            return self._cached
        model_path, metadata_path, report_path = (
            self.directory / name for name in ("model.joblib", "metadata.json", "evaluation.json")
        )
        if not all(path.exists() for path in (model_path, metadata_path, report_path)):
            raise ArtifactUnavailable("Offline detector artifact is unavailable")
        metadata = json.loads(metadata_path.read_text())
        digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if metadata.get("model_checksum") != digest or metadata.get("model_version") != MODEL_VERSION:
            raise ArtifactUnavailable("Offline detector artifact integrity verification failed")
        report = json.loads(report_path.read_text())
        if report.get("policy_version") != POLICY_VERSION or report.get("feature_allowlist") != ALL_FEATURES:
            raise ArtifactUnavailable("Offline and online feature contracts differ")
        self._cached = LoadedArtifact(joblib.load(model_path)["estimator"], metadata, report)
        return self._cached
