"""Simple Dependency Injection Container for NCM Sample."""

from typing import Dict, Type, Any, Callable, Optional, TypeVar
from functools import lru_cache
import inspect

T = TypeVar('T')

class DIContainer:
    """Dependency Injection Container with automatic dependency resolution."""
    
    def __init__(self):
        self._services: Dict[str, Type] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._instances: Dict[str, Any] = {}
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a singleton service."""
        self._services[interface.__name__] = implementation
        self._singletons[interface.__name__] = None
    
    def register_factory(self, interface: Type[T], factory: Callable) -> None:
        """Register a factory function."""
        self._factories[interface.__name__] = factory
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a specific instance."""
        self._instances[interface.__name__] = instance
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a transient service (new instance each time)."""
        self._services[interface.__name__] = implementation
    
    @lru_cache()
    def get(self, interface: Type[T]) -> T:
        """Get service instance with dependency injection."""
        interface_name = interface.__name__
        
        # Check if instance is already registered
        if interface_name in self._instances:
            return self._instances[interface_name]
        
        # Check if singleton exists
        if interface_name in self._singletons and self._singletons[interface_name] is not None:
            return self._singletons[interface_name]
        
        # Check if service is registered
        if interface_name in self._services:
            implementation = self._services[interface_name]
            if inspect.isclass(implementation):
                # Auto-inject dependencies
                instance = self._create_instance(implementation)
                if interface_name in self._singletons:
                    self._singletons[interface_name] = instance
                return instance
            return implementation
        
        # Check if factory is registered
        if interface_name in self._factories:
            instance = self._factories[interface_name]()
            if interface_name in self._singletons:
                self._singletons[interface_name] = instance
            return instance
        
        raise ValueError(f"Service {interface_name} not registered")
    
    def _create_instance(self, cls: Type[T]) -> T:
        """Create instance with automatic dependency injection."""
        sig = inspect.signature(cls.__init__)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = self.get(param.annotation)
                except ValueError:
                    # If dependency not found, use default value
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        # Try to create with empty kwargs if no default
                        pass
        
        return cls(**kwargs)
    
    def clear_cache(self) -> None:
        """Clear the LRU cache."""
        self.get.cache_clear()
    
    def is_registered(self, interface: Type[T]) -> bool:
        """Check if a service is registered."""
        interface_name = interface.__name__
        return (interface_name in self._services or 
                interface_name in self._factories or 
                interface_name in self._instances)

# Global container instance
_container: Optional[DIContainer] = None

def get_container() -> DIContainer:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container

def reset_container() -> None:
    """Reset the global container instance."""
    global _container
    _container = None


def get_provider(key: Any):
    """Return a FastAPI-compatible dependency callable that resolves `key` from the container."""

    def _dep():
        return get_container().get(key)

    return _dep
