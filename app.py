"""COOLForge interactive workbench. Launch with: python -m streamlit run app.py."""

import streamlit as st

from coolforge.dataset import generate_samples
from coolforge.environment import inspect_environment
from coolforge.ui.inspection import configuration_controls, render_inspection
from coolforge.ui.tuning import render_tuning

st.set_page_config(page_title="COOLForge · OpenCV performance workbench", layout="wide")
st.title("COOLForge")
st.header("Make OpenCV faster without breaking what it sees.")
st.write("An agentic performance engineer for OpenCV 5 pipelines on AWS Graviton.")
environment = inspect_environment()
if environment.cool_verified:
    st.success(environment.status)
elif environment.opencv5_verified:
    st.warning(environment.status)
else:
    st.error(environment.status + f" · Detected {environment.cv2_version}")
st.caption("Local processing · No external model API · Human-approved configuration export")


@st.cache_data(show_spinner=False)
def demo_samples():
    return generate_samples(50)


samples = demo_samples()
config = configuration_controls()
inspect_tab, tune_tab = st.tabs(["INSPECT", "AUTOTUNE AGENT"])
with inspect_tab:
    render_inspection(samples, config)
with tune_tab:
    render_tuning(samples, config)
