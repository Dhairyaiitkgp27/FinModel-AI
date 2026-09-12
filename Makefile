.PHONY: help install install-dev smoke test eval lint format run docker clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	pip install -r requirements.txt

install-dev: install  ## Install dev tooling (ruff) as well
	pip install ruff

smoke:  ## Run the smoke test (loads sample data, runs the full stack)
	python app.py

test:  ## Run the test suite
	pytest -q

eval:  ## Run the agent-evaluation suite
	python -m evals

lint:  ## Lint with ruff
	ruff check .

format:  ## Auto-format and fix with ruff
	ruff format .
	ruff check . --fix

run:  ## Launch the Streamlit dashboard
	streamlit run app.py

docker:  ## Build and run the dashboard in Docker
	docker compose up --build

clean:  ## Remove caches and build artefacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .ruff_cache build dist *.egg-info
