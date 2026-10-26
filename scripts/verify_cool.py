from pathlib import Path

from _common import parser, run, write_json

from coolforge.environment import inspect_environment


def main() -> None:
    args = parser("Inspect OpenCV/COOL provenance without assuming acceleration")
    args.add_argument("--json", default="results/environment.json")
    args.add_argument("--require-cool", action="store_true")
    opt = args.parse_args()
    result = inspect_environment()
    write_json(opt.json, result)
    summary = "\n".join([result.status, f"Python: {result.python_version}",
                          f"OpenCV: {result.cv2_version}", f"Module: {result.cv2_file}",
                          f"Architecture: {result.machine}", *result.evidence,
                          *result.build_excerpt, *result.warnings]) + "\n"
    Path(opt.json).with_suffix(".txt").write_text(summary, encoding="utf-8")
    print(summary.encode("ascii", errors="replace").decode())
    if opt.require_cool and not result.cool_verified:
        raise ValueError("COOL verification failed; evidence saved")


if __name__ == "__main__":
    run(main)
