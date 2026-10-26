from copy import deepcopy

import pytest

from coolforge.benchmark import compare, markdown_report, run_benchmark, validate_artifact
from coolforge.config import PipelineConfig
from coolforge.dataset import generate_samples


@pytest.fixture
def measurement():
    return run_benchmark(generate_samples(2, width=96, height=64), PipelineConfig(),
                         warmups=0, iterations=1)


def pair(measurement):
    # Explicitly synthetic test pair; never saved or loaded by the product UI.
    stock, cool = deepcopy(measurement), deepcopy(measurement)
    for name, value in (("stock", stock), ("cool", cool)):
        value["name"] = name
        value["environment"].update(opencv5_verified=True, architecture_arm64=True,
                                    cool_verified=name == "cool")
    return stock, cool


def test_measured_schema_and_missing_side(measurement):
    assert validate_artifact(measurement) is measurement
    assert compare(measurement, None)["warnings"] == ["COOL unavailable"]
    assert compare(None, measurement)["warnings"] == ["baseline unavailable"]
    assert "unavailable" in markdown_report(None, None)


def test_comparison_and_zero_division(measurement):
    stock, cool = pair(measurement)
    stock["evaluation"]["timing"]["mean_ms"] = 2
    cool["evaluation"]["timing"]["mean_ms"] = 1
    assert compare(stock, cool)["speedup"] == 2
    cool["evaluation"]["timing"]["mean_ms"] = 0
    assert compare(stock, cool)["speedup"] is None


@pytest.mark.parametrize("key", ["dataset_sha256", "source_sha256", "iterations"])
def test_mismatched_artifacts_refused(measurement, key):
    stock, cool = pair(measurement)
    cool[key] = "f" * 64 if key.endswith("sha256") else 5
    assert not compare(stock, cool)["comparable"]


def test_local_cannot_claim_cool(measurement):
    assert not compare(measurement, measurement)["comparable"]
    measurement["artifact_kind"] = "demo"
    with pytest.raises(ValueError, match="fixtures excluded"):
        validate_artifact(measurement)


def test_malformed_and_nonfinite(measurement):
    with pytest.raises(ValueError):
        validate_artifact({})
    measurement["evaluation"]["timing"]["p95_ms"] = float("nan")
    with pytest.raises(ValueError):
        validate_artifact(measurement)
