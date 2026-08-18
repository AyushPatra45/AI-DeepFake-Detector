from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from app.deepfake.model import HybridDeepfakeDetector


@dataclass(frozen=True)
class ModelRuntime:
    model: HybridDeepfakeDetector
    device: torch.device
    threshold: float
    temperature: float
    checkpoint_sha256: str

    def predict(self, faces_rgb: list[np.ndarray], *, batch_size: int = 4) -> list[float]:
        probabilities: list[float] = []
        for start in range(0, len(faces_rgb), batch_size):
            arrays = np.stack(faces_rgb[start : start + batch_size]).astype(np.float32) / 255
            batch = torch.from_numpy(arrays).permute(0, 3, 1, 2).to(self.device)
            with torch.inference_mode():
                logits = self.model(batch).flatten() / max(self.temperature, 1e-6)
                probabilities.extend(torch.sigmoid(logits).cpu().tolist())
        return [float(probability) for probability in probabilities]


def load_runtime(checkpoint_path: Path) -> ModelRuntime:
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if not isinstance(checkpoint, dict):
        raise ValueError("Unsupported checkpoint structure")

    state_dict = checkpoint.get("model_state_dict", checkpoint.get("state_dict", checkpoint))
    if not isinstance(state_dict, dict):
        raise ValueError("Checkpoint does not contain a model state dictionary")
    cleaned = {
        key.removeprefix("module.").removeprefix("_orig_mod."): value
        for key, value in state_dict.items()
    }
    model = HybridDeepfakeDetector()
    incompatible = model.load_state_dict(cleaned, strict=False)
    critical_prefixes = ("spatial_backbone", "freq_conv", "gate_fc", "classifier")
    critical_missing = [
        key for key in incompatible.missing_keys if key.startswith(critical_prefixes)
    ]
    if critical_missing:
        raise ValueError(f"Checkpoint is missing critical weights: {critical_missing[:5]}")

    model.to(device)
    model.eval()
    return ModelRuntime(
        model=model,
        device=device,
        threshold=float(checkpoint.get("optimal_threshold", 0.5)),
        temperature=float(checkpoint.get("temperature", 1.0)),
        checkpoint_sha256=_sha256(checkpoint_path),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
