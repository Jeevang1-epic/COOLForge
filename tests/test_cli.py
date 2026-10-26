import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(script, *args, expected=0):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    return result


def test_cli_workflow(tmp_path):
    dataset = tmp_path / "dataset"
    command("generate_dataset.py", "--output", dataset, "--count", 5, "--width", 96, "--height", 64)
    command(
        "evaluate.py",
        "--dataset",
        dataset,
        "--iterations",
        1,
        "--output",
        tmp_path / "evaluation.json",
    )
    command(
        "autotune.py",
        "--dataset",
        dataset,
        "--max-iterations",
        2,
        "--output",
        tmp_path / "agent.json",
    )
    command(
        "benchmark_worker.py",
        "--dataset",
        dataset,
        "--warmups",
        0,
        "--iterations",
        1,
        "--output",
        tmp_path / "local.json",
    )
    command("verify_cool.py", "--json", tmp_path / "environment.json")
    command("generate_report.py", "--output", tmp_path / "report.md")
    assert "baseline unavailable; COOL unavailable" in (tmp_path / "report.md").read_text()
    assert json.loads((tmp_path / "local.json").read_text())["sample_count"] == 5


def test_missing_interpreter_leaves_report(tmp_path):
    command(
        "benchmark_matrix.py",
        "--stock-python",
        tmp_path / "missing-python",
        "--output-dir",
        tmp_path / "matrix",
        expected=1,
    )
    report = next((tmp_path / "matrix").glob("*/report.md"))
    assert "baseline unavailable" in report.read_text()
