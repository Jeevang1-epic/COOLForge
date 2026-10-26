"""Foreground quality and latency statistics with explicit empty-mask semantics."""

import numpy as np


def confusion(prediction: np.ndarray, truth: np.ndarray) -> dict[str, int]:
    if prediction.shape != truth.shape or prediction.ndim != 2 or not prediction.size:
        raise ValueError("Masks must be nonempty, two-dimensional, and equally shaped")
    predicted, actual = prediction > 0, truth > 0
    return {"tp": int(np.count_nonzero(predicted & actual)),
            "fp": int(np.count_nonzero(predicted & ~actual)),
            "fn": int(np.count_nonzero(~predicted & actual))}


def quality_from_counts(tp: int, fp: int, fn: int) -> dict[str, float]:
    if min(tp, fp, fn) < 0:
        raise ValueError("Confusion counts cannot be negative")
    # Precision of an empty prediction is 1 only if truth is also empty.
    precision = tp / (tp + fp) if tp + fp else float(fn == 0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"precision": precision, "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0,
            "iou": tp / (tp + fp + fn) if tp + fp + fn else 1.0}


def mask_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    return quality_from_counts(**confusion(prediction, truth))


def latency_metrics(values_ms: list[float]) -> dict[str, float]:
    values = np.asarray(values_ms, dtype=float)
    if values.size == 0 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Latencies must be nonempty, finite, and nonnegative")
    mean = float(values.mean())
    return {"mean_ms": mean, "p50_ms": float(np.median(values)),
            "p95_ms": float(np.percentile(values, 95)),
            "throughput_ips": 1000 / mean if mean > 0 else 0.0}
