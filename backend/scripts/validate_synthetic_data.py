from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.data.validation import validate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a RazorShield synthetic dataset")
    parser.add_argument("--output-dir", type=Path, default=Path("../data/generated/default"))
    args = parser.parse_args()
    print(json.dumps(validate_dataset(args.output_dir), sort_keys=True))


if __name__ == "__main__":
    main()
