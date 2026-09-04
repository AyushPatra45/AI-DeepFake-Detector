from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.catalog import read_catalog
from evaluation.splitting import split_catalog, write_splits


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create deterministic identity/source-disjoint dataset manifests"
    )
    parser.add_argument(
        "--catalog", type=Path, default=Path("evaluation/manifests/catalog.csv")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("evaluation/manifests/splits")
    )
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=2205)
    args = parser.parse_args()

    result = split_catalog(
        read_catalog(args.catalog),
        ratios=(args.train_ratio, args.validation_ratio, args.test_ratio),
        seed=args.seed,
    )
    summary = write_splits(result, args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

