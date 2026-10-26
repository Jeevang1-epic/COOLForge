"""Evaluation fails closed: a skipped image cannot make a candidate look better."""

import logging

import numpy as np

from coolforge.config import PipelineConfig
from coolforge.metrics import confusion, latency_metrics, mask_metrics, quality_from_counts
from coolforge.models import EvaluationResult, Sample
from coolforge.pipeline import PipelineError, inspect

logger = logging.getLogger(__name__)


def evaluate(samples: list[Sample], config: PipelineConfig,
             repetitions: int = 1, warmups: int = 0) -> EvaluationResult:
    if not samples or repetitions < 1 or warmups < 0:
        raise ValueError("Evaluation needs samples, positive repetitions, and nonnegative warmups")
    records, failures, latencies = [], [], []
    stages: dict[str, list[float]] = {}
    counts = {"tp": 0, "fp": 0, "fn": 0}
    for sample in samples:
        try:
            for _ in range(warmups):
                inspect(sample.image, config)
            output = None
            for _ in range(repetitions):
                output = inspect(sample.image, config)
                latencies.append(output.latency_ms)
                for name, value in output.stages_ms.items():
                    stages.setdefault(name, []).append(value)
            assert output is not None
            quality = mask_metrics(output.mask, sample.mask)
            for name, value in confusion(output.mask, sample.mask).items():
                counts[name] += value
            records.append({"id": sample.sample_id, "defect": sample.metadata.get("defect"),
                            **quality, "latency_ms": output.latency_ms})
        except (ValueError, PipelineError) as exc:
            logger.warning("Sample %s failed: %s", sample.sample_id, exc)
            failures.append({"id": sample.sample_id, "error": str(exc)})
    quality = quality_from_counts(**counts)
    quality["macro_f1"] = float(np.mean([r["f1"] for r in records])) if records else 0.0
    if failures:
        quality = dict.fromkeys(quality, 0.0)
    timing = latency_metrics(latencies) if latencies else dict.fromkeys(
        ("mean_ms", "p50_ms", "p95_ms", "throughput_ips"), 0.0)
    return EvaluationResult(config, quality, timing,
                            {k: float(np.mean(v)) for k, v in stages.items()}, records, failures)
