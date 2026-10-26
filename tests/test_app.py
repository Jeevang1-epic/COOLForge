from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_app_inspection_and_agent_review():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "INSPECT",
        "AUTOTUNE AGENT",
        "BENCHMARKS",
        "ARCHITECTURE & REPRODUCIBILITY",
    ]
    assert any("COOL unavailable" in warning.value for warning in app.warning)
    assert len(app.tabs[0].metric) == 4
    assert len(app.tabs[0].dataframe) == 1
    assert app.tabs[1].subheader[0].value == "Autotune agent"
    assert len(app.tabs[2].selectbox) == 2
    assert "Architecture" in app.tabs[3].subheader[0].value
    assert "python -m streamlit run app.py" in app.tabs[3].code[0].value
    # Switching the built-in image exercises inspection without changing the layout.
    next(widget for widget in app.selectbox if widget.label == "Built-in sample").select(2).run()
    assert not app.exception
    iterations = next(widget for widget in app.number_input if widget.label == "Maximum iterations")
    iterations.set_value(2)
    next(button for button in app.button if button.label == "Run Autotune").click().run()
    assert not app.exception
    assert "proposal" in app.session_state
    assert len(app.session_state["proposal"][1].trace) == 2
    # Editing an input invalidates the review/export state.
    next(widget for widget in app.slider if widget.label == "Minimum pixel F1").set_value(0.9).run()
    assert any("Inputs changed" in warning.value for warning in app.warning)
    assert not app.exception


def test_demo_label_and_bad_benchmark_file(tmp_path, monkeypatch):
    from coolforge.ui import evidence

    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    (tmp_path / "results").mkdir()
    artifact = tmp_path / "results" / "stock.json"
    artifact.write_text('{"schema_version": 1}', encoding="utf-8")
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    from coolforge.environment import inspect_environment

    if not inspect_environment().opencv5_verified:
        assert any("DEMONSTRATION" in error.value for error in app.error)
    next(widget for widget in app.selectbox if widget.label == "Saved stock measurements").select(
        artifact
    ).run()
    assert not app.exception
    assert any("Cannot use stock result" in error.value for error in app.error)
