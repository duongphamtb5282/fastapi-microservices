"""Decorators for logging, caching, and other cross-cutting concerns."""

from functools import wraps
from typing import Any, Callable, Optional
from ncm_foundation.core.logging import get_logger
from ncm_foundation.core.cache.manager import CacheManager
from ncm_foundation.core.cache.serializers import CacheSerializer, SerializationType
from ncm_foundation.core.cache.reloader import CacheReloader, ReloadStrategy
from ncm_foundation.core.database.transactions import TransactionManager, NestedTransactionManager
import hashlib
import json
import asyncio

def log_method_call(func: Callable) -> Callable:
    """Decorator to log method calls with parameters and results."""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        logger = get_logger(func.__module__)
        
        # Log method entry
        logger.info(
            f"Calling {func.__name__}",
            extra={
                "method": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
        )
        
        try:
            result = await func(*args, **kwargs)
            logger.info(f"Successfully completed {func.__name__}")
            return result
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {str(e)}",
                exc_info=True,
                extra={
                    "method": func.__name__,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise
    
    return wrapper

def cache_result(ttl: int = 300, key_prefix: str = "", cache_manager_factory=None, serialization_type: str = "json"):
    """Decorator to cache method results using CacheManager with foundation serialization."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get cache manager from factory if provided
            cache_manager = None
            if cache_manager_factory and args:
                # For instance methods, args[0] is 'self'
                self_instance = args[0]
                if hasattr(self_instance, 'cache_manager') and self_instance.cache_manager:
                    cache_manager = self_instance.cache_manager

            # If no cache manager available, execute function without caching
            if cache_manager is None:
                return await func(*args, **kwargs)

            # Generate cache key
            cache_key_data = {
                "func": func.__name__,
                "module": func.__module__,
                "args": str(args[1:]),  # Skip 'self' argument
                "kwargs": str(sorted(kwargs.items()))
            }
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"

            try:
                # Try to get from cache first
                cached_result = await cache_manager.get(cache_key, deserialize=True)
                if cached_result is not None:
                    return cached_result
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.warning(f"Cache read failed for {func.__name__}: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            try:
                # Cache the result with serialization
                await cache_manager.set(cache_key, result, expire=ttl, serialize=True)
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.warning(f"Cache write failed for {func.__name__}: {e}")

            return result

        return wrapper
    return decorator


def with_session_transaction():
    """Decorator to execute function within a database session transaction for SQLAlchemy."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get session from the first argument (usually 'self')
            session = None
            if args:
                service_instance = args[0]
                if hasattr(service_instance, 'session') and service_instance.session:
                    session = service_instance.session

            if session is None:
                # Execute without transaction
                logger = get_logger(func.__module__)
                logger.debug(f"No session available for {func.__name__}, executing without transaction")
                return await func(*args, **kwargs)

            # Execute within session transaction
            try:
                async with session.begin():
                    result = await func(*args, **kwargs)
                    return result
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.error(f"Session transaction failed for {func.__name__}: {e}")
                raise

        return wrapper
    return decorator


def with_transaction(transaction_manager: Optional[TransactionManager] = None):
    """Decorator to execute function within a database transaction using ncm-foundation TransactionManager."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get transaction manager from parameter or from service instance
            tm = transaction_manager

            if tm is None and args:
                # Try to get transaction manager from the first argument (usually 'self')
                service_instance = args[0]
                if hasattr(service_instance, 'transaction_manager') and service_instance.transaction_manager is not None:
                    tm = service_instance.transaction_manager

            if tm is None:
                # Execute without transaction
                logger = get_logger(func.__module__)
                logger.debug(f"No transaction manager available for {func.__name__}, executing without transaction")
                return await func(*args, **kwargs)

            # Execute within transaction using ncm-foundation TransactionManager
            try:
                async with tm.get_transaction() as transaction:
                    result = await func(*args, **kwargs)
                    return result
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.error(f"Transaction failed for {func.__name__}: {e}")
                raise

        return wrapper

    # If called without parentheses, return the decorator
    if transaction_manager is not None and not callable(transaction_manager):
        # It's being called as @with_transaction(some_manager)
        return decorator

    # If called with parentheses or no arguments, return the decorator function
    return decorator


def with_nested_transaction(nested_transaction_manager: Optional[NestedTransactionManager] = None):
    """Decorator to execute function within a nested database transaction."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get nested transaction manager from parameter or from service instance
            ntm = nested_transaction_manager

            if ntm is None and args:
                # Try to get nested transaction manager from the first argument
                service_instance = args[0]
                if hasattr(service_instance, 'nested_transaction_manager'):
                    ntm = service_instance.nested_transaction_manager

            if ntm is None:
                # Execute without nested transaction
                return await func(*args, **kwargs)

            # Execute within nested transaction
            async with ntm.begin_nested() as nested_tx:
                result = await func(*args, **kwargs)
                return result

        return wrapper
    return decorator


def with_session_transaction():
    """Decorator to execute function within a database session transaction for SQLAlchemy."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get session from the first argument (usually 'self')
            session = None
            if args:
                service_instance = args[0]
                if hasattr(service_instance, 'session') and service_instance.session:
                    session = service_instance.session

            if session is None:
                # Execute without transaction
                logger = get_logger(func.__module__)
                logger.debug(f"No session available for {func.__name__}, executing without transaction")
                return await func(*args, **kwargs)

            # Execute within session transaction
            try:
                async with session.begin():
                    result = await func(*args, **kwargs)
                    return result
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.error(f"Session transaction failed for {func.__name__}: {e}")
                raise

        return wrapper
    return decorator


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry method on exception."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger = get_logger(func.__module__)
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger = get_logger(func.__module__)
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                        raise last_exception
            
            raise last_exception
        
        return wrapper
    return decorator


def with_session_transaction():
    """Decorator to execute function within a database session transaction for SQLAlchemy."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get session from the first argument (usually 'self')
            session = None
            if args:
                service_instance = args[0]
                if hasattr(service_instance, 'session') and service_instance.session:
                    session = service_instance.session

            if session is None:
                # Execute without transaction
                logger = get_logger(func.__module__)
                logger.debug(f"No session available for {func.__name__}, executing without transaction")
                return await func(*args, **kwargs)

            # Execute within session transaction
            try:
                async with session.begin():
                    result = await func(*args, **kwargs)
                    return result
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.error(f"Session transaction failed for {func.__name__}: {e}")
                raise

        return wrapper
    return decorator

def validate_input(schema_class: type):
    """Decorator to validate input using Pydantic schema."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Validate first argument if it's a dict
            if args and isinstance(args[0], dict):
                validated_data = schema_class(**args[0])
                new_args = (validated_data,) + args[1:]
                return await func(*new_args, **kwargs)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_session_transaction():
    """Decorator to execute function within a database session transaction for SQLAlchemy."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get session from the first argument (usually 'self')
            session = None
            if args:
                service_instance = args[0]
                if hasattr(service_instance, 'session') and service_instance.session:
                    session = service_instance.session

            if session is None:
                # Execute without transaction
                logger = get_logger(func.__module__)
                logger.debug(f"No session available for {func.__name__}, executing without transaction")
                return await func(*args, **kwargs)

            # Execute within session transaction
            try:
                async with session.begin():
                    result = await func(*args, **kwargs)
                    return result
            except Exception as e:
                logger = get_logger(func.__module__)
                logger.error(f"Session transaction failed for {func.__name__}: {e}")
                raise

        return wrapper
    return decorator
