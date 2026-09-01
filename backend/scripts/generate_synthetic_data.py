from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.data.generator import GeneratorConfig, generate_dataset, write_static_contracts
from app.data.validation import validate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic RazorShield synthetic commerce data")
    parser.add_argument("--output-dir", type=Path, default=Path("../data/generated/default"))
    parser.add_argument("--seed", type=int, default=GeneratorConfig().seed)
    args = parser.parse_args()
    data_root = args.output_dir.parent.parent
    write_static_contracts(data_root)
    manifest = generate_dataset(args.output_dir, GeneratorConfig(seed=args.seed))
    summary = validate_dataset(args.output_dir)
    (data_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
