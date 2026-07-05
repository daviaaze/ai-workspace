.PHONY: test lint format check dev worker dashboard validate-setup deploy-setup

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

# ── Go TUI (aiw-tui) ──────────────────────────────

build-tui:
	cd tui && go build -o ../dist/aiw-tui .

run-tui:
	dist/aiw-tui

test-tui:
	cd tui && go vet ./... && go test ./...

build-tui-linux:
	cd tui && GOOS=linux GOARCH=amd64 go build -o ../dist/aiw-tui-linux-amd64 .

clean-tui:
	rm -f dist/aiw-tui

worker:
	$(PYTHON) -m ai_workspace.cli worker

dashboard:
	streamlit run src/ai_workspace/dashboard/app.py

shell:
	nix develop

init:
	createdb ai_workspace 2>/dev/null || true
	$(PYTHON) -m ai_workspace.cli init

validate-setup:
	./pi-setup/validate.sh

deploy-setup:
	./pi-setup/deploy.sh

install-browser:
	@echo "Installing browser-use (autonomous browser agent)..."
	pip install "browser-use>=0.13.0"
	@echo "Done. Use: aiw agent 'Scrape https://example.com'"
