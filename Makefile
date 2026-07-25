.PHONY: all artifacts check lint test validate freshness

all: artifacts

artifacts:
	uv run python -m qslex.build

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
