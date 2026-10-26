"""Synthetic surfaces with exact raster masks and content-addressed manifests."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from coolforge.models import Sample

DEFECTS = ("clean", "scratch", "crack", "pit", "blob")
GENERATOR_VERSION = 1


def generate_samples(
    count: int = 50, seed: int = 42, width: int = 384, height: int = 256
) -> list[Sample]:
    if not 1 <= count <= 1000 or not 64 <= min(width, height) <= max(width, height) <= 4096:
        raise ValueError("Use 1–1000 samples and dimensions between 64 and 4096")
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:height, :width]
    samples = []
    for index in range(count):
        kind = DEFECTS[index % len(DEFECTS)]
        surface = (
            175
            + 23 * xx / width
            + 12 * yy / height
            + 2 * np.sin(xx / 8)
            + 1.5 * np.cos(yy / 13)
            + rng.normal(0, 2.2, (height, width))
        )
        mask = np.zeros((height, width), np.uint8)
        for _ in range(int(rng.integers(1, 4))):
            x = int(rng.integers(width // 8, 7 * width // 8))
            y = int(rng.integers(height // 8, 7 * height // 8))
            if kind == "scratch":
                end = (
                    min(width - 8, x + int(rng.integers(20, width // 3))),
                    min(height - 8, y + int(rng.integers(-15, 16))),
                )
                cv2.line(mask, (x, y), end, 255, int(rng.integers(2, 6)))
            elif kind == "crack":
                points = np.array(
                    [
                        (x, y),
                        (min(width - 5, x + 15), max(5, y - 12)),
                        (min(width - 5, x + 32), min(height - 5, y + 7)),
                        (min(width - 5, x + 55), max(5, y - 15)),
                    ],
                    np.int32,
                )
                cv2.polylines(mask, [points], False, 255, int(rng.integers(1, 4)))
            elif kind == "pit":
                cv2.circle(mask, (x, y), int(rng.integers(3, 11)), 255, -1)
            elif kind == "blob":
                angles = np.linspace(0, 2 * np.pi, 8, endpoint=False)
                radii = rng.uniform(5, 15, 8)
                points = np.column_stack(
                    (x + radii * np.cos(angles), y + radii * np.sin(angles))
                ).astype(np.int32)
                cv2.fillPoly(mask, [points], 255)
        # Masks describe precisely the pixels altered, not an inferred segmentation.
        surface[mask > 0] -= rng.uniform(65, 110)
        gray = np.clip(surface, 0, 255).astype(np.uint8)
        image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        samples.append(
            Sample(
                f"{index:04d}_{kind}",
                image,
                mask,
                {
                    "seed": seed,
                    "index": index,
                    "defect": kind,
                    "generator_version": GENERATOR_VERSION,
                },
            )
        )
    return samples


def dataset_hash(samples: list[Sample]) -> str:
    digest = hashlib.sha256()
    for sample in samples:
        digest.update(sample.sample_id.encode())
        for array in (sample.image, sample.mask):
            digest.update(str((array.shape, array.dtype.str)).encode())
            digest.update(array.tobytes())
    return digest.hexdigest()


def save_dataset(samples: list[Sample], directory: str | Path) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "manifest.json").exists():
        raise FileExistsError(f"Dataset exists: {directory}; use a new output directory")
    records = []
    for sample in samples:
        image_name, mask_name = f"{sample.sample_id}.png", f"{sample.sample_id}_mask.png"
        for name, array in ((image_name, sample.image), (mask_name, sample.mask)):
            # imencode + tofile also supports Unicode paths on Windows.
            ok, encoded = cv2.imencode(".png", array)
            if not ok:
                raise OSError(f"Could not encode {name}")
            encoded.tofile(directory / name)
        records.append(
            {
                "id": sample.sample_id,
                "image": image_name,
                "mask": mask_name,
                "metadata": sample.metadata,
            }
        )
    manifest = directory / "manifest.json"
    manifest.write_text(
        json.dumps(
            {"schema_version": 1, "hash": dataset_hash(samples), "samples": records}, indent=2
        ),
        encoding="utf-8",
    )
    return manifest


def read_image(path: str | Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("Supported formats: PNG and JPEG")
    raw = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(raw, flags) if raw.size else None
    if image is None or not image.size:
        raise ValueError(f"Unreadable image: {path.name}")
    return image


def load_dataset(directory: str | Path) -> list[Sample]:
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not manifest.get("samples"):
        raise ValueError("Invalid dataset manifest")
    samples = []
    for record in manifest["samples"]:
        paths = [(root / record[key]).resolve() for key in ("image", "mask")]
        if any(not p.is_relative_to(root) for p in paths):
            raise ValueError("Manifest path escapes dataset directory")
        image, mask = read_image(paths[0]), read_image(paths[1], cv2.IMREAD_GRAYSCALE)
        if image.shape[:2] != mask.shape or not np.isin(mask, [0, 255]).all():
            raise ValueError("Ground truth must be a matching binary mask")
        samples.append(Sample(record["id"], image, mask, record["metadata"]))
    if dataset_hash(samples) != manifest["hash"]:
        raise ValueError("Dataset hash mismatch: image, order, or mask changed")
    return samples
