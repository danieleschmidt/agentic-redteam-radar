.PHONY: help install install-dev test lint format type-check security clean build docs

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in production mode
	pip install .

install-dev:  ## Install package in development mode with dev dependencies
	pip install -e ".[dev]"
	pre-commit install

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=agentic_redteam --cov-report=html --cov-report=term-missing

lint:  ## Run linting
	flake8 src/ tests/

format:  ## Format code
	black .
	isort .

format-check:  ## Check code formatting
	black --check .
	isort --check-only .

type-check:  ## Run type checking
	mypy src/

security:  ## Run security checks
	bandit -r src/
	pip-audit

quality:  ## Run all quality checks
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build:  ## Build package
	python -m build

docs:  ## Build documentation
	mkdocs build

docs-serve:  ## Serve documentation locally
	mkdocs serve

pre-commit:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

setup-dev:  ## Complete development environment setup
	$(MAKE) install-dev
	$(MAKE) pre-commit

ci:  ## Run all CI checks locally
	$(MAKE) quality
	$(MAKE) test-cov