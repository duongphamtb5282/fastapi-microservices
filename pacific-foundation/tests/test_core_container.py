"""Test cases for dependency injection container."""

import pytest
from ncm_foundation.core.container import DIContainer, get_container, reset_container


class TestDIContainer:
    """Test DI Container functionality."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def test_container_singleton(self):
        """Test that get_container returns the same instance."""
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2

    def test_register_singleton(self):
        """Test registering singleton services."""
        container = get_container()

        class TestService:
            pass

        container.register_singleton(TestService, TestService)
        assert container.is_registered(TestService)

        # Should return the same instance
        instance1 = container.get(TestService)
        instance2 = container.get(TestService)
        assert instance1 is instance2

    def test_register_transient(self):
        """Test registering transient services."""
        container = get_container()

        class TestService:
            def __init__(self):
                self.value = id(self)

        container.register_transient(TestService, TestService)

        # Should return different instances
        instance1 = container.get(TestService)
        instance2 = container.get(TestService)
        assert instance1 is not instance2
        assert instance1.value != instance2.value

    def test_register_factory(self):
        """Test registering factory functions."""
        container = get_container()

        def create_service():
            return "factory_instance"

        container.register_factory(str, create_service)

        instance = container.get(str)
        assert instance == "factory_instance"

    def test_register_instance(self):
        """Test registering specific instances."""
        container = get_container()

        test_instance = "specific_instance"
        container.register_instance(str, test_instance)

        instance = container.get(str)
        assert instance is test_instance

    def test_dependency_injection(self):
        """Test automatic dependency injection."""
        container = get_container()

        class Dependency:
            def __init__(self):
                self.value = "dependency"

        class Service:
            def __init__(self, dep: Dependency):
                self.dep = dep

        container.register_singleton(Dependency, Dependency)
        container.register_singleton(Service, Service)

        service = container.get(Service)
        assert isinstance(service.dep, Dependency)
        assert service.dep.value == "dependency"

    def test_missing_service(self):
        """Test that missing services raise appropriate errors."""
        container = get_container()

        with pytest.raises(ValueError, match="Service.*not registered"):
            container.get(str)

    def test_clear_cache(self):
        """Test clearing the LRU cache."""
        container = get_container()
        container.clear_cache()
        # Should not raise any errors
