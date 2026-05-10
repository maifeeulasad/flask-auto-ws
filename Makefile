.PHONY: help install test test-cov clean lint format

help:
	@echo "flask-auto-ws development helpers"
	@echo "  install   - install the package in editable mode with dev deps"
	@echo "  test      - run tests"
	@echo "  test-cov  - run tests with coverage"
	@echo "  clean     - remove build & cache files"
	@echo "  lint      - run ruff linter"
	@echo "  lint-fix  - run ruff linter with auto-fix"
	@echo "  format    - format code with ruff"

setup:


install:
	@if [ ! -d ".venv" ]; then \
		uv venv; \
	fi
	uv pip install -e ".[dev]"

test:
	uv run pytest -v

test-cov:
	uv run pytest --cov=src/flask_auto_ws --cov-report=term-missing -v

clean:
	rm -rf build dist *.egg-info .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -r {} +

lint:
	uv run ruff check src tests

lint-fix:
	uv run ruff check --fix src tests

format:
	uv run ruff format src tests