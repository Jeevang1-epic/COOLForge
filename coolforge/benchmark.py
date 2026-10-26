"""Benchmark artifact validation and comparisons that refuse mismatched evidence."""

import hashlib
import json
import math
import re
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2

from coolforge.config import PipelineConfig
from coolforge.dataset import dataset_hash
from coolforge.environment import inspect_environment, runtime_identity
from coolforge.evaluation import evaluate
from coolforge.models import Sample

ROOT = Path(__file__).resolve().parents[1]


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "coolforge").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_benchmark(
    samples: list[Sample],
    config: PipelineConfig,
    name: str = "local",
    warmups: int = 5,
    iterations: int = 30,
    threads: int = 1,
) -> dict[str, Any]:
    if name not in {"local", "stock", "cool"} or threads < 1:
        raise ValueError("Use local/stock/cool and positive thread count")
    previous_threads = cv2.getNumThreads()
    try:
        cv2.setNumThreads(threads)
        environment = inspect_environment().to_dict()
        if name == "cool" and not environment["cool_verified"]:
            raise ValueError("COOL label requires verified COOL environment")
        if name == "stock" and (
            not environment["opencv5_verified"]
            or environment["cool_verified"]
            or environment["cv2_file"].replace("\\", "/").startswith("/opt/cool/")
        ):
            raise ValueError("Stock baseline requires OpenCV 5 outside the COOL installation")
        result = evaluate(samples, config, repetitions=iterations, warmups=warmups)
        if not result.valid:
            raise ValueError(f"Benchmark has failed samples: {result.failures}")
        return {
            "schema_version": 1,
            "artifact_kind": "measurement",
            "name": name,
            "created_at": datetime.now(UTC).isoformat(),
            "environment": environment,
            "host": runtime_identity(),
            "git_commit": git_revision(),
            "source_sha256": source_hash(),
            "dataset_sha256": dataset_hash(samples),
            "sample_count": len(samples),
            "warmups": warmups,
            "iterations": iterations,
            "evaluation": asdict(result),
        }
    finally:
        cv2.setNumThreads(previous_threads)


def validate_artifact(value: dict) -> dict:
    try:
        if value["schema_version"] != 1 or value["artifact_kind"] != "measurement":
            raise ValueError(
                "Only measured schema-v1 artifacts are accepted; demo fixtures excluded"
            )
        if value["name"] not in {"local", "stock", "cool"}:
            raise ValueError("Unknown environment label")
        PipelineConfig.from_dict(value["evaluation"]["config"])
        for key in ("source_sha256", "dataset_sha256"):
            if not isinstance(value[key], str) or not re.fullmatch(r"[a-f0-9]{64}", value[key]):
                raise ValueError(f"Invalid {key}")
        for key in ("sample_count", "iterations", "warmups"):
            if type(value[key]) is not int or value[key] < (0 if key == "warmups" else 1):
                raise ValueError(f"Invalid {key}")
        if value["evaluation"]["failures"]:
            raise ValueError("Incomplete measurements cannot be compared")
        for key in ("precision", "recall", "f1", "iou", "macro_f1"):
            number = value["evaluation"]["quality"][key]
            if (
                type(number) not in (float, int)
                or not math.isfinite(number)
                or not 0 <= number <= 1
            ):
                raise ValueError(f"Invalid quality: {key}")
        for key in ("mean_ms", "p50_ms", "p95_ms", "throughput_ips"):
            number = value["evaluation"]["timing"][key]
            if type(number) not in (float, int) or not math.isfinite(number) or number < 0:
                raise ValueError(f"Invalid timing: {key}")
        stages = value["evaluation"]["stages_ms"]
        required_stages = {
            "resize",
            "grayscale",
            "blur",
            "threshold",
            "morphology",
            "contours",
            "annotate",
        }
        if not isinstance(stages, dict) or set(stages) != required_stages:
            raise ValueError("Missing or unknown pipeline stages")
        if any(
            type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in stages.values()
        ):
            raise ValueError("Invalid stage timing")
        if (
            not isinstance(value["evaluation"]["samples"], list)
            or len(value["evaluation"]["samples"]) != value["sample_count"]
        ):
            raise ValueError("Sample count does not match measurement records")
        for key in ("opencv5_verified", "cool_verified", "architecture_arm64"):
            if type(value["environment"][key]) is not bool:
                raise ValueError(f"Invalid environment flag: {key}")
        if not value["host"]["host_id"] or value["host"]["cv_threads"] < 1:
            raise ValueError("Missing host or thread evidence")
        for key in ("cv2_version", "python_version", "machine"):
            if not isinstance(value["environment"][key], str):
                raise ValueError(f"Invalid environment field: {key}")
        if not isinstance(value["host"]["processor"], str):
            raise ValueError("Invalid processor metadata")
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed benchmark artifact: {exc}") from exc
    return value


