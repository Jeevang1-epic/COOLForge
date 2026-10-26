"""The same OpenCV workload runs on stock builds and the COOL AMI."""

from time import perf_counter_ns

import cv2
import numpy as np

from coolforge.config import PipelineConfig
from coolforge.models import PipelineResult


class PipelineError(RuntimeError):
    """An image could not be inspected by OpenCV."""


def inspect(image: np.ndarray, config: PipelineConfig | None = None) -> PipelineResult:
    config = config or PipelineConfig()
    if (not isinstance(image, np.ndarray) or image.dtype != np.uint8 or not image.size
            or image.ndim != 3 or image.shape[2] != 3):
        raise ValueError("Expected a nonempty uint8 BGR image with three channels")
    height, width = image.shape[:2]
    if min(height, width) < 8 or height * width > 16_000_000:
        raise ValueError("Image dimensions must be at least 8 pixels and at most 16 MP")
    stages: dict[str, float] = {}
    start = checkpoint = perf_counter_ns()

    def mark(name: str) -> None:
        nonlocal checkpoint
        now = perf_counter_ns()
        stages[name] = (now - checkpoint) / 1e6
        checkpoint = now

    try:
        size = (max(3, round(width * config.processing_scale)),
                max(3, round(height * config.processing_scale)))
        resized = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        mark("resize")
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        mark("grayscale")
        blurred = cv2.GaussianBlur(gray, (config.blur_kernel,) * 2, 0)
        mark("blur")
        threshold = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
            config.adaptive_block_size, config.adaptive_c)
        mark("threshold")
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                          (config.morphology_kernel,) * 2)
        cleaned = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
        mark("morphology")
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        retained = np.zeros_like(cleaned)
        # Area is specified in original-image pixels, so comparisons survive scale changes.
        scale_area = size[0] * size[1] / (width * height)
        for contour in contours:
            if cv2.contourArea(contour) >= config.min_contour_area * scale_area:
                cv2.drawContours(retained, [contour], -1, 255, cv2.FILLED)
        # Preserve holes in thresholded defects rather than scoring filled-in backgrounds.
        retained = cv2.bitwise_and(retained, cleaned)
        mask = cv2.resize(retained, (width, height), interpolation=cv2.INTER_NEAREST)
        mark("contours")
        annotated = image.copy()
        detections = []
        full_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in full_contours:
            x, y, w, h = cv2.boundingRect(contour)
            detections.append({"bbox": [x, y, w, h], "area": float(cv2.contourArea(contour))})
            cv2.rectangle(annotated, (x, y), (x + w - 1, y + h - 1), (40, 180, 245), 1)
        mark("annotate")
    except cv2.error as exc:
        raise PipelineError(f"OpenCV inspection failed: {exc}") from exc
    return PipelineResult(mask, annotated, detections, stages,
                          (perf_counter_ns() - start) / 1e6, config)
