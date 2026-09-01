from __future__ import annotations

import json
from pathlib import Path

from app.risk.offline import run_offline_pipeline

if __name__ == "__main__":
    report = run_offline_pipeline(Path("../data/generated/default"), Path("../artifacts/generated/offline-hgb-v1"))
    print(
        json.dumps(
            {
                "model_version": report["model_version"],
                "test_metrics": report["test_metrics"],
                "validation_ablation_pr_auc": report["validation_ablation_pr_auc"],
            },
            sort_keys=True,
        )
    )
