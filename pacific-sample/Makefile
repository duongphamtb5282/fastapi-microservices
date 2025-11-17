# NCM Sample Makefile

.PHONY: help install dev prod test clean migrate-up migrate-down migrate-current migrate-create migrate-history

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install dependencies"
	@echo "  dev              Run in development mode"
	@echo "  prod             Run in production mode"
	@echo "  test             Run tests"
	@echo "  clean            Clean up temporary files"
	@echo "  migrate-up       Run database migrations (dev)"
	@echo "  migrate-up-prod  Run database migrations (prod)"
	@echo "  migrate-down     Downgrade database (dev)"
	@echo "  migrate-current  Show current migration (dev)"
	@echo "  migrate-create   Create new migration"
	@echo "  migrate-history  Show migration history (dev)"

# Install dependencies
install:
	pip install -e .

# Development mode
dev:
	ENVIRONMENT=dev python -m uvicorn src.ncm_sample.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
prod:
	ENVIRONMENT=prod python -m uvicorn src.ncm_sample.main:app --host 0.0.0.0 --port 8000

# Run tests
test:
	python -m pytest tests/ -v

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

# Database migrations
migrate-up:
	python scripts/migrate.py upgrade --env=dev

migrate-up-prod:
	python scripts/migrate.py upgrade --env=prod

migrate-down:
	python scripts/migrate.py downgrade --env=dev --revision=$(REVISION)

migrate-current:
	python scripts/migrate.py current --env=dev

migrate-create:
	python scripts/migrate.py create --message="$(MESSAGE)"

migrate-history:
	python scripts/migrate.py history --env=dev

# Docker commands
docker-build:
	docker build -t ncm-sample .

docker-run:
	docker run -p 8000:8000 --env-file .env.dev ncm-sample

# Format code
format:
	black src/ scripts/ tests/
	isort src/ scripts/ tests/

# Lint code
lint:
	black --check src/ scripts/ tests/
	isort --check-only src/ scripts/ tests/
	flake8 src/ scripts/ tests/
