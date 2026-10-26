# Contributing

Use a fresh Python 3.12+ virtual environment and follow the README's local setup.
Preserve the independent COOL dependency boundary: `requirements-app.txt` must never
depend on an OpenCV wheel. OpenCV 4 is acceptable for local regression work and must
remain visibly labeled as development-only.

Before proposing a change:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

For a restricted environment that cannot create system temporary directories, set a
writable temporary directory and/or use pytest's `--basetemp=results/pytest-local`.
Pytest owns and may clear its explicitly selected base directory; keep other files out.

Keep changes focused. Use descriptive categories such as `feat(vision)`, `fix(agent)`,
`test(metrics)`, `docs(benchmark)`, or `build`. Describe actual behavior and validation
in commit messages and PRs. Do not rewrite measurement history to improve appearances.

Algorithm changes should compare foreground precision, recall, F1, and IoU on both
tuning and held-out seeds. Keep exact masks and per-image failures. Preserve rollback,
iteration bounds, and human approval. Avoid tests whose assertions depend on wall-clock
speedups; inject controlled observations for policy tests and run real OpenCV separately.

Benchmark changes must retain source/data hashes, environment provenance, thread count,
warmups, and iteration budgets. Never add fabricated measurements to product-facing
artifacts. Clearly label synthetic test fixtures and keep them inside tests. Review local
paths and private host metadata before publishing artifacts.

No LLM API dependency, database, or deployment framework should be added without a
concrete use case. Document new assumptions and failure modes alongside the code.
