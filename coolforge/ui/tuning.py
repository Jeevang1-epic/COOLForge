import json
from dataclasses import asdict

import streamlit as st

from coolforge.agent import PipelineOptimizationAgent
from coolforge.config import PipelineConfig
from coolforge.dataset import generate_samples
from coolforge.evaluation import evaluate
from coolforge.models import Sample
from coolforge.pipeline import PipelineError, inspect


def render_tuning(samples: list[Sample], config: PipelineConfig) -> None:
    st.subheader("Autotune agent")
    st.write("Observe → decide → mutate → rerun → evaluate → accept or roll back.")
    columns = st.columns(3)
    floor = columns[0].slider("Minimum pixel F1", 0.50, 1.0, 0.85, 0.01)
    budget = columns[1].number_input("Maximum iterations", 1, 30, 12)
    subset = columns[2].number_input("Tuning subset size", 5, len(samples), 15, step=5)
    target = st.number_input("Optional p50 latency target (ms; 0 disables)", 0.0, 1000.0, 0.0)
    signature = (config, floor, budget, subset, target)
    if st.button("Run Autotune", type="primary"):
        progress = st.progress(0, text="Evaluating incumbent")
        try:

            def on_step(entry):
                progress.progress(
                    entry.iteration / budget, text=f"{entry.iteration}/{budget} · {entry.action}"
                )

            result = PipelineOptimizationAgent(floor, int(budget), target or None).run(
                samples[: int(subset)], config, on_step=on_step
            )
            with st.spinner("Checking proposal on 20 held-out surfaces (seed 1042)"):
                holdout = generate_samples(20, seed=1042)
                held_before = evaluate(holdout, result.initial.config, repetitions=3, warmups=1)
                held_after = evaluate(holdout, result.final.config, repetitions=3, warmups=1)
            st.session_state["proposal"] = (signature, result, held_before, held_after)
            progress.progress(1.0, text="Complete — proposal ready for review")
        except (ValueError, PipelineError) as exc:
            st.error(f"Autotune failed: {exc}")
            st.session_state.pop("proposal", None)
    proposal = st.session_state.get("proposal")
    if proposal is None:
        st.info("Run the agent to produce a measured proposal and decision trace.")
        return
    saved_signature, result, held_before, held_after = proposal
    if saved_signature != signature:
        st.warning("Inputs changed. Run Autotune again before reviewing or exporting a proposal.")
        return
    before, after = result.initial, result.final
    columns = st.columns(3)
    columns[0].metric(
        "Proposed F1",
        f"{after.quality['f1']:.3f}",
        f"{after.quality['f1'] - before.quality['f1']:+.3f}",
    )
    columns[1].metric(
        "Proposed p50",
        f"{after.timing['p50_ms']:.2f} ms",
        f"{after.timing['p50_ms'] - before.timing['p50_ms']:+.2f} ms",
        delta_color="inverse",
    )
    columns[2].metric(
        "Held-out F1",
        f"{held_after.quality['f1']:.3f}",
        f"{held_after.quality['f1'] - held_before.quality['f1']:+.3f}",
    )
    st.caption(f"Stop reason: {result.stop_reason}. Tuning and hold-out metrics are separate.")
    st.dataframe(
        [
            {"dataset": label, "configuration": stage, **evaluation.quality, **evaluation.timing}
            for label, stage, evaluation in (
                ("tuning", "incumbent", before),
                ("tuning", "proposal", after),
                ("hold-out", "incumbent", held_before),
                ("hold-out", "proposal", held_after),
            )
        ],
        hide_index=True,
        width="stretch",
    )
    st.dataframe(
        [
            {
                "iteration": entry.iteration,
                "observed_f1": entry.observation["incumbent"]["quality"]["f1"],
                "action": entry.action,
                "rationale": entry.rationale,
                "candidate_f1": entry.result["quality"]["f1"] if entry.result else None,
                "p50_ms": entry.result["timing"]["p50_ms"] if entry.result else None,
                "accepted": entry.accepted,
                "failure": entry.failure,
            }
            for entry in result.trace
        ],
        hide_index=True,
        width="stretch",
    )
    st.dataframe(
        [
            {
                "parameter": key,
                "incumbent": str(value),
                "proposal": str(after.config.to_dict()[key]),
                "changed": value != after.config.to_dict()[key],
            }
            for key, value in before.config.to_dict().items()
        ],
        hide_index=True,
        width="stretch",
    )
    # Execute the selected configuration again, demonstrating the final running workload.
    preview = inspect(samples[1].image, after.config)
    st.image(preview.annotated_bgr, channels="BGR", caption="Live proposal preview", width=600)
    exportable = result.feasible and held_after.valid and held_after.quality["f1"] >= floor
    if not exportable:
        st.warning("Quality floor was not met on tuning or hold-out data. Export is disabled.")
    st.caption(
        "Approval exports a YAML file. It does not alter the sidebar or deploy a workload. "
        "Small timing differences may be noise; validate on representative production data."
    )
    st.download_button(
        "Approve & Export Configuration",
        after.config.to_yaml(),
        file_name="coolforge-approved.yaml",
        mime="text/yaml",
        disabled=not exportable,
        type="primary",
    )
    with st.expander("Full audit trace and Pareto frontier"):
        st.json(asdict(result))
        st.download_button(
            "Download audit trace",
            json.dumps(asdict(result), indent=2),
            file_name="agent-trace.json",
            mime="application/json",
        )
