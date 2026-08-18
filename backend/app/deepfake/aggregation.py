from __future__ import annotations

import numpy as np


def softmax_weighted_score(scores: list[float], *, temperature: float = 0.1) -> float:
    if not scores:
        raise ValueError("At least one score is required")
    values = np.clip(np.asarray(scores, dtype=np.float64), 0, 1)
    scaled = values / max(temperature, 1e-8)
    weights = np.exp(scaled - scaled.max())
    weights /= weights.sum()
    return float(np.dot(values, weights))
