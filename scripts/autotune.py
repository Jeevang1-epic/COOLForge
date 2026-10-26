from _common import parser, run, write_json

from coolforge.agent import PipelineOptimizationAgent
from coolforge.config import PipelineConfig
from coolforge.dataset import load_dataset


def main() -> None:
    args = parser("Run a bounded optimization; write an audit trace, not an approved config")
    args.add_argument("--dataset", default="data/eval")
    args.add_argument("--config", default="configs/default.yaml")
    args.add_argument("--quality-floor", type=float, default=0.85)
    args.add_argument("--max-iterations", type=int, default=12)
    args.add_argument("--subset", type=int, default=15)
    args.add_argument("--latency-target-ms", type=float)
    args.add_argument("--output", default="results/agent.json")
    opt = args.parse_args()
    if opt.subset < 1:
        raise ValueError("Subset must be positive")
    result = PipelineOptimizationAgent(opt.quality_floor, opt.max_iterations,
                                       opt.latency_target_ms).run(
        load_dataset(opt.dataset)[:opt.subset], PipelineConfig.load(opt.config),
        on_step=lambda entry: print(f"{entry.iteration}: {entry.action}; accepted={entry.accepted}"))
    write_json(opt.output, result)
    print(f"Stop: {result.stop_reason}; feasible={result.feasible}. Review and approve in the app.")


if __name__ == "__main__":
    run(main)
