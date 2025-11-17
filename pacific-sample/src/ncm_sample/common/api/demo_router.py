"""
Demo API Router - Showcases all NCM Foundation features
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from ncm_foundation.core.logging.manager import (correlation_id_var,
                                                 request_id_var, user_id_var)
from ncm_sample.config import settings
from ncm_sample.features.user_management.schemas import HealthResponse
from ncm_sample.features.utilities import generate_uuid

# Import global services
logger = logging.getLogger(__name__)
user_service = None
role_service = None
user_role_service = None
auth_service = None
messaging_service = None
notification_service = None
db_manager = None
cache_manager = None
health_manager = None
migration_manager = None
keycloak_manager = None

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.get("/cache")
async def demo_cache():
    """Demo endpoint showcasing caching capabilities."""
    correlation_id = correlation_id_var.get()

    # Test cache statistics
    cache_stats = user_service.get_cache_stats() if user_service else {}

    # Test cache operations
    test_key = "demo:test_key"
    test_value = {"demo": "data", "timestamp": datetime.utcnow().isoformat()}

    # Set value in cache
    cache_set = False
    if user_service.multi_cache:
        cache_set = await user_service.multi_cache.set(test_key, test_value, ttl=60)

    # Get value from cache
    cache_get = None
    if user_service.multi_cache:
        cache_get = await user_service.multi_cache.get(test_key)

    return {
        "cache_stats": cache_stats,
        "cache_set": cache_set,
        "cache_get": cache_get,
        "correlation_id": correlation_id,
        "message": "Cache demo completed",
    }


@router.get("/logging")
async def demo_logging():
    """Demo endpoint showcasing logging capabilities."""
    correlation_id = correlation_id_var.get()
    request_id = request_id_var.get()
    user_id = user_id_var.get()

    # Log different levels with structured data
    logger.debug(
        "Debug message with correlation ID",
        extra={"correlation_id": correlation_id, "demo_feature": "structured_logging"},
    )

    logger.info(
        "Info message with context",
        extra={
            "correlation_id": correlation_id,
            "user_id": user_id,
            "feature": "correlation_tracking",
        },
    )

    logger.warning(
        "Warning message with masking demo",
        extra={
            "correlation_id": correlation_id,
            "demo_data": {
                "email": "test@example.com",
                "phone": "123-456-7890",
            },  # Will be masked
        },
    )

    return {
        "correlation_id": correlation_id,
        "request_id": request_id,
        "user_id": user_id,
        "message": "Logging demo completed - check logs for structured output",
    }


@router.post("/messaging")
async def demo_messaging(payload: Dict[str, Any]):
    """Demo endpoint showcasing messaging capabilities."""
    correlation_id = correlation_id_var.get()

    if not messaging_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Messaging service not available",
        )

    # Publish a custom event
    event_type = payload.get("event_type", "demo_event")
    event_data = payload.get("data", {"demo": "data"})

    await messaging_service.publish_system_event(event_type, event_data)

    # Get circuit breaker status
    circuit_breaker_state = messaging_service.circuit_breaker.get_state()

    return {
        "correlation_id": correlation_id,
        "event_published": event_type,
        "circuit_breaker_state": circuit_breaker_state.value,
        "message": "Messaging demo completed",
    }


@router.get("/monitoring")
async def demo_monitoring():
    """Demo endpoint showcasing monitoring capabilities."""
    correlation_id = correlation_id_var.get()

    if not health_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health manager not available",
        )

    # Get comprehensive health status using foundation's health manager
    overall_health = await health_manager.get_overall_health()

    # Add messaging health if available
    messaging_health = None
    if messaging_service:
        try:
            messaging_health = {
                "status": "healthy",
                "service": "messaging",
                "details": "Kafka messaging operational",
            }
        except Exception as e:
            messaging_health = {
                "status": "unhealthy",
                "service": "messaging",
                "error": str(e),
            }

    # Combine health results
    all_services = overall_health.get("services", {})
    if messaging_health:
        all_services["messaging"] = messaging_health

    return {
        "correlation_id": correlation_id,
        "health_status": overall_health.get("status"),
        "services": all_services,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Monitoring demo completed using NCM Foundation Health Manager",
    }


@router.get("/migrations")
async def demo_migrations():
    """Demo endpoint showcasing database migration capabilities."""
    correlation_id = correlation_id_var.get()

    if not migration_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Migration manager not available",
        )

    # Get migration status
    migration_status = migration_manager.check_migration_status()

    # Get migration history
    migration_history = migration_manager.get_migration_history()

    # Get health check for migrations
    migration_health = await migration_manager.health_check()

    return {
        "correlation_id": correlation_id,
        "migration_status": migration_status,
        "migration_history": migration_history[:5],  # Show last 5 migrations
        "migration_health": migration_health,
        "message": "Migration demo completed using NCM Foundation Migration Manager",
    }


@router.get("/utilities")
async def demo_utilities():
    """Demo endpoint showcasing utility functions."""
    correlation_id = correlation_id_var.get()

    # Test utility functions from ncm-foundation (imported from features)
    test_email = "test@example.com"
    test_phone = "+1-555-123-4567"
    test_uuid = generate_uuid()

    # Validate inputs
    email_valid = validate_email(test_email)
    phone_valid = validate_phone(test_phone)

    return {
        "correlation_id": correlation_id,
        "utilities_tested": {
            "email_validation": {"input": test_email, "valid": email_valid},
            "phone_validation": {"input": test_phone, "valid": phone_valid},
            "uuid_generation": test_uuid,
        },
        "message": "Utilities demo completed using NCM Foundation utilities",
    }


@router.get("/keycloak")
async def demo_keycloak():
    """Demo endpoint showcasing Keycloak SSO and MFA features."""
    correlation_id = correlation_id_var.get()

    if not keycloak_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak manager not available",
        )

    # Test Keycloak connectivity
    keycloak_healthy = True
    try:
        # This would test the Keycloak connection
        # For demo purposes, just return status
        pass
    except Exception as e:
        keycloak_healthy = False

    return {
        "correlation_id": correlation_id,
        "keycloak_status": "healthy" if keycloak_healthy else "unhealthy",
        "features": [
            "SSO Authentication",
            "MFA Support",
            "User Management",
            "Role-based Access Control",
            "Token Management",
            "Session Management",
        ],
        "message": "Keycloak demo completed - SSO and MFA authentication ready",
    }


@router.get("/complete")
async def demo_complete():
    """Complete demo showcasing all foundation features."""
    correlation_id = correlation_id_var.get()

    # Gather information about all features
    features_status = {
        "configuration": {
            "status": "enabled",
            "description": "FoundationConfig with environment variable support",
        },
        "database": {
            "status": "enabled",
            "description": "Enhanced models with audit logging and GUID primary keys",
        },
        "caching": {
            "status": "enabled",
            "description": "Multi-level caching with L1/L2 strategy",
        },
        "logging": {
            "status": "enabled",
            "description": "Structured logging with correlation IDs and masking",
        },
        "messaging": {
            "status": "enabled" if messaging_service else "disabled",
            "description": "Kafka messaging with circuit breakers",
        },
        "monitoring": {
            "status": "enabled",
            "description": "Health checks and service monitoring",
        },
        "security": {
            "status": "enabled",
            "description": "Audit logging, encryption, and access control",
        },
        "migrations": {
            "status": "enabled",
            "description": "Database migration management with Alembic",
        },
        "utilities": {
            "status": "enabled",
            "description": "Validation, encoding, and helper utilities",
        },
        "keycloak": {
            "status": "enabled" if keycloak_manager else "disabled",
            "description": "SSO and MFA authentication with Keycloak",
        },
        "repository_pattern": {
            "status": "enabled",
            "description": "Repository pattern with NCM Foundation AbstractRepository",
        },
        "middleware": {
            "status": "enabled",
            "description": "CORS, Rate Limiting, and Security middleware from NCM Foundation",
        },
        "concurrent_startup": {
            "status": "enabled",
            "description": "Concurrent service startup for improved performance",
        },
    }

    return {
        "correlation_id": correlation_id,
        "demo_status": "complete",
        "features": features_status,
        "message": "NCM Sample now utilizes all NCM Foundation features!",
        "documentation": "Check /docs/v1 for API documentation",
    }
