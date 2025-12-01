.PHONY: help install test run clean lint format check

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make run        - Run development server"
	@echo "  make lint       - Run linter"
	@echo "  make format     - Format code"
	@echo "  make check      - Run all checks (lint + test)"
	@echo "  make clean      - Clean cache and build files"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --tb=short

run:
	uvicorn main:app --host 0.0.0.0 --port 8080 --reload

lint:
	ruff check .

format:
	black .
	ruff check --fix .

check: lint test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache
