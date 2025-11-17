#!/usr/bin/env python3
"""
API testing script for NCM Sample Project.
"""

import asyncio
import json
import sys
from typing import Any, Dict

import httpx


class APITester:
    """API testing client."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.token: str = None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        """Test health check endpoint."""
        print("🔍 Testing health check...")

        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()

            data = response.json()
            print(f"  Status: {data['status']}")
            print(f"  Services: {data['services']}")
            print("  ✅ Health check passed")
            return data

        except Exception as e:
            print(f"  ❌ Health check failed: {e}")
            return {}

    async def test_cache_stats(self) -> Dict[str, Any]:
        """Test cache statistics endpoint."""
        print("\n📊 Testing cache statistics...")

        try:
            response = await self.client.get(f"{self.base_url}/cache/stats")
            response.raise_for_status()

            data = response.json()
            print(f"  Cache stats: {json.dumps(data, indent=2)}")
            print("  ✅ Cache stats retrieved")
            return data

        except Exception as e:
            print(f"  ❌ Cache stats failed: {e}")
            return {}

    async def test_user_creation(self) -> Dict[str, Any]:
        """Test user creation."""
        print("\n👤 Testing user creation...")

        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "password123",
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/users/",
                json=user_data,
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            print(f"  User created: {data['id']} - {data['email']}")
            print("  ✅ User creation passed")
            return data

        except Exception as e:
            print(f"  ❌ User creation failed: {e}")
            return {}

    async def test_user_retrieval(self, user_id: int) -> Dict[str, Any]:
        """Test user retrieval."""
        print(f"\n🔍 Testing user retrieval (ID: {user_id})...")

        try:
            response = await self.client.get(
                f"{self.base_url}/users/{user_id}",
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            print(f"  User retrieved: {data['email']}")
            print("  ✅ User retrieval passed")
            return data

        except Exception as e:
            print(f"  ❌ User retrieval failed: {e}")
            return {}

    async def test_user_list(self) -> Dict[str, Any]:
        """Test user listing."""
        print("\n📋 Testing user listing...")

        try:
            response = await self.client.get(
                f"{self.base_url}/users/",
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            print(f"  Found {len(data)} users")
            print("  ✅ User listing passed")
            return data

        except Exception as e:
            print(f"  ❌ User listing failed: {e}")
            return {}

    async def test_role_creation(self) -> Dict[str, Any]:
        """Test role creation."""
        print("\n🔐 Testing role creation...")

        role_data = {
            "name": "admin",
            "description": "Administrator role",
            "permissions": '["read", "write", "delete"]',
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/roles/",
                json=role_data,
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            print(f"  Role created: {data['id']} - {data['name']}")
            print("  ✅ Role creation passed")
            return data

        except Exception as e:
            print(f"  ❌ Role creation failed: {e}")
            return {}

    async def test_role_list(self) -> Dict[str, Any]:
        """Test role listing."""
        print("\n📋 Testing role listing...")

        try:
            response = await self.client.get(
                f"{self.base_url}/roles/",
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            print(f"  Found {len(data)} roles")
            print("  ✅ Role listing passed")
            return data

        except Exception as e:
            print(f"  ❌ Role listing failed: {e}")
            return {}

    async def test_cache_operations(self):
        """Test cache operations."""
        print("\n🗄️  Testing cache operations...")

        try:
            # Test cache clear
            response = await self.client.post(
                f"{self.base_url}/cache/clear",
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            print(f"  Cache cleared: {data['message']}")

            # Test pattern clear
            response = await self.client.post(
                f"{self.base_url}/cache/clear/users:*",
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            )
            response.raise_for_status()

            data = response.json()
            print(f"  Pattern cleared: {data['message']}")
            print("  ✅ Cache operations passed")

        except Exception as e:
            print(f"  ❌ Cache operations failed: {e}")

    async def test_login(self, username: str, password: str) -> bool:
        """Test login and get token."""
        print(f"\n🔑 Testing login for {username}...")

        login_data = {"username": username, "password": password}

        try:
            response = await self.client.post(
                f"{self.base_url}/auth/login", json=login_data
            )
            response.raise_for_status()

            data = response.json()
            self.token = data["access_token"]
            print(f"  Login successful: {data['token_type']} token")
            print("  ✅ Login passed")
            return True

        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all API tests."""
        print("🧪 NCM Sample API Testing")
        print("=" * 50)

        try:
            # Health check
            await self.health_check()

            # Cache stats
            await self.test_cache_stats()

            # Test login (this will fail without a user, but that's expected)
            login_success = await self.test_login("test@example.com", "password123")

            if login_success:
                # Test authenticated endpoints
                await self.test_user_creation()
                await self.test_user_list()
                await self.test_role_creation()
                await self.test_role_list()
                await self.test_cache_operations()
            else:
                print("\n⚠️  Skipping authenticated tests (no valid token)")

            print("\n🎉 API testing completed!")

        except Exception as e:
            print(f"\n❌ API testing failed: {e}")
            sys.exit(1)


async def main():
    """Main testing function."""
    tester = APITester()

    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
