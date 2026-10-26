"""Immutable configurations; invalid parameters never reach OpenCV."""

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PipelineConfig:
    processing_scale: float = 1.0
    blur_kernel: int = 3
    adaptive_block_size: int = 41
    adaptive_c: float = 8.0
    morphology_kernel: int = 1
    min_contour_area: float = 5.0

    def __post_init__(self) -> None:
        for name in ("processing_scale", "adaptive_c", "min_contour_area"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0.25 <= self.processing_scale <= 1:
            raise ValueError("processing_scale must be between 0.25 and 1")
        for name, maximum in (
            ("blur_kernel", 15),
            ("adaptive_block_size", 101),
            ("morphology_kernel", 15),
        ):
            value = getattr(self, name)
            minimum = 3 if name == "adaptive_block_size" else 1
            if type(value) is not int or not minimum <= value <= maximum or value % 2 != 1:
                raise ValueError(f"{name} must be an odd integer in [{minimum}, {maximum}]")
        if not -20 <= self.adaptive_c <= 50:
            raise ValueError("adaptive_c must be between -20 and 50")
        if not 0 <= self.min_contour_area <= 10000:
            raise ValueError("min_contour_area must be between 0 and 10000")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PipelineConfig":
        if not isinstance(value, dict):
            raise ValueError("Configuration must be a mapping")
        try:
            return cls(**value)
        except TypeError as exc:
            raise ValueError(f"Unknown or malformed configuration: {exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> "PipelineConfig":
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        value = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
        return cls.from_dict(value)

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False)
