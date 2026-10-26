# Local engineering handoff — 2026-10-26

## Verified locally

Environment: Windows AMD64, Python 3.14.2, OpenCV 4.13.0, NumPy 2.4.1,
Streamlit 1.53.0, PyYAML 6.0.3, pytest 9.0.3, Ruff 0.14.10.
This is explicitly a development environment, not the final competition runtime.

The final local suite completed with **67 passed**. Ruff lint and formatting checks
passed. A wheel was built successfully. The installer passed Bash syntax validation.
Relative Markdown links resolved, `git diff --check` passed, and a scan for common
AWS/GitHub/API token and private-key patterns found no matches in project files.
Pattern scanning is a hygiene check, not a proof that arbitrary sensitive data is absent.

Commands actually exercised during development and final verification:

```bash
python scripts/generate_dataset.py --output data/eval --count 50
python scripts/evaluate.py --iterations 3
python scripts/autotune.py --max-iterations 8
python scripts/verify_cool.py --json results/environment.json
python scripts/benchmark_worker.py --warmups 2 --iterations 5 --output results/local.json
python scripts/generate_report.py --output results/missing-comparison.md
python scripts/export_demo.py
python -m pytest -q --basetemp=results/pytest-release
python -m ruff check .
python -m ruff format --check .
python -m pip wheel --no-deps --no-build-isolation --wheel-dir results/dist .
bash -n deploy/aws/install_on_cool_ami.sh
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true
```

The app was opened in a real browser on port 8502. Inspection panels, runtime status,
a 12-step Autotune run, result tables, config comparison, live proposal preview, and
approval/export control were observed. Genuine captures are in `docs/assets/`.
Automated app tests also exercise input changes that invalidate a proposal. CLI tests
cover a missing interpreter and verify that an explicit unavailable report remains.

The first sandboxed pytest attempt could not access the system temp directory; later
runs used a workspace base directory. The final unsandboxed test run completed cleanly.
The initial sandboxed Streamlit process did not bind a port; the verified browser run
used the normal local runtime. These were execution-environment constraints, not masked
test failures. The benchmark artifacts were regenerated against the final core source
and their source hash was checked programmatically.

## Start locally

From the repository, with the dependencies installed:

```bash
python -m streamlit run app.py
```

The normal configured endpoint is `http://localhost:8501`. Data is generated in memory
for the demo. The development browser session used 8502 to avoid the restricted launcher.

## Required AWS evidence

On a subscribed compatible official COOL Graviton AMI, from the cloned repository:

```bash
bash deploy/aws/install_on_cool_ami.sh
source /opt/cool/venvs/python_3.12/bin/activate
python scripts/verify_cool.py --json results/environment.json --require-cool
python scripts/evaluate.py --dataset data/eval
python scripts/autotune.py --dataset data/eval --max-iterations 12
python scripts/benchmark_worker.py --name cool --dataset data/eval --warmups 5 --iterations 30 --output results/cool.json
python scripts/benchmark_matrix.py --stock-python /path/to/your/stock/python --cool-python /opt/cool/venvs/python_3.12/bin/python --dataset data/eval --warmups 5 --iterations 30
```

The stock interpreter must actually be prepared with the matching stock OpenCV 5 build;
replace its path. Repeat matched pairs in both orders as described in `BENCHMARKS.md`.

Not verified locally: OpenCV 5 execution, COOL activation, EC2/Graviton deployment,
stock/COOL comparative performance, Nginx/systemd execution on Linux, production defect
accuracy, a public demo endpoint, or a recorded submission video. CI execution status
belongs to GitHub Actions and is separate from this recorded local validation.

CI always publishes compact measurement summaries. Raw artifact upload is an opt-in
manual-run input with three-day retention. The initial automatic upload encountered
the account's existing storage quota; no existing artifacts were deleted. Tests remain
mandatory regardless of artifact retention, and matrix jobs finish independently.

## Five priority review files

1. [README.md](../README.md): setup and evidence status.
2. [REPORT.md](../REPORT.md): technical claims and submission gaps.
3. [agent.py](../coolforge/agent.py): decision policy and quality constraints.
4. [benchmark.py](../coolforge/benchmark.py): measurement and comparison gates.
5. [AWS runbook](../deploy/aws/README.md): vendor-runtime-safe deployment procedure.
