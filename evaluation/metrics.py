from __future__ import annotations

import math


def _validate(labels: list[int], scores: list[float]) -> None:
    if not labels or len(labels) != len(scores):
        raise ValueError("Labels and scores must be non-empty and have equal length")
    if any(label not in {0, 1} for label in labels):
        raise ValueError("Labels must be binary (0 or 1)")
    if any(not math.isfinite(score) or not 0 <= score <= 1 for score in scores):
        raise ValueError("Scores must be finite probabilities between 0 and 1")


def roc_auc(labels: list[int], scores: list[float]) -> float | None:
    _validate(labels, scores)
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None

    ranked = sorted(zip(scores, labels, strict=True), key=lambda item: item[0])
    positive_rank_sum = 0.0
    index = 0
    while index < len(ranked):
        end = index + 1
        while end < len(ranked) and ranked[end][0] == ranked[index][0]:
            end += 1
        average_rank = ((index + 1) + end) / 2
        positive_rank_sum += average_rank * sum(label for _, label in ranked[index:end])
        index = end
    return (positive_rank_sum - positives * (positives + 1) / 2) / (
        positives * negatives
    )


def expected_calibration_error(
    labels: list[int], scores: list[float], *, bins: int = 10
) -> float:
    _validate(labels, scores)
    if bins <= 0:
        raise ValueError("bins must be positive")
    total_error = 0.0
    for bin_index in range(bins):
        lower = bin_index / bins
        upper = (bin_index + 1) / bins
        members = [
            index
            for index, score in enumerate(scores)
            if lower <= score < upper or (bin_index == bins - 1 and score == 1)
        ]
        if not members:
            continue
        confidence = sum(scores[index] for index in members) / len(members)
        accuracy = sum(labels[index] for index in members) / len(members)
        total_error += len(members) / len(labels) * abs(accuracy - confidence)
    return total_error


def binary_metrics(
    labels: list[int], scores: list[float], *, threshold: float
) -> dict[str, float | int | None | dict[str, int]]:
    _validate(labels, scores)
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1")
    predictions = [int(score >= threshold) for score in scores]
    true_positive = sum(p == 1 and y == 1 for p, y in zip(predictions, labels, strict=True))
    true_negative = sum(p == 0 and y == 0 for p, y in zip(predictions, labels, strict=True))
    false_positive = sum(p == 1 and y == 0 for p, y in zip(predictions, labels, strict=True))
    false_negative = sum(p == 0 and y == 1 for p, y in zip(predictions, labels, strict=True))

    def divide(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    precision = divide(true_positive, true_positive + false_positive)
    recall = divide(true_positive, true_positive + false_negative)
    specificity = divide(true_negative, true_negative + false_positive)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "samples": len(labels),
        "threshold": threshold,
        "accuracy": (true_positive + true_negative) / len(labels),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "roc_auc": roc_auc(labels, scores),
        "brier_score": sum(
            (score - label) ** 2
            for label, score in zip(labels, scores, strict=True)
        )
        / len(labels),
        "expected_calibration_error_10_bins": expected_calibration_error(labels, scores),
        "confusion_matrix": {
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_positive": true_positive,
        },
    }
