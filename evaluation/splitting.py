from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from evaluation.catalog import CATALOG_FIELDS, CatalogRecord

SPLITS = ("train", "validation", "test")


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parents = list(range(size))

    def find(self, item: int) -> int:
        while self.parents[item] != item:
            self.parents[item] = self.parents[self.parents[item]]
            item = self.parents[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parents[right_root] = left_root


@dataclass(frozen=True)
class SplitResult:
    assignments: dict[str, list[CatalogRecord]]
    seed: int
    ratios: tuple[float, float, float]


def identity_components(records: list[CatalogRecord]) -> list[list[CatalogRecord]]:
    if not records:
        raise ValueError("Cannot split an empty catalog")
    union_find = UnionFind(len(records))
    constraint_owner: dict[str, int] = {}
    for index, record in enumerate(records):
        constraints = [
            *(f"identity:{identity}" for identity in record.identity_ids),
            f"source:{record.source_group}",
            f"sha256:{record.sha256}",
        ]
        for constraint in constraints:
            previous = constraint_owner.setdefault(constraint, index)
            union_find.union(index, previous)

    components: dict[int, list[CatalogRecord]] = defaultdict(list)
    for index, record in enumerate(records):
        components[union_find.find(index)].append(record)
    return list(components.values())


def split_catalog(
    records: list[CatalogRecord],
    *,
    ratios: tuple[float, float, float] = (0.7, 0.15, 0.15),
    seed: int = 2205,
) -> SplitResult:
    if any(ratio <= 0 for ratio in ratios) or abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("Split ratios must be positive and sum to 1")
    components = identity_components(records)
    if len(components) < len(SPLITS):
        raise ValueError(
            "At least three disconnected identity/source groups are required for "
            "non-empty train, validation, and test splits"
        )

    randomizer = random.Random(seed)
    randomizer.shuffle(components)
    components.sort(key=len, reverse=True)
    assignments: dict[str, list[CatalogRecord]] = {split: [] for split in SPLITS}
    target_total = {
        split: len(records) * ratio
        for split, ratio in zip(SPLITS, ratios, strict=True)
    }
    label_totals = Counter(record.label for record in records)
    target_labels = {
        split: {label: count * ratio for label, count in label_totals.items()}
        for split, ratio in zip(SPLITS, ratios, strict=True)
    }

    for component_index, component in enumerate(components):
        if component_index < len(SPLITS):
            chosen = SPLITS[component_index]
        else:
            component_labels = Counter(record.label for record in component)

            def cost(
                split: str,
                component_size: int = len(component),
                component_label_counts: Counter[int] = component_labels,
            ) -> tuple[float, int]:
                projected_total = len(assignments[split]) + component_size
                size_error = abs(projected_total - target_total[split]) / max(
                    target_total[split], 1
                )
                existing_labels = Counter(record.label for record in assignments[split])
                label_error = sum(
                    abs(existing_labels[label] + component_label_counts[label] - target)
                    / max(target, 1)
                    for label, target in target_labels[split].items()
                )
                return size_error + label_error, len(assignments[split])

            chosen = min(SPLITS, key=cost)
        assignments[chosen].extend(component)

    audit_split_integrity(assignments)
    for split_records in assignments.values():
        split_records.sort(key=lambda record: record.sample_id)
    return SplitResult(assignments=assignments, seed=seed, ratios=ratios)


def audit_split_integrity(assignments: dict[str, list[CatalogRecord]]) -> None:
    seen: dict[str, str] = {}
    for split, records in assignments.items():
        for record in records:
            constraints = [
                *(f"identity:{identity}" for identity in record.identity_ids),
                f"source:{record.source_group}",
                f"sha256:{record.sha256}",
            ]
            for constraint in constraints:
                previous = seen.setdefault(constraint, split)
                if previous != split:
                    raise ValueError(
                        f"Leakage detected: {constraint} appears in {previous} and {split}"
                    )


def write_splits(result: SplitResult, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {
        "seed": result.seed,
        "ratios": dict(zip(SPLITS, result.ratios, strict=True)),
        "splits": {},
        "integrity": "passed: identities, source groups, and file hashes are disjoint",
    }
    for split, records in result.assignments.items():
        manifest_path = output_dir / f"{split}.csv"
        with manifest_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=CATALOG_FIELDS)
            writer.writeheader()
            writer.writerows(record.as_row() for record in records)
        labels = Counter(record.label for record in records)
        summary["splits"][split] = {
            "samples": len(records),
            "real": labels[0],
            "fake": labels[1],
            "identities": len(
                {identity for record in records for identity in record.identity_ids}
            ),
            "source_groups": len({record.source_group for record in records}),
        }
    (output_dir / "split_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
