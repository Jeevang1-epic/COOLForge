from pathlib import Path

from _common import parser, run

from coolforge.benchmark import load_artifact, markdown_report


def main() -> None:
    args = parser("Generate a report only from supplied measurement artifacts")
    args.add_argument("--stock")
    args.add_argument("--cool")
    args.add_argument("--output", default="results/benchmark-report.md")
    opt = args.parse_args()
    stock = load_artifact(opt.stock) if opt.stock else None
    cool = load_artifact(opt.cool) if opt.cool else None
    output = Path(opt.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_report(stock, cool), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    run(main)
