import pytest

from coolforge.config import PipelineConfig


@pytest.mark.parametrize("change", [
    {"processing_scale": 0}, {"processing_scale": 1.1}, {"processing_scale": float("nan")},
    {"blur_kernel": 2}, {"adaptive_block_size": 1}, {"adaptive_block_size": 20},
    {"morphology_kernel": True}, {"adaptive_c": float("inf")}, {"min_contour_area": -1},
    {"processing_scale": "1"}, {"unknown": 3},
])
def test_invalid_parameters(change):
    with pytest.raises(ValueError):
        PipelineConfig.from_dict(change)


def test_roundtrip(tmp_path):
    config = PipelineConfig(processing_scale=0.8, adaptive_c=5)
    target = tmp_path / "config.yaml"
    target.write_text(config.to_yaml())
    assert PipelineConfig.load(target) == config
    assert PipelineConfig.from_dict(config.to_dict()) == config


def test_mapping_required():
    with pytest.raises(ValueError):
        PipelineConfig.from_dict([])
