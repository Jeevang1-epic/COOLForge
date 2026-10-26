from copy import deepcopy

import pytest

from coolforge.benchmark import compare, markdown_report, run_benchmark, validate_artifact
from coolforge.config import PipelineConfig
from coolforge.dataset import generate_samples


@pytest.fixture
def measurement():
    return run_benchmark(
        generate_samples(2, width=96, height=64), PipelineConfig(), warmups=0, iterations=1
    )


def pair(measurement):
    # Explicitly synthetic test pair; never saved or loaded by the product UI.
    stock, cool = deepcopy(measurement), deepcopy(measurement)
    for name, value in (("stock", stock), ("cool", cool)):
        value["name"] = name
        value["environment"].update(
            opencv5_verified=True, architecture_arm64=True, cool_verified=name == "cool"
        )
        value["environment"].update(
            cv2_version="5.0.0",
            machine="aarch64",
            cool_root_exists=True,
            cv2_file="/opt/cool/cv2.so" if name == "cool" else "/stock/cv2.so",
            build_excerpt=["Custom HAL: KleidiCV"],
        )
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


def test_missing_stages_are_rejected(measurement):
    measurement["evaluation"]["stages_ms"] = {}
    with pytest.raises(ValueError, match="stages"):
        validate_artifact(measurement)


def test_version_mismatch_blocks_speedup(measurement):
    stock, cool = pair(measurement)
    cool["environment"]["cv2_version"] = "5.1.0-dev"
    assert not compare(stock, cool)["comparable"]


def test_contradictory_verification_is_rejected(measurement):
    measurement["environment"]["opencv5_verified"] = not measurement["environment"][
        "opencv5_verified"
    ]
    with pytest.raises(ValueError, match="contradicts"):
        validate_artifact(measurement)
