"""Test minimal TUI v3 — manual integration test, requires display terminal."""
import pytest

pytestmark = pytest.mark.skip(reason="requires display terminal and CSS file")

# This module imports from tui.app which needs a real terminal
# Keep the test logic for manual runs, skip in CI
