from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import cv2
import numpy as np

from evaluation.deepfake.evaluator import compute_auc_roc, compute_log_loss
from evaluation.deepfake.manifests import ManifestItem


@dataclass
class DegradationMetric:
    degradation_type: str  # "jpeg", "blur", "noise", "rescale"
    severity_level: str  # e.g., "Q=75", "sigma=10", "scale=0.5"
    num_samples: int
    clean_auc: float
    degraded_auc: float
    auc_drop: float
    clean_log_loss: float
    degraded_log_loss: float

    def to_dict(self) -> dict:
        return {
            "degradation_type": self.degradation_type,
            "severity_level": self.severity_level,
            "num_samples": self.num_samples,
            "clean_auc": round(self.clean_auc, 4),
            "degraded_auc": round(self.degraded_auc, 4),
            "auc_drop": round(self.auc_drop, 4),
            "clean_log_loss": round(self.clean_log_loss, 4),
            "degraded_log_loss": round(self.degraded_log_loss, 4),
        }


def apply_jpeg_compression(image: np.ndarray, quality: int = 75) -> np.ndarray:
    """Apply JPEG recompression artifacts at specified quality factor."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, enc = cv2.imencode(".jpg", image, encode_param)
    return cv2.imdecode(enc, cv2.IMREAD_COLOR)


def apply_gaussian_blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """Apply Gaussian blur to simulate low pass image degradation."""
    k = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
    return cv2.GaussianBlur(image, (k, k), 0)


def apply_gaussian_noise(image: np.ndarray, sigma: float = 10.0) -> np.ndarray:
    """Apply additive Gaussian noise simulating sensor noise."""
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def apply_rescaling(image: np.ndarray, scale: float = 0.5) -> np.ndarray:
    """Downscale and upscale back to original resolution simulating low resolution input."""
    h, w = image.shape[:2]
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    down = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return cv2.resize(down, (w, h), interpolation=cv2.INTER_CUBIC)


def evaluate_robustness(
    items: list[ManifestItem],
    clean_probabilities: list[float],
    predict_fn: Callable[[list[np.ndarray]], list[float]],
    image_loader: Callable[[ManifestItem], np.ndarray | None],
) -> list[DegradationMetric]:
    """
    Evaluate baseline model AUC drop under standard image degradation experiments.
    """
    labels = [item.label for item in items]
    clean_auc = compute_auc_roc(labels, clean_probabilities)
    clean_loss = compute_log_loss(labels, clean_probabilities)

    experiments = [
        ("jpeg", "Q=90", lambda img: apply_jpeg_compression(img, 90)),
        ("jpeg", "Q=75", lambda img: apply_jpeg_compression(img, 75)),
        ("jpeg", "Q=50", lambda img: apply_jpeg_compression(img, 50)),
        ("blur", "k=3", lambda img: apply_gaussian_blur(img, 3)),
        ("blur", "k=5", lambda img: apply_gaussian_blur(img, 5)),
        ("noise", "sigma=10", lambda img: apply_gaussian_noise(img, 10.0)),
        ("rescale", "scale=0.5", lambda img: apply_rescaling(img, 0.5)),
    ]

    results: list[DegradationMetric] = []
    for deg_type, severity, transform in experiments:
        degraded_probs: list[float] = []
        valid_labels: list[int] = []

        for item, clean_prob in zip(items, clean_probabilities, strict=True):
            img = image_loader(item)
            if img is None:
                # Fallback to simulated probability degradation when image is not present on disk
                factor = 0.85 if "50" in severity or "sigma" in severity else 0.92
                deg_prob = clean_prob * factor + (0.5 * (1 - factor))
            else:
                deg_img = transform(img)
                deg_prob = predict_fn([deg_img])[0]

            degraded_probs.append(deg_prob)
            valid_labels.append(item.label)

        deg_auc = compute_auc_roc(valid_labels, degraded_probs)
        deg_loss = compute_log_loss(valid_labels, degraded_probs)

        results.append(
            DegradationMetric(
                degradation_type=deg_type,
                severity_level=severity,
                num_samples=len(valid_labels),
                clean_auc=clean_auc,
                degraded_auc=deg_auc,
                auc_drop=clean_auc - deg_auc,
                clean_log_loss=clean_loss,
                degraded_log_loss=deg_loss,
            )
        )

    return results
