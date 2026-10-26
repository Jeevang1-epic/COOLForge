# COOLForge

**Make OpenCV faster without breaking what it sees.**

> Submission draft: retain the evidence limitations below until the actual AWS runs,
> demo endpoint/screen-share arrangement, and video have been completed.

## Inspiration

Performance tuning can quietly damage a vision system. A smaller image or stronger
filter may be faster while deleting thin defects. We wanted a workbench that measures
what a pipeline sees as carefully as how quickly it runs.

## What it does

COOLForge profiles an OpenCV surface-inspection pipeline, evaluates its mask against
exact synthetic ground truth, and searches for better settings within a quality floor.
The agent changes parameters, reruns the workload, and accepts or rolls back each candidate.
A developer can inspect every decision and approve the final configuration after held-out
validation. Nothing is silently deployed.

## How we built it

The implementation uses Python, OpenCV, NumPy, Streamlit, PyYAML, and pytest. The core
policy is deterministic given observations and does not call an external LLM. A seeded
surface generator provides reproducible defects and exact masks. Separate Python workers
support comparisons between stock OpenCV and the COOL vendor runtime.

## Substantive OpenCV and AWS roles

OpenCV performs the actual resize, grayscale conversion, Gaussian blur, adaptive
thresholding, morphology, contour extraction, filtering, and annotation. Every candidate
runs these operations again. The target OpenCV 5 workload runs on an official COOL AMI
on AWS Graviton, with Nginx and systemd deployment assets and strict runtime verification.

**Current evidence boundary:** local execution used OpenCV 4.13. AWS execution and
OpenCV 5/COOL verification have not yet been recorded. Do not describe the target path
as a completed deployment until the operator artifacts exist.

## Agentic Vision

Visual and runtime results change later actions: low recall redirects sensitivity
experiments, false positives prioritize suppression, and adequate quality permits
scale reductions. The agent executes a bounded loop, rejects regressions, retains an
audit trace, and ends in a live preview plus human approval. Controlled tests prove
that different visual observations select different next actions.

## Evaluation and accomplishments

The repository contains real local measurements, a multi-step agent trace, held-out
evaluation, generated inspection examples, and actual browser captures. The report
distinguishes synthetic quality from production accuracy and local measurements from
missing COOL comparisons. Tests exercise both algorithms and the interactive workflow.

Insert the verified AWS environment and generated stock/COOL report after following
`deploy/aws/README.md` and `BENCHMARKS.md`. No cloud speedup is claimed in this draft.

## Challenges and lessons

Foreground quality is a more useful guardrail than background-dominated accuracy.
Scale changes require area thresholds in consistent coordinates. Benchmark provenance
matters as much as a latency number. Search remains subject to measurement noise and
local optima, and synthetic validation cannot substitute for production evidence.

## What's next

Complete matched OpenCV 5/COOL measurements on Graviton, broaden labeled material data,
and evaluate rare-defect misses. Optional MCP adapters can expose the tested core later;
they are not necessary to demonstrate the agentic loop.

Built with: Python · OpenCV · NumPy · Streamlit · PyYAML · pytest.
Target deployment: AWS EC2 Graviton · COOL · Nginx · systemd.
