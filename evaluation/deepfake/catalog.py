from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

CATALOG_FIELDS = (
    "sample_id",
    "path",
    "label",
    "identity_ids",
    "source_group",
    "dataset",
    "manipulation",
    "sha256",
)
REQUIRED_METADATA_FIELDS = {"path", "label", "identity_ids", "source_group"}
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class CatalogRecord:
    sample_id: str
    path: str
    label: int
    identity_ids: tuple[str, ...]
    source_group: str
    dataset: str
    manipulation: str
    sha256: str

    def as_row(self) -> dict[str, str | int]:
        return {
            "sample_id": self.sample_id,
            "path": self.path,
            "label": self.label,
            "identity_ids": ";".join(self.identity_ids),
            "source_group": self.source_group,
            "dataset": self.dataset,
            "manipulation": self.manipulation,
            "sha256": self.sha256,
        }


def normalise_label(value: str) -> int:
    normalised = value.strip().lower()
    if normalised in {"1", "fake", "manipulated", "deepfake"}:
        return 1
    if normalised in {"0", "real", "authentic", "original"}:
        return 0
    raise ValueError(f"Unsupported label {value!r}; use real/fake or 0/1")


def normalise_identities(value: str) -> tuple[str, ...]:
    identities = tuple(sorted({item.strip() for item in value.split(";") if item.strip()}))
    if not identities:
        raise ValueError("identity_ids must contain at least one identity")
    return identities


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_catalog(
    *, source_root: Path, metadata_path: Path, dataset: str
) -> list[CatalogRecord]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ValueError(f"Dataset root does not exist: {source_root}")
    if not dataset.strip():
        raise ValueError("Dataset name cannot be empty")

    records: list[CatalogRecord] = []
    seen_paths: set[str] = set()
    seen_hashes: dict[str, str] = {}
    with metadata_path.open(newline="", encoding="utf-8-sig") as metadata_file:
        reader = csv.DictReader(metadata_file)
        missing = REQUIRED_METADATA_FIELDS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Metadata CSV is missing columns: {', '.join(sorted(missing))}")

        for line_number, row in enumerate(reader, start=2):
            relative_path = Path(row["path"].strip())
            if relative_path.is_absolute():
                raise ValueError(f"Line {line_number}: path must be relative to the dataset root")
            media_path = (source_root / relative_path).resolve()
            try:
                media_path.relative_to(source_root)
            except ValueError as error:
                raise ValueError(f"Line {line_number}: path escapes the dataset root") from error
            if media_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                raise ValueError(
                    f"Line {line_number}: unsupported image type {media_path.suffix!r}"
                )
            if not media_path.is_file():
                raise ValueError(f"Line {line_number}: media file does not exist: {relative_path}")

            portable_path = relative_path.as_posix()
            if portable_path in seen_paths:
                raise ValueError(f"Line {line_number}: duplicate path {portable_path!r}")
            seen_paths.add(portable_path)

            source_group = row["source_group"].strip()
            if not source_group:
                raise ValueError(f"Line {line_number}: source_group cannot be empty")
            checksum = sha256_file(media_path)
            if checksum in seen_hashes:
                raise ValueError(
                    f"Line {line_number}: duplicate media content also appears at "
                    f"{seen_hashes[checksum]!r}"
                )
            seen_hashes[checksum] = portable_path
            records.append(
                CatalogRecord(
                    sample_id=f"{dataset.strip()}-{checksum[:16]}-{line_number - 1:06d}",
                    path=portable_path,
                    label=normalise_label(row["label"]),
                    identity_ids=normalise_identities(row["identity_ids"]),
                    source_group=source_group,
                    dataset=dataset.strip(),
                    manipulation=(row.get("manipulation") or "unspecified").strip()
                    or "unspecified",
                    sha256=checksum,
                )
            )

    if not records:
        raise ValueError("Metadata CSV contains no samples")
    return records


def write_catalog(records: list[CatalogRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(record.as_row() for record in records)


def read_catalog(path: Path) -> list[CatalogRecord]:
    records: list[CatalogRecord] = []
    with path.open(newline="", encoding="utf-8-sig") as catalog_file:
        reader = csv.DictReader(catalog_file)
        missing = set(CATALOG_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Catalog is missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            records.append(
                CatalogRecord(
                    sample_id=row["sample_id"],
                    path=row["path"],
                    label=normalise_label(row["label"]),
                    identity_ids=normalise_identities(row["identity_ids"]),
                    source_group=row["source_group"],
                    dataset=row["dataset"],
                    manipulation=row["manipulation"],
                    sha256=row["sha256"],
                )
            )
    return records
