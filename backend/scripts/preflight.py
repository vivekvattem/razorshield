from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import sklearn
from sqlalchemy import func, select

from alembic.runtime.migration import MigrationContext
from app.core.config import get_settings
from app.db.session import Database
from app.models import RiskAssessment
from app.models.enums import RiskDecision
from app.services.artifacts import ArtifactService, ArtifactUnavailable


def masked_database_url(value: str) -> str:
    if "@" not in value or "://" not in value:
        return value
    scheme, rest = value.split("://", 1)
    return f"{scheme}://***:***@{rest.split('@', 1)[1]}"


def main() -> None:
    executable = Path(sys.executable)
    environment_root = Path(sys.prefix)
    if "conda" in str(environment_root).lower() or environment_root.name != ".venv":
        raise SystemExit(f"Use the project .venv Python, not global/Conda: {executable}")
    settings = get_settings()
    database = Database(settings.database_url)
    artifact_dir = Path(__file__).resolve().parents[2] / "artifacts/generated/offline-hgb-v1"
    try:
        artifact = ArtifactService(artifact_dir).load()
        artifact_status = f"verified ({artifact.metadata['model_version']})"
    except ArtifactUnavailable as exc:
        raise SystemExit(f"Model artifact unavailable: {exc}") from exc
    with database.engine.connect() as connection:
        migration = MigrationContext.configure(connection).get_current_revision()
    with database.transaction() as session:
        counts = {
            decision.value: session.scalar(
                select(func.count()).select_from(RiskAssessment).where(RiskAssessment.decision == decision)
            )
            or 0
            for decision in RiskDecision
        }
    expected = {"APPROVE": 6, "VERIFY": 4, "MANUAL_REVIEW": 1}
    if any(counts[key] < value for key, value in expected.items()):
        raise SystemExit(f"Seeded outcomes incomplete: expected at least {expected}, found {counts}")
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        raise SystemExit("Node and npm must be installed (Node 20+ required)")
    node_version = subprocess.check_output([node, "--version"], text=True).strip()
    npm_version = subprocess.check_output([npm, "--version"], text=True).strip()
    if int(node_version.removeprefix("v").split(".")[0]) < 20:
        raise SystemExit(f"Node 20+ required, found {node_version}")
    print(
        json.dumps(
            {
                "python_executable": str(executable),
                "python_version": sys.version.split()[0],
                "scikit_learn": sklearn.__version__,
                "node": node_version,
                "npm": npm_version,
                "database_url": masked_database_url(settings.database_url),
                "artifact": artifact_status,
                "migration": migration,
                "seeded_outcomes": counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
