#!/usr/bin/env python3
"""
Setup script for ncm-foundation.

This is a fallback setup script for building the package when Poetry is not available.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read version from version.py
version_path = Path(__file__).parent / "src" / "ncm_foundation" / "version.py"
if version_path.exists():
    exec(version_path.read_text())
    __version__ = locals().get("__version__", "0.1.0")
else:
    __version__ = "0.1.0"

setup(
    name="ncm-foundation",
    version=__version__,
    description="NCM Foundation Library for Microservices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="NCM Team",
    author_email="dev@ncm.com",
    license="MIT",
    url="https://github.com/ncm/ncm-foundation",
    project_urls={
        "Bug Reports": "https://github.com/ncm/ncm-foundation/issues",
        "Source": "https://github.com/ncm/ncm-foundation",
        "Documentation": "https://ncm-foundation.readthedocs.io/",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        # Core dependencies
        "fastapi>=0.100.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        
        # Database dependencies
        "sqlalchemy>=2.0.19",
        "alembic>=1.11.0",
        "asyncpg>=0.28.0",
        "aiomysql>=0.2.0",
        "aiosqlite>=0.19.0",
        "motor>=3.0.0",
        "pymongo>=4.0.0",
        
        # Cache dependencies
        "redis>=4.5.0",
        "aiocache>=0.12.0",
        "aioredis>=2.0.0",
        "diskcache>=5.4.0",
        
        # Logging dependencies
        "structlog>=23.0.0",
        "loguru>=0.7.0",
        "python-json-logger>=2.0.0",
        "colorlog>=6.7.0",
        "elasticsearch>=8.0.0",
        
        # Messaging dependencies
        "kafka-python>=2.0.2",
        "celery>=5.3.0",
        "tenacity>=8.2.0",
        "circuitbreaker>=1.4.0",
        "backoff>=2.2.0",
        
        # Security dependencies
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "authlib>=1.2.0",
        "requests-oauthlib>=1.3.0",
        "pyjwt>=2.8.0",
        "cryptography>=41.0.0",
        "bcrypt>=4.0.0",
        "argon2-cffi>=21.3.0",
        
        # HTTP and networking
        "httpx>=0.24.0",
        "requests>=2.31.0",
        
        # Monitoring and metrics
        "prometheus-client>=0.17.0",
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-instrumentation-fastapi>=0.41b0",
        
        # Utilities
        "python-dotenv>=1.0.0",
        "click>=8.1.0",
        "typer>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.2",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
            "ruff>=0.1.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocs-mermaid2-plugin>=1.1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: System :: Logging",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    keywords="microservices, foundation, cache, database, logging, messaging, security",
    include_package_data=True,
    zip_safe=False,
)