def load_artifact(path: str | Path) -> dict:
    return validate_artifact(json.loads(Path(path).read_text(encoding="utf-8")))


def compare(stock: dict | None, cool: dict | None) -> dict:
    if stock is not None:
        validate_artifact(stock)
    if cool is not None:
        validate_artifact(cool)
    missing = [label for label, result in (("baseline", stock), ("COOL", cool)) if result is None]
    if missing:
        return {"comparable": False, "warnings": [f"{label} unavailable" for label in missing]}
    warnings = []
    for key in ("dataset_sha256", "source_sha256", "sample_count", "warmups", "iterations"):
        if stock[key] != cool[key]:
            warnings.append(f"Mismatched {key}")
    for key in ("host_id", "cv_threads", "processor"):
        if stock["host"][key] != cool["host"][key]:
            warnings.append(f"Mismatched host {key}")
    if stock["evaluation"]["config"] != cool["evaluation"]["config"]:
        warnings.append("Mismatched pipeline configuration")
    for key in ("cv2_version", "python_version"):
        if stock["environment"][key] != cool["environment"][key]:
            warnings.append(f"Mismatched {key}; align versions for a fair comparison")
    for group in ("quality", "timing"):
        if stock["evaluation"][group].keys() != cool["evaluation"][group].keys():
            warnings.append(f"Mismatched {group} fields")
    if stock["name"] != "stock" or cool["name"] != "cool":
        warnings.append("Pair must be labeled stock and cool; local runs are not COOL evidence")
    if not all(x["environment"]["opencv5_verified"] for x in (stock, cool)):
        warnings.append("Both runs must use OpenCV 5")
    if not all(x["environment"]["architecture_arm64"] for x in (stock, cool)):
        warnings.append("Both runs must use Arm64")
    if not cool["environment"]["cool_verified"] or stock["environment"]["cool_verified"]:
        warnings.append("COOL verification must apply only to the COOL run")
    if warnings:
        return {"comparable": False, "warnings": warnings}
    baseline = stock["evaluation"]["timing"]["mean_ms"]
    candidate = cool["evaluation"]["timing"]["mean_ms"]
    return {
        "comparable": True,
        "warnings": [],
        "latency_delta_ms": candidate - baseline,
        "speedup": baseline / candidate if baseline > 0 and candidate > 0 else None,
        "f1_delta": cool["evaluation"]["quality"]["f1"] - stock["evaluation"]["quality"]["f1"],
        "iou_delta": cool["evaluation"]["quality"]["iou"] - stock["evaluation"]["quality"]["iou"],
    }


def markdown_report(stock: dict | None, cool: dict | None) -> str:
    comparison = compare(stock, cool)
    lines = ["# COOLForge benchmark report", "", "Generated from measurement artifacts.", ""]
    if not comparison["comparable"]:
        lines += ["Comparison unavailable: " + "; ".join(comparison["warnings"]), ""]
    else:
        lines += ["| Metric | Stock | COOL |", "|---|---:|---:|"]
        for group in ("timing", "quality"):
            for key, value in stock["evaluation"][group].items():
                lines.append(f"| {key} | {value:.6f} | {cool['evaluation'][group][key]:.6f} |")
        lines += [
            "",
            f"Comparison: `{json.dumps(comparison, sort_keys=True)}`",
            "",
            "Stage means (ms):",
            "",
            "| Stage | Stock | COOL |",
            "|---|---:|---:|",
        ]
        for stage, value in stock["evaluation"]["stages_ms"].items():
            lines.append(
                f"| {stage} | {value:.6f} | {cool['evaluation']['stages_ms'][stage]:.6f} |"
            )
    lines += [
        "",
        "Measurements exclude disk I/O, quality scoring, and UI rendering; annotation is included.",
        "Repeat paired runs in alternating order. "
        "Timing ratios alone do not establish quality parity.",
        "",
    ]
    return "\n".join(lines)
