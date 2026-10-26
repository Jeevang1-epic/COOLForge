"""Shared CLI bootstrap for direct execution from a repository checkout."""

import argparse
import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def parser(description: str) -> argparse.ArgumentParser:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    return argparse.ArgumentParser(description=description)


def write_json(path: str | Path, value: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(value) if is_dataclass(value) else value,
                                 indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run(main) -> None:
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        logging.error("%s", exc)
        raise SystemExit(1) from None
