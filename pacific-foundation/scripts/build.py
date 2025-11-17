#!/usr/bin/env python3
"""
Build script for ncm-foundation.

This script handles building, testing, and packaging the ncm-foundation library.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(
    cmd: List[str], cwd: Optional[Path] = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, cwd=cwd or project_root, check=check, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        raise


def clean_build():
    """Clean build artifacts."""
    print("🧹 Cleaning build artifacts...")

    # Remove build directories
    dirs_to_clean = [
        "build",
        "dist",
        "*.egg-info",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    ]
    for pattern in dirs_to_clean:
        for path in project_root.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"Removed: {path}")

    # Remove Python cache files
    for pycache in project_root.rglob("__pycache__"):
        shutil.rmtree(pycache)
        print(f"Removed: {pycache}")


def install_dependencies():
    """Install project dependencies."""
    print("📦 Installing dependencies...")

    # Check if poetry is available
    try:
        run_command(["poetry", "--version"])
        print("Using Poetry for dependency management")

        # Install dependencies
        run_command(["poetry", "install", "--with", "dev"])

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Poetry not found, trying pip...")

        # Try to install with pip
        try:
            run_command([sys.executable, "-m", "pip", "install", "-e", "."])
        except subprocess.CalledProcessError:
            print("Failed to install dependencies with pip")
            return False

    return True


def run_linting():
    """Run code linting."""
    print("🔍 Running code linting...")

    try:
        # Run black
        print("Running Black...")
        run_command(["black", "--check", "src/", "scripts/", "examples/"])

        # Run isort
        print("Running isort...")
        run_command(["isort", "--check-only", "src/", "scripts/", "examples/"])

        # Run mypy
        print("Running mypy...")
        run_command(["mypy", "src/"])

        print("✅ Linting passed!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Linting failed: {e}")
        return False


def run_tests():
    """Run tests."""
    print("🧪 Running tests...")

    try:
        # Run pytest
        run_command(
            [
                "pytest",
                "tests/",
                "-v",
                "--cov=src/ncm_foundation",
                "--cov-report=html",
                "--cov-report=term-missing",
            ]
        )

        print("✅ Tests passed!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
        return False


def build_package():
    """Build the package."""
    print("📦 Building package...")

    try:
        # Clean dist directory
        dist_dir = project_root / "dist"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)

        # Build with poetry
        try:
            run_command(["poetry", "build"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to setuptools
            print("Poetry not available, using setuptools...")
            run_command([sys.executable, "-m", "build"])

        print("✅ Package built successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False


def verify_build():
    """Verify the build."""
    print("🔍 Verifying build...")

    dist_dir = project_root / "dist"
    if not dist_dir.exists():
        print("❌ No dist directory found")
        return False

    # Check for wheel files
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel files found")
        return False

    print(f"✅ Found {len(wheel_files)} wheel file(s):")
    for wheel in wheel_files:
        print(f"  - {wheel.name}")

    # Try to install the wheel
    try:
        print("Testing wheel installation...")
        run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                str(wheel_files[0]),
                "--force-reinstall",
            ]
        )
        print("✅ Wheel installation test passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Wheel installation test failed: {e}")
        return False


def create_documentation():
    """Create documentation."""
    print("📚 Creating documentation...")

    try:
        # Check if mkdocs is available
        run_command(["mkdocs", "--version"])

        # Build documentation
        run_command(["mkdocs", "build"])

        print("✅ Documentation created!")
        return True

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ MkDocs not available, skipping documentation")
        return True


def main():
    """Main build process."""
    print("🚀 Building ncm-foundation...")
    print("=" * 50)

    # Parse command line arguments
    args = sys.argv[1:]
    skip_tests = "--skip-tests" in args
    skip_lint = "--skip-lint" in args
    clean_only = "--clean-only" in args

    if clean_only:
        clean_build()
        return

    try:
        # Step 1: Clean
        clean_build()

        # Step 2: Install dependencies
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            return 1

        # Step 3: Linting
        if not skip_lint:
            if not run_linting():
                print("❌ Linting failed")
                return 1

        # Step 4: Tests
        if not skip_tests:
            if not run_tests():
                print("❌ Tests failed")
                return 1

        # Step 5: Build package
        if not build_package():
            print("❌ Build failed")
            return 1

        # Step 6: Verify build
        if not verify_build():
            print("❌ Build verification failed")
            return 1

        # Step 7: Documentation
        create_documentation()

        print("=" * 50)
        print("🎉 Build completed successfully!")
        print(f"📦 Package location: {project_root / 'dist'}")

        return 0

    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Build failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
