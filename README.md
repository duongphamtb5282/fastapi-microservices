# Pacific Microservices Suite

A comprehensive collection of microservices and foundation libraries built with Python, FastAPI, and modern best practices.

## Overview

This repository contains multiple interconnected projects that form a complete microservices ecosystem:

- **pacific-foundation**: Core foundation library providing infrastructure components
- **pacific-auth-service**: Authentication and authorization service
- **pacific-sample**: Sample application demonstrating the use of foundation components

## Projects

### 🏗️ Pacific Foundation

A comprehensive foundation library providing core infrastructure components for microservices including:

- Multi-database support (PostgreSQL, MongoDB, MySQL, SQLite)
- Advanced caching system with multi-level support
- Structured logging with rotation and masking
- Async messaging with Kafka integration
- Security and authentication utilities
- Monitoring and health checks

See [pacific-foundation/README.md](pacific-foundation/README.md) for detailed documentation.

### 🔐 Pacific Auth Service

Authentication and authorization service built on top of the foundation library.

See [pacific-auth-service/README.md](pacific-auth-service/README.md) for detailed documentation.

### 📝 Pacific Sample

Sample application demonstrating how to use the foundation library components in a real-world scenario.

See [pacific-sample/README.md](pacific-sample/README.md) for detailed documentation.

## Getting Started

### Prerequisites

- Python 3.10+
- Poetry (recommended) or pip
- Docker and Docker Compose (for local development)

### Installation

Each project can be installed independently. Navigate to the project directory and follow its specific installation instructions.

For example, to install the foundation library:

```bash
cd pacific-foundation
poetry install
```

## Development

### Project Structure

```
.
├── pacific-foundation/      # Core foundation library
├── pacific-auth-service/    # Authentication service
└── pacific-sample/          # Sample application
```

### Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see individual project LICENSE files for details.

## Support

For issues and questions, please refer to the individual project documentation or create an issue in the repository.

