# Benchmark protocol and evidence status

There is **no verified stock OpenCV 5 versus COOL result yet**. The checked-in
[local artifact](docs/assets/local-benchmark.json) is a real local development run and
cannot be used as a final stock baseline. [Its generated summary](docs/assets/LOCAL_RESULTS.md)
records actual environment, configuration, metrics, source hash, and dataset hash.

## Measurement contract

- Use the same dataset manifest, decoded pixels, exact masks, sample order, and config.
- Use the same host, OpenCV/Python versions, thread count, source code, and sampling budget.
- Use independent Python environments: stock OpenCV 5 outside `/opt/cool`, COOL inside it.
- Run workers sequentially. Close competing workloads, record CPU type/load, and allow warmup.
- Warm each image `--warmups` times, then measure it `--iterations` times before the next image.
- Stage and total latency use `perf_counter_ns`. Images are loaded before measurement.
- Include annotation and internal allocation; exclude data generation, disk, UI, and metric scoring.
- Report micro foreground precision/recall/F1/IoU, macro F1, per-image quality, mean/p50/p95,
  stage means, and reciprocal-mean sequential throughput. CSV latency is the last pass per image;
  JSON aggregate timing covers all measured passes. It is not concurrent request throughput.

The comparator refuses missing or mismatched evidence. It also rejects demo/schema
fixtures, nonfinite numbers, incomplete stage sets, failed samples, and contradictory
verification flags. Uploaded JSON remains user-supplied evidence, not signed attestation.

## Local check

```bash
python scripts/generate_dataset.py --output data/eval --count 50 --seed 42
python scripts/benchmark_worker.py --name local --dataset data/eval --config configs/default.yaml --warmups 5 --iterations 30 --threads 1 --output results/local.json
python scripts/generate_report.py --output results/no-comparison.md
```

If `data/eval/manifest.json` already exists, reuse it rather than regenerate over it.
The last command intentionally says baseline/COOL unavailable. No ratio is invented.
For checked-in local examples, run `python scripts/export_demo.py`; its smaller five-pass
budget is recorded and is intended for reproducible software demonstration only.

## Final Graviton pair

Follow [the deployment runbook](deploy/aws/README.md). Prepare the stock interpreter
yourself using the correct upstream OpenCV version/build instructions; there is no
assumed stock path. Verify it does not import COOL through shared environment variables.

```bash
source /opt/cool/venvs/python_3.12/bin/activate
python scripts/verify_cool.py --json results/environment.json --require-cool
export STOCK_PYTHON=/absolute/path/to/your/stock/python
python scripts/benchmark_matrix.py --stock-python "$STOCK_PYTHON" --cool-python /opt/cool/venvs/python_3.12/bin/python --dataset data/eval --warmups 5 --iterations 30 --threads 1
python scripts/benchmark_matrix.py --stock-python "$STOCK_PYTHON" --cool-python /opt/cool/venvs/python_3.12/bin/python --dataset data/eval --warmups 5 --iterations 30 --threads 1 --order cool-first
```

Repeat at least three pairs in alternating order on an otherwise idle instance. Each
matrix invocation creates a new timestamped directory with worker JSON/CSV/logs, a
matrix status artifact, and a Markdown report. Worker failure cannot reuse stale files.
Missing sides are allowed explicitly; a requested but failed worker exits nonzero and
still writes a report. Matrix execution does not provision or charge for AWS resources.

To generate a report from two selected artifacts:

```bash
python scripts/generate_report.py --stock results/matrix/RUN/stock.json --cool results/matrix/RUN/cool.json --output results/benchmark-report.md
```

Replace `RUN` with the actual run directory. Save the region, instance type, vCPU count,
CPU model, AMI release, COOL release, full OpenCV build information, and operating load
in an adjacent `operator-notes.md`. Do not publish account IDs, SSH keys, or private IPs.

## Interpretation

Mean latency difference is `COOL − stock`; the ratio is `stock / COOL` only when both
means are positive. A ratio below one is a slowdown. There is no forced “win.” Zero
latency suppresses the ratio instead of dividing by zero. F1 and IoU differences are
reported separately. A faster run with a quality regression is not automatically better.

Compare repeat-run spread before claiming a gain. The harness does not estimate
confidence intervals or causal attribution; retain each run and report their range or
an appropriate statistical analysis. Match upstream runtime versions and disclose
remaining compiler/backend differences. A green provenance flag does not prove that
each OpenCV operation used a specialized kernel.

Agent latency observations are exploratory. They use one warmup and three measured
passes per image and can be affected by selection bias and noise. Freeze an approved
configuration and rerun the independent benchmark protocol to assess its performance.
Keep tuning and library-acceleration comparisons separate: change one factor at a time.

## Quality parity and failure examples

Inspect per-image rows, not just aggregate F1. The generated contact sheet shows
boundary oversegmentation; the agent trace records quality-floor violations at some
lower scales. Tiny cracks and rare defect classes require dedicated recall review.
Use seed 1042 as a held-out synthetic check and representative independently labeled
production surfaces before making real-world accuracy claims.

Synthetic fixtures used in tests are constructed in memory, are not saved as production
evidence, and do not populate the benchmark tab. Local artifacts are labeled `local`
and the comparison logic refuses to treat them as a stock/COOL pair.
