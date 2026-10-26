"""Shared data contracts for inspection and evaluation."""

from dataclasses import dataclass
from typing import Any

import numpy as np

from coolforge.config import PipelineConfig


@dataclass
class Sample:
    sample_id: str
    image: np.ndarray
    mask: np.ndarray
    metadata: dict[str, Any]


@dataclass
class PipelineResult:
    mask: np.ndarray
    annotated_bgr: np.ndarray
    detections: list[dict[str, Any]]
    stages_ms: dict[str, float]
    latency_ms: float
    config: PipelineConfig


@dataclass
class EvaluationResult:
    config: PipelineConfig
    quality: dict[str, float]
    timing: dict[str, float]
    stages_ms: dict[str, float]
    samples: list[dict[str, Any]]
    failures: list[dict[str, str]]

    @property
    def valid(self) -> bool:
        return bool(self.samples) and not self.failures
