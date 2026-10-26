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
