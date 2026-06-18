"""Dashboard module — Streamlit web interface."""

def run_dashboard():
    from ai_workspace.dashboard.app import run_dashboard as _run
    return _run()

__all__ = ["run_dashboard"]
