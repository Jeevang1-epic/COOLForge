import json

import numpy as np
import pytest

from coolforge.dataset import dataset_hash, generate_samples, load_dataset, read_image, save_dataset


def test_seed_and_masks():
    samples = generate_samples(10)
    assert dataset_hash(samples) == dataset_hash(generate_samples(10))
    assert dataset_hash(samples) != dataset_hash(generate_samples(10, seed=43))
    assert not samples[0].mask.any()
    for sample in samples:
        assert sample.image.shape[:2] == sample.mask.shape
        assert set(np.unique(sample.mask)) <= {0, 255}
        if sample.metadata["defect"] != "clean":
            assert sample.mask.any()


def test_save_load_and_tampering(tmp_path):
    samples = generate_samples(5, width=96, height=64)
    manifest = save_dataset(samples, tmp_path)
    assert dataset_hash(load_dataset(tmp_path)) == dataset_hash(samples)
    with pytest.raises(FileExistsError):
        save_dataset(samples, tmp_path)
    data = json.loads(manifest.read_text())
    data["hash"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_dataset(tmp_path)
    data["samples"][0]["image"] = "../escape.png"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="escapes"):
        load_dataset(tmp_path)


def test_unreadable(tmp_path):
    path = tmp_path / "bad.png"
    path.write_bytes(b"garbage")
    with pytest.raises(ValueError, match="Unreadable"):
        read_image(path)
    with pytest.raises(ValueError, match="Supported"):
        read_image(tmp_path / "bad.txt")
