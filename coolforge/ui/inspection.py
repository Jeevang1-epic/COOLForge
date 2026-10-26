import cv2
import numpy as np
import streamlit as st

from coolforge.config import PipelineConfig
from coolforge.metrics import mask_metrics
from coolforge.models import Sample
from coolforge.pipeline import PipelineError, inspect


def configuration_controls() -> PipelineConfig:
    with st.sidebar:
        st.header("Pipeline configuration")
        scale = st.select_slider("Processing scale", [0.6, 0.7, 0.8, 0.9, 1.0], value=1.0)
        blur = st.selectbox("Blur kernel", [1, 3, 5, 7], index=1)
        block = st.selectbox("Adaptive block size", [11, 15, 21, 31, 41], index=4)
        threshold = st.number_input("Adaptive C", -20.0, 50.0, 8.0, step=1.0)
        morphology = st.selectbox("Morphology kernel", [1, 3, 5], index=0)
        area = st.number_input("Minimum contour area (original pixels)", 0.0, 10000.0, 5.0)
        st.caption("These controls remain yours. Autotuning produces a proposal for review.")
    return PipelineConfig(scale, blur, block, threshold, morphology, area)


def render_inspection(samples: list[Sample], config: PipelineConfig) -> None:
    st.subheader("Inspect a surface")
    st.write("Compare foreground masks with exact synthetic ground truth and inspect stage costs.")
    choice = st.selectbox(
        "Built-in sample", range(len(samples)), format_func=lambda i: samples[i].sample_id, index=1
    )
    upload = st.file_uploader("Or upload a PNG / JPEG", type=["png", "jpg", "jpeg"])
    image, truth = samples[choice].image, samples[choice].mask
    try:
        if upload is not None:
            raw = np.frombuffer(upload.getvalue(), np.uint8)
            image = cv2.imdecode(raw, cv2.IMREAD_COLOR) if raw.size else None
            if image is None:
                raise ValueError("The uploaded file is not a readable image")
            truth = None
            st.caption(
                "Uploaded image: no ground truth available; quality metrics are unavailable."
            )
        result = inspect(image, config)
        columns = st.columns(2)
        columns[0].image(image, channels="BGR", caption="Original surface", width="stretch")
        columns[1].image(
            result.annotated_bgr, channels="BGR", caption="Detected regions", width="stretch"
        )
        columns = st.columns(2)
        if truth is not None:
            columns[0].image(truth, caption="Exact ground truth", width="stretch", clamp=True)
        else:
            columns[0].info("Ground truth is required to assess detection quality.")
        columns[1].image(result.mask, caption="Predicted defect mask", width="stretch", clamp=True)
        cards = st.columns(4)
        cards[0].metric("Pipeline latency", f"{result.latency_ms:.2f} ms")
        cards[1].metric("Detected regions", len(result.detections))
        if truth is not None:
            quality = mask_metrics(result.mask, truth)
            cards[2].metric("Pixel F1", f"{quality['f1']:.3f}")
            cards[3].metric("IoU", f"{quality['iou']:.3f}")
            st.caption(f"Precision {quality['precision']:.3f} · Recall {quality['recall']:.3f}")
        st.dataframe(
            [{"stage": key, "latency_ms": value} for key, value in result.stages_ms.items()],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "One inspection, not a benchmark. "
            "Latency includes annotation and excludes UI rendering."
        )
    except (ValueError, PipelineError, cv2.error) as exc:
        st.error(str(exc))
