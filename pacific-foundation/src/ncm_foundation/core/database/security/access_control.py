"""
Row-level security and access control for databases.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import event, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for data access."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RowLevelSecurity:
    """Row-level security implementation."""

    def __init__(self, user_context: Dict[str, Any]):
        self.user_context = user_context
        self.user_id = user_context.get("user_id")
        self.roles = user_context.get("roles", [])
        self.organization_id = user_context.get("organization_id")
        self.department_id = user_context.get("department_id")
        self.security_level = user_context.get("security_level", SecurityLevel.PUBLIC)

    def setup_rls_policies(self, session: Session, table_name: str) -> None:
        """Setup row-level security policies for PostgreSQL."""
        try:
            # Enable RLS on table
            session.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))

            # Create policies based on user context
            if self.organization_id:
                policy_sql = f"""
                CREATE POLICY user_org_policy ON {table_name}
                FOR ALL TO authenticated
                USING (organization_id = {self.organization_id})
                """
                session.execute(text(policy_sql))

            if self.department_id:
                policy_sql = f"""
                CREATE POLICY user_dept_policy ON {table_name}
                FOR ALL TO authenticated
                USING (department_id = {self.department_id})
                """
                session.execute(text(policy_sql))

            # Admin role policy
            if "admin" in self.roles:
                policy_sql = f"""
                CREATE POLICY admin_policy ON {table_name}
                FOR ALL TO admin
                USING (true)
                """
                session.execute(text(policy_sql))

            session.commit()
            logger.info(f"RLS policies created for table: {table_name}")

        except Exception as e:
            logger.error(f"Failed to create RLS policies for {table_name}: {e}")
            session.rollback()
            raise

    def apply_security_filters(self, query, model_class) -> Any:
        """Apply security filters to query."""
        # Apply organization-based filtering
        if hasattr(model_class, "organization_id") and self.organization_id:
            query = query.filter(model_class.organization_id == self.organization_id)

        # Apply department-based filtering
        if hasattr(model_class, "department_id") and self.department_id:
            query = query.filter(model_class.department_id == self.department_id)

        # Apply role-based filtering
        if "admin" not in self.roles and hasattr(model_class, "created_by"):
            query = query.filter(model_class.created_by == self.user_id)

        # Apply security level filtering
        if hasattr(model_class, "security_level"):
            allowed_levels = self._get_allowed_security_levels()
            query = query.filter(model_class.security_level.in_(allowed_levels))

        return query

    def _get_allowed_security_levels(self) -> List[str]:
        """Get allowed security levels based on user context."""
        if self.security_level == SecurityLevel.RESTRICTED:
            return [SecurityLevel.RESTRICTED.value]
        elif self.security_level == SecurityLevel.CONFIDENTIAL:
            return [SecurityLevel.CONFIDENTIAL.value, SecurityLevel.RESTRICTED.value]
        elif self.security_level == SecurityLevel.INTERNAL:
            return [
                SecurityLevel.INTERNAL.value,
                SecurityLevel.CONFIDENTIAL.value,
                SecurityLevel.RESTRICTED.value,
            ]
        else:  # PUBLIC
            return [
                SecurityLevel.PUBLIC.value,
                SecurityLevel.INTERNAL.value,
                SecurityLevel.CONFIDENTIAL.value,
                SecurityLevel.RESTRICTED.value,
            ]

    def check_access(self, entity, operation: str) -> bool:
        """Check if user has access to entity for operation."""
        # Admin has full access
        if "admin" in self.roles:
            return True

        # Check organization access
        if (
            hasattr(entity, "organization_id")
            and entity.organization_id != self.organization_id
        ):
            return False

        # Check department access
        if (
            hasattr(entity, "department_id")
            and entity.department_id != self.department_id
        ):
            return False

        # Check security level
        if hasattr(entity, "security_level"):
            entity_level = SecurityLevel(entity.security_level)
            if not self._is_level_allowed(entity_level):
                return False

        # Check ownership for sensitive operations
        if operation in ["update", "delete"] and hasattr(entity, "created_by"):
            if entity.created_by != self.user_id and "owner" not in self.roles:
                return False

        return True

    def _is_level_allowed(self, entity_level: SecurityLevel) -> bool:
        """Check if user can access entity with given security level."""
        allowed_levels = self._get_allowed_security_levels()
        return entity_level.value in allowed_levels


class AccessControlManager:
    """Access control manager for database operations."""

    def __init__(self):
        self.rls_instances: Dict[str, RowLevelSecurity] = {}
        self.security_policies: Dict[str, List[Dict[str, Any]]] = {}

    def register_user_context(
        self, session_id: str, user_context: Dict[str, Any]
    ) -> None:
        """Register user context for session."""
        self.rls_instances[session_id] = RowLevelSecurity(user_context)
        logger.debug(f"Registered user context for session: {session_id}")

    def get_rls_for_session(self, session_id: str) -> Optional[RowLevelSecurity]:
        """Get RLS instance for session."""
        return self.rls_instances.get(session_id)

    def setup_security_policies(
        self, table_name: str, policies: List[Dict[str, Any]]
    ) -> None:
        """Setup security policies for table."""
        self.security_policies[table_name] = policies
        logger.info(f"Security policies registered for table: {table_name}")

    def apply_table_security(
        self, session: Session, table_name: str, session_id: str
    ) -> None:
        """Apply security policies to table."""
        rls = self.get_rls_for_session(session_id)
        if rls:
            rls.setup_rls_policies(session, table_name)

    def filter_query_by_security(self, query, model_class, session_id: str) -> Any:
        """Filter query based on security policies."""
        rls = self.get_rls_for_session(session_id)
        if rls:
            return rls.apply_security_filters(query, model_class)
        return query

    def check_entity_access(self, entity, operation: str, session_id: str) -> bool:
        """Check if user has access to entity."""
        rls = self.get_rls_for_session(session_id)
        if rls:
            return rls.check_access(entity, operation)
        return True  # Default to allow if no RLS context


# Global access control manager
access_control_manager = AccessControlManager()
