from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np

from evaluation.deepfake.manifests import DatasetManifest, ManifestItem


@dataclass
class ConfusionMatrix:
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total > 0 else 0.0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "tn": self.tn,
            "fn": self.fn,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
        }


@dataclass
class EvaluationMetrics:
    dataset_name: str
    num_samples: int
    decision_threshold: float
    auc_roc: float
    f1_score: float
    precision: float
    recall: float
    accuracy: float
    log_loss: float
    brier_score: float
    expected_calibration_error: float
    confusion_matrix: ConfusionMatrix
    generator_breakdown: dict[str, dict[str, float]]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["confusion_matrix"] = self.confusion_matrix.to_dict()
        return data


def compute_auc_roc(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Compute Area Under the Receiver Operating Characteristic Curve (ROC-AUC)."""
    y_true = np.array(labels)
    y_score = np.array(probabilities)
    pos_mask = y_true == 1
    neg_mask = y_true == 0
    n_pos = np.sum(pos_mask)
    n_neg = np.sum(neg_mask)

    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Rank probabilities (1-based ranks for Mann-Whitney U calculation)
    order = np.argsort(y_score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1)

    # Calculate Mann-Whitney U statistic
    pos_ranks_sum = np.sum(ranks[pos_mask])
    u_stat = pos_ranks_sum - (n_pos * (n_pos + 1)) / 2.0
    return float(u_stat / (n_pos * n_neg))


def compute_log_loss(labels: Sequence[int], probabilities: Sequence[float], eps: float = 1e-15) -> float:
    """Compute binary cross-entropy log loss."""
    probs = np.clip(np.array(probabilities), eps, 1.0 - eps)
    y_true = np.array(labels)
    loss = -(y_true * np.log(probs) + (1 - y_true) * np.log(1 - probs))
    return float(np.mean(loss))


def compute_brier_score(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    """Compute Brier score (mean squared difference between prediction probability and actual label)."""
    y_true = np.array(labels)
    probs = np.array(probabilities)
    return float(np.mean((probs - y_true) ** 2))


def compute_ece(labels: Sequence[int], probabilities: Sequence[float], n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    y_true = np.array(labels)
    probs = np.array(probabilities)
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (probs > bin_lower) & (probs <= bin_upper) if i > 0 else (probs >= bin_lower) & (probs <= bin_upper)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = np.mean(y_true[in_bin])
            bin_conf = np.mean(probs[in_bin])
            ece += (bin_size / len(y_true)) * abs(bin_acc - bin_conf)

    return float(ece)


def evaluate_predictions(
    items: list[ManifestItem],
    probabilities: list[float],
    dataset_name: str = "Test Set",
    threshold: float = 0.01,
) -> EvaluationMetrics:
    """Compute full evaluation metrics given items and predicted probabilities."""
    labels = [item.label for item in items]
    tp = fp = tn = fn = 0

    for label, prob in zip(labels, probabilities, strict=True):
        pred = 1 if prob >= threshold else 0
        if label == 1 and pred == 1:
            tp += 1
        elif label == 0 and pred == 1:
            fp += 1
        elif label == 0 and pred == 0:
            tn += 1
        else:
            fn += 1

    cm = ConfusionMatrix(tp=tp, fp=fp, tn=tn, fn=fn)
    auc = compute_auc_roc(labels, probabilities)
    log_loss = compute_log_loss(labels, probabilities)
    brier = compute_brier_score(labels, probabilities)
    ece = compute_ece(labels, probabilities)

    # Per-generator breakdown
    generators: dict[str, list[tuple[int, float]]] = {}
    for item, prob in zip(items, probabilities, strict=True):
        gen = item.generator_family
        if gen not in generators:
            generators[gen] = []
        generators[gen].append((item.label, prob))

    breakdown: dict[str, dict[str, float]] = {}
    for gen, gen_samples in generators.items():
        gen_labels = [s[0] for s in gen_samples]
        gen_probs = [s[1] for s in gen_samples]
        gen_preds = [1 if p >= threshold else 0 for p in gen_probs]
        gen_acc = sum(1 for l, p in zip(gen_labels, gen_preds, strict=True) if l == p) / len(gen_samples)
        gen_mean_prob = float(np.mean(gen_probs))
        breakdown[gen] = {
            "count": len(gen_samples),
            "accuracy": round(gen_acc, 4),
            "mean_probability": round(gen_mean_prob, 4),
        }

    return EvaluationMetrics(
        dataset_name=dataset_name,
        num_samples=len(items),
        decision_threshold=threshold,
        auc_roc=round(auc, 4),
        f1_score=cm.f1_score,
        precision=cm.precision,
        recall=cm.recall,
        accuracy=cm.accuracy,
        log_loss=round(log_loss, 4),
        brier_score=round(brier, 4),
        expected_calibration_error=round(ece, 4),
        confusion_matrix=cm,
        generator_breakdown=breakdown,
    )
