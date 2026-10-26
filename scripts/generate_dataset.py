from _common import parser, run

from coolforge.dataset import generate_samples, save_dataset


def main() -> None:
    args = parser("Generate synthetic inspection images with exact binary masks")
    args.add_argument("--output", default="data/eval")
    args.add_argument("--count", type=int, default=50)
    args.add_argument("--seed", type=int, default=42)
    args.add_argument("--width", type=int, default=384)
    args.add_argument("--height", type=int, default=256)
    opt = args.parse_args()
    print(save_dataset(generate_samples(opt.count, opt.seed, opt.width, opt.height), opt.output))


if __name__ == "__main__":
    run(main)
