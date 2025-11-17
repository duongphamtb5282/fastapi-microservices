#!/usr/bin/env python3
"""
Compilation script for ncm-foundation.

This script compiles the ncm-foundation library and creates distributable packages.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_project_info() -> Dict[str, str]:
    """Get project information from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return {"name": "ncm-foundation", "version": "0.1.0"}

    # Simple TOML parsing for basic info
    content = pyproject_path.read_text()
    name = "ncm-foundation"
    version = "0.1.0"

    for line in content.split("\n"):
        if line.strip().startswith("name = "):
            name = line.split('"')[1]
        elif line.strip().startswith("version = "):
            version = line.split('"')[1]

    return {"name": name, "version": version}


def check_dependencies() -> bool:
    """Check if required dependencies are available."""
    print("🔍 Checking dependencies...")

    required_commands = ["python", "pip"]
    optional_commands = ["poetry", "black", "isort", "mypy", "pytest"]

    missing_required = []
    missing_optional = []

    for cmd in required_commands:
        if not shutil.which(cmd):
            missing_required.append(cmd)

    for cmd in optional_commands:
        if not shutil.which(cmd):
            missing_optional.append(cmd)

    if missing_required:
        print(f"❌ Missing required dependencies: {', '.join(missing_required)}")
        return False

    if missing_optional:
        print(f"⚠️ Missing optional dependencies: {', '.join(missing_optional)}")
        print("   Some features may not be available")

    print("✅ Dependencies check passed")
    return True


def clean_build_artifacts():
    """Clean all build artifacts."""
    print("🧹 Cleaning build artifacts...")

    # Directories to clean
    dirs_to_clean = [
        "build",
        "dist",
        "*.egg-info",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov",
    ]

    for pattern in dirs_to_clean:
        for path in project_root.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  Removed: {path}")
            elif path.is_file():
                path.unlink()
                print(f"  Removed: {path}")

    # Remove Python cache files recursively
    for pycache in project_root.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
            print(f"  Removed: {pycache}")


def install_build_dependencies():
    """Install build dependencies."""
    print("📦 Installing build dependencies...")

    try:
        # Try to install build tools
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "build",
                "wheel",
                "setuptools",
                "twine",
            ],
            check=True,
            capture_output=True,
        )
        print("✅ Build dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install build dependencies: {e}")
        return False


def run_code_quality_checks():
    """Run code quality checks."""
    print("🔍 Running code quality checks...")

    checks_passed = True

    # Black formatting check
    try:
        print("  Running Black...")
        subprocess.run(
            ["black", "--check", "src/", "scripts/"], check=True, capture_output=True
        )
        print("  ✅ Black check passed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ⚠️ Black not available or failed")
        checks_passed = False

    # isort import sorting check
    try:
        print("  Running isort...")
        subprocess.run(
            ["isort", "--check-only", "src/", "scripts/"],
            check=True,
            capture_output=True,
        )
        print("  ✅ isort check passed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ⚠️ isort not available or failed")
        checks_passed = False

    # MyPy type checking
    try:
        print("  Running MyPy...")
        subprocess.run(["mypy", "src/"], check=True, capture_output=True)
        print("  ✅ MyPy check passed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ⚠️ MyPy not available or failed")
        checks_passed = False

    return checks_passed


def run_tests():
    """Run tests."""
    print("🧪 Running tests...")

    try:
        # Check if pytest is available
        subprocess.run(["pytest", "--version"], check=True, capture_output=True)

        # Run tests
        subprocess.run(
            [
                "pytest",
                "tests/",
                "-v",
                "--cov=src/ncm_foundation",
                "--cov-report=html",
                "--cov-report=term-missing",
            ],
            check=True,
        )

        print("✅ Tests passed")
        return True

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Tests not available or failed")
        return False


def build_package():
    """Build the package."""
    print("📦 Building package...")

    try:
        # Try Poetry first
        if shutil.which("poetry"):
            print("  Using Poetry...")
            subprocess.run(["poetry", "build"], check=True)
        else:
            # Fallback to setuptools
            print("  Using setuptools...")
            subprocess.run([sys.executable, "-m", "build"], check=True)

        print("✅ Package built successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False


def verify_package():
    """Verify the built package."""
    print("🔍 Verifying package...")

    dist_dir = project_root / "dist"
    if not dist_dir.exists():
        print("❌ No dist directory found")
        return False

    # Check for wheel files
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel files found")
        return False

    print(f"✅ Found {len(wheel_files)} package(s):")
    for wheel in wheel_files:
        print(f"  - {wheel.name} ({wheel.stat().st_size} bytes)")

    # Try to install the wheel to verify it works
    try:
        print("  Testing package installation...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                str(wheel_files[0]),
                "--force-reinstall",
                "--no-deps",
            ],
            check=True,
            capture_output=True,
        )
        print("✅ Package installation test passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Package installation test failed: {e}")
        return False


def create_manifest():
    """Create a manifest file with build information."""
    print("📄 Creating build manifest...")

    project_info = get_project_info()
    manifest = {
        "name": project_info["name"],
        "version": project_info["version"],
        "build_timestamp": str(Path(__file__).stat().st_mtime),
        "python_version": sys.version,
        "platform": sys.platform,
        "packages": [],
    }

    # Add package information
    dist_dir = project_root / "dist"
    if dist_dir.exists():
        for package_file in dist_dir.glob("*"):
            manifest["packages"].append(
                {
                    "name": package_file.name,
                    "size": package_file.stat().st_size,
                    "type": "wheel" if package_file.suffix == ".whl" else "source",
                }
            )

    # Write manifest
    manifest_path = project_root / "build_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✅ Manifest created: {manifest_path}")
    return True


def main():
    """Main compilation process."""
    print("🚀 Compiling ncm-foundation...")
    print("=" * 50)

    # Parse command line arguments
    args = sys.argv[1:]
    skip_tests = "--skip-tests" in args
    skip_checks = "--skip-checks" in args
    clean_only = "--clean-only" in args

    if clean_only:
        clean_build_artifacts()
        return 0

    try:
        # Step 1: Check dependencies
        if not check_dependencies():
            print("❌ Dependency check failed")
            return 1

        # Step 2: Clean build artifacts
        clean_build_artifacts()

        # Step 3: Install build dependencies
        if not install_build_dependencies():
            print("❌ Failed to install build dependencies")
            return 1

        # Step 4: Code quality checks
        if not skip_checks:
            if not run_code_quality_checks():
                print("⚠️ Code quality checks failed, but continuing...")

        # Step 5: Run tests
        if not skip_tests:
            if not run_tests():
                print("⚠️ Tests failed, but continuing...")

        # Step 6: Build package
        if not build_package():
            print("❌ Build failed")
            return 1

        # Step 7: Verify package
        if not verify_package():
            print("⚠️ Package verification failed, but build artifacts exist")

        # Step 8: Create manifest
        create_manifest()

        print("=" * 50)
        print("🎉 Compilation completed successfully!")
        print(f"📦 Package location: {project_root / 'dist'}")

        # Show next steps
        print("\n📋 Next steps:")
        print("  1. Test the package: pip install dist/*.whl")
        print("  2. Upload to PyPI: twine upload dist/*")
        print("  3. Create Docker image: docker build -t ncm-foundation .")

        return 0

    except KeyboardInterrupt:
        print("\n❌ Compilation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Compilation failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
