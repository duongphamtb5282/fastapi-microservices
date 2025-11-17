"""
Monitoring Integration using NCM Foundation
"""

from ncm_foundation.core.monitoring import \
    HealthCheckManager as FoundationHealthCheckManager

# Re-export foundation health check manager
HealthCheckManager = FoundationHealthCheckManager

__all__ = ["HealthCheckManager"]
