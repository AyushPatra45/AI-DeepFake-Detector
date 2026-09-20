from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManifestItem:
    item_id: str
    relative_path: str
    label: int  # 0 = real, 1 = fake
    identity_id: str
    dataset_name: str
    generator_family: str  # e.g., "real", "Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures", "Celeb-DF"
    sha256: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ManifestItem:
        return cls(
            item_id=data["item_id"],
            relative_path=data["relative_path"],
            label=int(data["label"]),
            identity_id=data["identity_id"],
            dataset_name=data["dataset_name"],
            generator_family=data["generator_family"],
            sha256=data.get("sha256", ""),
        )


@dataclass
class DatasetManifest:
    name: str
    description: str
    split: str  # "train", "val", "test", "cross_test"
    items: list[ManifestItem]

    @property
    def num_real(self) -> int:
        return sum(1 for item in self.items if item.label == 0)

    @property
    def num_fake(self) -> int:
        return sum(1 for item in self.items if item.label == 1)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def identities(self) -> set[str]:
        return {item.identity_id for item in self.items if item.identity_id}

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "description": self.description,
            "split": self.split,
            "total_items": self.total,
            "num_real": self.num_real,
            "num_fake": self.num_fake,
            "unique_identities": len(self.identities),
            "items": [item.to_dict() for item in self.items],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> DatasetManifest:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = [ManifestItem.from_dict(item_data) for item_data in data["items"]]
        return cls(
            name=data["name"],
            description=data["description"],
            split=data["split"],
            items=items,
        )


def check_identity_disjointness(manifest_a: DatasetManifest, manifest_b: DatasetManifest) -> tuple[bool, set[str]]:
    """Verify that two manifests share no identity IDs."""
    intersection = manifest_a.identities.intersection(manifest_b.identities)
    return len(intersection) == 0, intersection


def generate_benchmark_manifests(output_dir: Path, seed: int = 42) -> dict[str, Path]:
    """Generate fixed deterministic benchmark manifests for FF++ subset and Celeb-DF subset."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    # 1. FF++ In-Domain Test Manifest (50 real, 50 fake across 20 disjoint identities id_101..id_120)
    ffpp_items: list[ManifestItem] = []
    generators = ["Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures"]
    for i in range(1, 51):
        ident = f"ffpp_id_{100 + (i % 20) + 1}"
        # Real
        ffpp_items.append(
            ManifestItem(
                item_id=f"ffpp_real_{i:03d}",
                relative_path=f"ffpp/real/real_{i:03d}.png",
                label=0,
                identity_id=ident,
                dataset_name="FaceForensics++",
                generator_family="real",
                sha256=hashlib.sha256(f"ffpp_real_{i}".encode()).hexdigest(),
            )
        )
        # Fake
        gen = generators[i % len(generators)]
        ffpp_items.append(
            ManifestItem(
                item_id=f"ffpp_fake_{i:03d}",
                relative_path=f"ffpp/fake/{gen.lower()}_{i:03d}.png",
                label=1,
                identity_id=ident,
                dataset_name="FaceForensics++",
                generator_family=gen,
                sha256=hashlib.sha256(f"ffpp_fake_{i}".encode()).hexdigest(),
            )
        )

    ffpp_manifest = DatasetManifest(
        name="FaceForensics++ Test Subset (In-Domain)",
        description="Fixed identity-disjoint test subset of FaceForensics++ (50 real, 50 fake)",
        split="test",
        items=ffpp_items,
    )
    ffpp_path = output_dir / "ffpp_indomain_test.json"
    ffpp_manifest.save(ffpp_path)

    # 2. Celeb-DF v2 Cross-Dataset Test Manifest (25 real, 25 fake across identities celeb_201..celeb_210)
    celeb_items: list[ManifestItem] = []
    for i in range(1, 26):
        ident = f"celeb_id_{200 + (i % 10) + 1}"
        # Real
        celeb_items.append(
            ManifestItem(
                item_id=f"celeb_real_{i:03d}",
                relative_path=f"celebdf/real/celeb_real_{i:03d}.png",
                label=0,
                identity_id=ident,
                dataset_name="Celeb-DF-v2",
                generator_family="real",
                sha256=hashlib.sha256(f"celeb_real_{i}".encode()).hexdigest(),
            )
        )
        # Fake
        celeb_items.append(
            ManifestItem(
                item_id=f"celeb_fake_{i:03d}",
                relative_path=f"celebdf/fake/celeb_fake_{i:03d}.png",
                label=1,
                identity_id=ident,
                dataset_name="Celeb-DF-v2",
                generator_family="Celeb-DF-Synthesis",
                sha256=hashlib.sha256(f"celeb_fake_{i}".encode()).hexdigest(),
            )
        )

    celeb_manifest = DatasetManifest(
        name="Celeb-DF v2 Test Subset (Cross-Dataset)",
        description="Fixed out-of-distribution cross-dataset test subset of Celeb-DF v2 (25 real, 25 fake)",
        split="cross_test",
        items=celeb_items,
    )
    celeb_path = output_dir / "celebdf_cross_test.json"
    celeb_manifest.save(celeb_path)

    return {
        "ffpp_indomain_test": ffpp_path,
        "celebdf_cross_test": celeb_path,
    }
