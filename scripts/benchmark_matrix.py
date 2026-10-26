import subprocess
from datetime import UTC, datetime
from pathlib import Path

from _common import ROOT, parser, run, write_json

from coolforge.benchmark import load_artifact, markdown_report


def main() -> None:
    args = parser("Run stock/COOL sequentially using explicit interpreters")
    args.add_argument("--stock-python")
    args.add_argument("--cool-python")
    args.add_argument("--dataset", default="data/eval")
    args.add_argument("--config", default="configs/default.yaml")
    args.add_argument("--warmups", type=int, default=5)
    args.add_argument("--iterations", type=int, default=30)
    args.add_argument("--threads", type=int, default=1)
    args.add_argument("--order", choices=["stock-first", "cool-first"], default="stock-first")
    args.add_argument("--output-dir", default="results/matrix")
    opt = args.parse_args()
    if not (opt.stock_python or opt.cool_python):
        raise ValueError("Provide at least one interpreter; absent sides remain unavailable")
    output = Path(opt.output_dir) / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True)
    results, failures = {}, {}
    order = ["stock", "cool"] if opt.order == "stock-first" else ["cool", "stock"]
    for name in order:
        executable = getattr(opt, f"{name}_python")
        if not executable:
            continue
        target = output / f"{name}.json"
        command = [
            executable,
            str(ROOT / "scripts/benchmark_worker.py"),
            "--name",
            name,
            "--dataset",
            str(Path(opt.dataset).resolve()),
            "--config",
            str(Path(opt.config).resolve()),
            "--warmups",
            str(opt.warmups),
            "--iterations",
            str(opt.iterations),
            "--threads",
            str(opt.threads),
            "--output",
            str(target.resolve()),
        ]
        try:
            completed = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=3600, check=False
            )
            (output / f"{name}.log").write_text(
                completed.stdout + completed.stderr, encoding="utf-8"
            )
            if completed.returncode:
                failures[name] = f"Worker exited {completed.returncode}; see {name}.log"
            else:
                results[name] = load_artifact(target)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            failures[name] = str(exc)
    write_json(output / "matrix.json", {"failures": failures, "order": order})
    (output / "report.md").write_text(
        markdown_report(results.get("stock"), results.get("cool")), encoding="utf-8"
    )
    print(output / "report.md")
    if failures:
        raise ValueError(f"Workers failed: {failures}")


if __name__ == "__main__":
    run(main)
