# Makefile for ncm-foundation

.PHONY: help clean install lint test build verify docs install-dev install-prod

# Default target
help:
	@echo "NCM-Foundation Build System"
	@echo "========================="
	@echo ""
	@echo "Available targets:"
	@echo "  help        - Show this help message"
	@echo "  clean       - Clean build artifacts"
	@echo "  install     - Install dependencies"
	@echo "  install-dev - Install development dependencies"
	@echo "  install-prod- Install production dependencies"
	@echo "  lint        - Run code linting"
	@echo "  test        - Run tests"
	@echo "  build       - Build package"
	@echo "  verify      - Verify build"
	@echo "  docs        - Build documentation"
	@echo "  all         - Run full build process"
	@echo "  dev         - Development setup"
	@echo ""

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@echo "✅ Clean completed"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
	else \
		pip install -e .; \
	fi
	@echo "✅ Dependencies installed"

# Install development dependencies
install-dev:
	@echo "📦 Installing development dependencies..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install --with dev; \
	else \
		pip install -e ".[dev]"; \
	fi
	@echo "✅ Development dependencies installed"

# Install production dependencies
install-prod:
	@echo "📦 Installing production dependencies..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install --only main; \
	else \
		pip install -e .; \
	fi
	@echo "✅ Production dependencies installed"

# Run linting
lint:
	@echo "🔍 Running code linting..."
	@black --check src/ scripts/ examples/
	@isort --check-only src/ scripts/ examples/
	@mypy src/
	@echo "✅ Linting passed"

# Run tests
test:
	@echo "🧪 Running tests..."
	@pytest tests/ -v --cov=src/ncm_foundation --cov-report=html --cov-report=term-missing
	@echo "✅ Tests passed"

# Build package
build:
	@echo "📦 Building package..."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry build; \
	else \
		python -m build; \
	fi
	@echo "✅ Package built"

# Verify build
verify:
	@echo "🔍 Verifying build..."
	@if [ -d "dist" ]; then \
		echo "✅ Build artifacts found in dist/"; \
		ls -la dist/; \
	else \
		echo "❌ No dist directory found"; \
		exit 1; \
	fi

# Build documentation
docs:
	@echo "📚 Building documentation..."
	@if command -v mkdocs >/dev/null 2>&1; then \
		mkdocs build; \
		echo "✅ Documentation built"; \
	else \
		echo "⚠️ MkDocs not available, skipping documentation"; \
	fi

# Full build process
all: clean install-dev lint test build verify docs
	@echo "🎉 Full build completed successfully!"

# Development setup
dev: clean install-dev
	@echo "🚀 Development environment ready!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make lint' to check code style"
	@echo "Run 'make build' to build package"

# Quick build (skip tests and linting)
quick: clean install build verify
	@echo "⚡ Quick build completed!"

# Production build
prod: clean install-prod build verify
	@echo "🏭 Production build completed!"
