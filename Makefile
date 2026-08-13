.PHONY: all artifacts site payload bundle check lint test validate freshness

all: artifacts

artifacts:
	uv run python -m qslex.build

site:
	uv run python -m qslex.desk

payload:
	uv run python -m qslex.payload

bundle:
	cd editor/server && npm ci --no-audit --no-fund && npm run bundle

check: lint test validate freshness

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

test:
	uv run pytest

validate:
	uv run python -m qslex.validate

freshness:
	uv run python -m qslex.build --check
	uv run python -m qslex.desk --check
	uv run python -m qslex.payload --check
