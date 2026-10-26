import cv2
import numpy as np
import pytest

from coolforge.config import PipelineConfig
from coolforge.dataset import generate_samples
from coolforge.evaluation import evaluate
from coolforge.pipeline import PipelineError, inspect


@pytest.mark.parametrize("scale", [1, 0.7, 0.25])
def test_pipeline_shapes_timings(scale):
    sample = generate_samples(2)[1]
    original = sample.image.copy()
    result = inspect(sample.image, PipelineConfig(processing_scale=scale))
    assert result.mask.shape == sample.mask.shape
    assert result.annotated_bgr.shape == sample.image.shape
    assert result.detections
    assert set(result.stages_ms) == {
        "resize", "grayscale", "blur", "threshold", "morphology", "contours", "annotate"}
    assert all(value >= 0 for value in result.stages_ms.values())
    assert result.latency_ms >= sum(result.stages_ms.values())
    np.testing.assert_array_equal(sample.image, original)


def test_clean_and_invalid_images():
    result = inspect(np.full((64, 64, 3), 180, np.uint8))
    assert result.detections == [] and not result.mask.any()
    for image in (np.zeros((0, 0, 3), np.uint8), np.zeros((10, 10)), None):
        with pytest.raises(ValueError):
            inspect(image)


def test_opencv_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise cv2.error("test failure")
    monkeypatch.setattr(cv2, "resize", fail)
    with pytest.raises(PipelineError):
        inspect(generate_samples(1)[0].image)


def test_evaluation_fails_closed():
    samples = generate_samples(5)
    good = evaluate(samples, PipelineConfig())
    assert good.valid and good.quality["f1"] > 0.6
    samples[1].image = np.zeros((0, 0, 3), np.uint8)
    bad = evaluate(samples, PipelineConfig())
    assert not bad.valid and len(bad.failures) == 1
    assert bad.quality["f1"] == 0
