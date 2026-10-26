from _common import parser, run, write_json

from coolforge.config import PipelineConfig
from coolforge.dataset import load_dataset
from coolforge.evaluation import evaluate


def main() -> None:
    args = parser("Evaluate foreground quality and latency")
    args.add_argument("--dataset", default="data/eval")
    args.add_argument("--config", default="configs/default.yaml")
    args.add_argument("--output", default="results/evaluation.json")
    args.add_argument("--iterations", type=int, default=3)
    opt = args.parse_args()
    result = evaluate(
        load_dataset(opt.dataset),
        PipelineConfig.load(opt.config),
        repetitions=opt.iterations,
        warmups=1,
    )
    write_json(opt.output, result)
    print(result.quality)
    print(result.timing)
    if not result.valid:
        raise ValueError("Evaluation contains failures; see artifact")


if __name__ == "__main__":
    run(main)
