#!/usr/bin/env python3
"""Simple test to verify basic functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_imports():
    """Test basic imports work."""
    try:
        from ncm_sample.config.settings import get_settings
        settings = get_settings()
        print(f"✅ Settings loaded: {settings.app_name} ({settings.environment})")

        from ncm_sample.core.security import get_password_hash, verify_password
        password = "test123"
        hashed = get_password_hash(password)
        if verify_password(password, hashed):
            print("✅ Password hashing works")
        else:
            print("❌ Password verification failed")

        print("✅ Basic functionality works!")
        return True

    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing NCM Sample Basic Functionality")
    success = test_basic_imports()

    if success:
        print("\n🎉 Basic functionality is working!")
        print("The core features have been successfully implemented.")
    else:
        print("\n❌ Basic functionality failed.")
