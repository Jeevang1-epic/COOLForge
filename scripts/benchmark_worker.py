import csv
from pathlib import Path

from _common import parser, run, write_json

from coolforge.benchmark import run_benchmark
from coolforge.config import PipelineConfig
from coolforge.dataset import load_dataset


def main() -> None:
    args = parser("Measure the pipeline in this Python environment")
    args.add_argument("--dataset", default="data/eval")
    args.add_argument("--config", default="configs/default.yaml")
    args.add_argument("--name", choices=["local", "stock", "cool"], default="local")
    args.add_argument("--warmups", type=int, default=5)
    args.add_argument("--iterations", type=int, default=30)
    args.add_argument("--threads", type=int, default=1)
    args.add_argument("--output", default="results/local.json")
    opt = args.parse_args()
    result = run_benchmark(load_dataset(opt.dataset), PipelineConfig.load(opt.config),
                           opt.name, opt.warmups, opt.iterations, opt.threads)
    write_json(opt.output, result)
    rows = result["evaluation"]["samples"]
    with Path(opt.output).with_suffix(".csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Measured {result['sample_count']} samples: {opt.output}")


if __name__ == "__main__":
    run(main)
