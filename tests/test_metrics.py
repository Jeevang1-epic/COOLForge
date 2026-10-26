import numpy as np
import pytest

from coolforge.metrics import latency_metrics, mask_metrics


@pytest.mark.parametrize(
    "prediction,truth,f1,iou",
    [
        ([[1, 0]], [[1, 0]], 1, 1),
        ([[1, 0]], [[0, 1]], 0, 0),
        ([[0, 0]], [[0, 0]], 1, 1),
        ([[0, 0]], [[1, 0]], 0, 0),
        ([[1, 0]], [[0, 0]], 0, 0),
        ([[1, 1]], [[1, 0]], 2 / 3, 1 / 2),
    ],
)
def test_foreground_edges(prediction, truth, f1, iou):
    result = mask_metrics(np.array(prediction), np.array(truth))
    assert result["f1"] == pytest.approx(f1)
    assert result["iou"] == pytest.approx(iou)


def test_shape_mismatch():
    with pytest.raises(ValueError):
        mask_metrics(np.zeros((2, 2)), np.zeros((3, 3)))


def test_latency_statistics():
    result = latency_metrics([1, 2, 3])
    assert result["mean_ms"] == result["p50_ms"] == 2
    assert result["p95_ms"] == pytest.approx(2.9)
    assert result["throughput_ips"] == 500
    assert latency_metrics([0])["throughput_ips"] == 0


@pytest.mark.parametrize("values", [[], [-1], [float("nan")]])
def test_bad_latencies(values):
    with pytest.raises(ValueError):
        latency_metrics(values)
