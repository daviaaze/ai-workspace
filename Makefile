.PHONY: test lint format check dev worker dashboard

# NixOS note: crewai → numpy needs libstdc++.so.6
# Use: nix develop --command make test
# Or set: export LD_LIBRARY_PATH=$(nix eval nixpkgs#gcc.cc.lib --raw)/lib

PYTHON := python
TEST_ARGS := -v --tb=short

test:
	$(PYTHON) -m pytest tests/ $(TEST_ARGS)

test-cov:
	$(PYTHON) -m pytest tests/ $(TEST_ARGS) --cov=ai_workspace --cov-report=term-missing

lint:
	ruff check src/
	mypy src/ || true

format:
	ruff format src/

check: lint test

dev:
	textual run --dev src/ai_workspace/tui/app.py 2>/dev/null || echo "Textual not installed"

worker:
	$(PYTHON) -m ai_workspace.cli worker

dashboard:
	streamlit run src/ai_workspace/dashboard/app.py

shell:
	nix develop

init:
	createdb ai_workspace 2>/dev/null || true
	$(PYTHON) -m ai_workspace.cli init

install-browser:
	@echo "Installing browser-use (autonomous browser agent)..."
	pip install "browser-use>=0.13.0"
	@echo "Done. Use: aiw agent 'Scrape https://example.com'"
