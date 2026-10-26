import json

import streamlit as st

from coolforge.benchmark import ROOT, compare, load_artifact, validate_artifact
from coolforge.environment import EnvironmentEvidence


def result_loader(label: str) -> dict | None:
    upload = st.file_uploader(f"Load {label} result", type=["json"], key=f"result_{label}")
    candidates = sorted(
        (ROOT / "results").rglob(f"{label}.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    selection = st.selectbox(
        f"Saved {label} measurements",
        [None, *candidates[:10]],
        format_func=lambda p: "No saved result selected" if p is None else str(p.relative_to(ROOT)),
    )
    try:
        if upload:
            return validate_artifact(json.loads(upload.getvalue()))
        if selection:
            return load_artifact(selection)
    except (ValueError, OSError) as exc:
        st.error(f"Cannot use {label} result: {exc}")
    return None


def render_benchmarks(environment: EnvironmentEvidence) -> None:
    st.subheader("Measured evidence")
    st.write(
        "Stock and COOL comparisons require matching source, dataset, host, configuration, "
        "thread count, and sampling budgets. Uploaded artifacts are user-supplied evidence."
    )
    with st.expander("Current environment evidence"):
        st.json(environment.to_dict())
    left, right = st.columns(2)
    with left:
        stock = result_loader("stock")
    with right:
        cool = result_loader("cool")
    result = compare(stock, cool)
    if not result["comparable"]:
        st.warning("; ".join(result["warnings"]))
    else:
        columns = st.columns(3)
        columns[0].metric(
            "Mean latency ratio (stock / COOL)",
            f"{result['speedup']:.3f}×" if result["speedup"] else "Unavailable",
        )
        columns[1].metric("COOL − stock latency", f"{result['latency_delta_ms']:+.3f} ms")
        columns[2].metric("COOL − stock F1", f"{result['f1_delta']:+.4f}")
        if abs(result["f1_delta"]) > 0.005:
            st.warning("Quality differs by more than 0.005 F1. Investigate before claiming parity.")
        st.dataframe(
            [
                {
                    "environment": name,
                    **value["evaluation"]["timing"],
                    **value["evaluation"]["quality"],
                }
                for name, value in (("stock", stock), ("cool", cool))
            ],
            hide_index=True,
            width="stretch",
        )
        st.dataframe(
            [
                {
                    "stage": stage,
                    "stock_ms": latency,
                    "cool_ms": cool["evaluation"]["stages_ms"][stage],
                }
                for stage, latency in stock["evaluation"]["stages_ms"].items()
            ],
            hide_index=True,
            width="stretch",
        )
    for name, value in (("stock", stock), ("cool", cool)):
        if value:
            with st.expander(f"{name} artifact and provenance"):
                st.json(value)
    st.code(
        "python scripts/benchmark_matrix.py --stock-python /path/to/stock/python "
        "--cool-python /opt/cool/venvs/python_3.12/bin/python "
        "--dataset data/eval --warmups 5 --iterations 30",
        language="bash",
    )


def render_architecture() -> None:
    st.subheader("Architecture & reproducibility")
    st.markdown("""
**One workload, two OpenCV environments.** A deterministic surface generator supplies images
and exact masks. OpenCV resizes, converts color, blurs, thresholds, cleans morphology,
extracts contours, and draws detections. Foreground F1 and monotonic stage timings feed
an inspectable coordinate-search policy.

**A real feedback loop.** Recall loss redirects the next experiment toward sensitivity;
false positives prioritize suppression; feasible quality permits scale reduction. Each
candidate runs OpenCV again. Quality violations roll back to the incumbent. A fixed
budget bounds work. The final proposal runs live and needs human approval to export.

**AWS deployment.** Browser → Nginx → localhost Streamlit → OpenCV 5 in the official
COOL AMI on Graviton. Two explicitly selected interpreters run serial benchmarks on
the same host. No external model API, database, or cloud credential is required by the app.

**Limitations.** Dark synthetic defects are easier than real reflective, colored, or
low-contrast surfaces. Small defects may disappear during downsampling or morphology.
Timing noise can change acceptance decisions. The policy is deterministic given observations,
not guaranteed to find a global optimum. A locally green build check alone does not prove
AWS hosting or acceleration of every operation.

**Responsible use.** This is a developer experiment, not a certified industrial inspection
system. Validate on representative held-out production data. Demo uploads should contain no
sensitive data; they are processed in server memory and not sent to an external AI service.
The public demo has no authentication: restrict access and avoid sensitive workloads.
""")
    st.code(
        """python scripts/generate_dataset.py --output data/eval --count 50
python scripts/evaluate.py --dataset data/eval
python scripts/autotune.py --dataset data/eval --max-iterations 12
python scripts/verify_cool.py --json results/environment.json
python -m pytest -q
python -m streamlit run app.py""",
        language="bash",
    )
    st.caption(
        "Dataset generation refuses to overwrite an existing manifest. "
        "Reuse it or choose a new directory."
    )
    st.markdown(
        "See `deploy/aws/README.md`, `BENCHMARKS.md`, and `docs/ARCHITECTURE.md` in the repository."
    )
