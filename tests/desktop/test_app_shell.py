"""Desktop application shell and lifecycle smoke tests."""

from veritrace.gui.app import VeriTraceApp


def test_veritrace_app_instantiation():
    """Verify that VeriTraceApp instantiates cleanly with empty arguments."""
    app = VeriTraceApp(["veritrace"])
    assert app.argv == ["veritrace"]


def test_veritrace_app_run_placeholder():
    """Verify that VeriTraceApp run placeholder returns clean exit code 0."""
    app = VeriTraceApp(["veritrace"])
    exit_code = app.run()
    assert exit_code == 0
