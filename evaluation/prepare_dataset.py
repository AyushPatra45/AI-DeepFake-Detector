from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from evaluation.catalog import build_catalog, write_catalog


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate dataset metadata and create a checksummed image catalog"
    )
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--dataset", required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation/manifests/catalog.csv")
    )
    args = parser.parse_args()

    records = build_catalog(
        source_root=args.source_root,
        metadata_path=args.metadata,
        dataset=args.dataset,
    )
    write_catalog(records, args.output)
    counts = Counter(record.label for record in records)
    print(
        f"Wrote {len(records)} samples ({counts[0]} real, {counts[1]} fake) "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()

