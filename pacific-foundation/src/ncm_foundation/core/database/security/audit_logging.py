"""
Security audit logging for database operations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from ..models.listeners import audit_context

logger = logging.getLogger(__name__)


class SecurityAuditLogger:
    """Security audit logger for database operations."""

    def __init__(self, audit_table: str = "security_audit_logs"):
        self.audit_table = audit_table
        self._setup_audit_listeners()
        self._audit_entries: List[Dict[str, Any]] = []

    def _setup_audit_listeners(self) -> None:
        """Setup security audit listeners."""

        @event.listens_for(Session, "after_insert")
        def log_insert(mapper, connection, target):
            """Log insert operations."""
            self._log_operation("INSERT", target, connection)

        @event.listens_for(Session, "after_update")
        def log_update(mapper, connection, target):
            """Log update operations."""
            self._log_operation("UPDATE", target, connection)

        @event.listens_for(Session, "after_delete")
        def log_delete(mapper, connection, target):
            """Log delete operations."""
            self._log_operation("DELETE", target, connection)

    def _log_operation(self, operation: str, target: Any, connection) -> None:
        """Log database operation."""
        try:
            audit_data = {
                "operation": operation,
                "table_name": target.__tablename__,
                "record_id": getattr(target, "id", None),
                "timestamp": datetime.utcnow(),
                "user_id": audit_context.get_user(),
                "data": self._serialize_object(target),
                "session_id": getattr(connection, "session_id", None),
                "ip_address": getattr(connection, "ip_address", None),
            }

            # Store in audit table
            self._store_audit_log(audit_data, connection)

            # Store in memory for immediate access
            self._audit_entries.append(audit_data)

            logger.info(
                f"Security audit: {operation} on {target.__tablename__} by {audit_context.get_user()}"
            )

        except Exception as e:
            logger.error(f"Failed to log security audit: {e}")

    def _serialize_object(self, obj: Any) -> Dict[str, Any]:
        """Serialize object for audit logging."""
        try:
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        except Exception as e:
            logger.error(f"Failed to serialize object for audit: {e}")
            return {}

    def _store_audit_log(self, audit_data: Dict[str, Any], connection) -> None:
        """Store audit log in database."""
        try:
            # Create audit table if it doesn't exist
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.audit_table} (
                id SERIAL PRIMARY KEY,
                operation VARCHAR(20) NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                record_id INTEGER,
                timestamp TIMESTAMP NOT NULL,
                user_id VARCHAR(255),
                data JSONB,
                session_id VARCHAR(255),
                ip_address INET
            )
            """
            connection.execute(text(create_table_sql))

            # Insert audit log
            insert_sql = f"""
            INSERT INTO {self.audit_table} 
            (operation, table_name, record_id, timestamp, user_id, data, session_id, ip_address)
            VALUES (:operation, :table_name, :record_id, :timestamp, :user_id, :data, :session_id, :ip_address)
            """

            connection.execute(
                text(insert_sql),
                {
                    "operation": audit_data["operation"],
                    "table_name": audit_data["table_name"],
                    "record_id": audit_data["record_id"],
                    "timestamp": audit_data["timestamp"],
                    "user_id": audit_data["user_id"],
                    "data": json.dumps(audit_data["data"]),
                    "session_id": audit_data["session_id"],
                    "ip_address": audit_data["ip_address"],
                },
            )

        except Exception as e:
            logger.error(f"Failed to store audit log: {e}")

    def get_audit_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit entries."""
        return self._audit_entries[-limit:]

    def clear_audit_entries(self) -> None:
        """Clear in-memory audit entries."""
        self._audit_entries.clear()

    async def query_audit_logs(
        self,
        session,
        table_name: Optional[str] = None,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query audit logs from database."""
        try:
            query = f"SELECT * FROM {self.audit_table} WHERE 1=1"
            params = {}

            if table_name:
                query += " AND table_name = :table_name"
                params["table_name"] = table_name

            if user_id:
                query += " AND user_id = :user_id"
                params["user_id"] = user_id

            if operation:
                query += " AND operation = :operation"
                params["operation"] = operation

            if start_date:
                query += " AND timestamp >= :start_date"
                params["start_date"] = start_date

            if end_date:
                query += " AND timestamp <= :end_date"
                params["end_date"] = end_date

            query += " ORDER BY timestamp DESC LIMIT :limit"
            params["limit"] = limit

            result = await session.execute(text(query), params)
            return [dict(row) for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []

    def generate_security_report(
        self, session, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate security audit report."""
        try:
            # Get operation counts
            operation_counts_sql = f"""
            SELECT operation, COUNT(*) as count
            FROM {self.audit_table}
            WHERE timestamp BETWEEN :start_date AND :end_date
            GROUP BY operation
            ORDER BY count DESC
            """

            result = session.execute(
                text(operation_counts_sql),
                {"start_date": start_date, "end_date": end_date},
            )
            operation_counts = {row.operation: row.count for row in result.fetchall()}

            # Get user activity
            user_activity_sql = f"""
            SELECT user_id, COUNT(*) as count
            FROM {self.audit_table}
            WHERE timestamp BETWEEN :start_date AND :end_date
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
            """

            result = session.execute(
                text(user_activity_sql),
                {"start_date": start_date, "end_date": end_date},
            )
            user_activity = {row.user_id: row.count for row in result.fetchall()}

            # Get table activity
            table_activity_sql = f"""
            SELECT table_name, COUNT(*) as count
            FROM {self.audit_table}
            WHERE timestamp BETWEEN :start_date AND :end_date
            GROUP BY table_name
            ORDER BY count DESC
            LIMIT 10
            """

            result = session.execute(
                text(table_activity_sql),
                {"start_date": start_date, "end_date": end_date},
            )
            table_activity = {row.table_name: row.count for row in result.fetchall()}

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "operation_counts": operation_counts,
                "user_activity": user_activity,
                "table_activity": table_activity,
                "total_operations": sum(operation_counts.values()),
            }

        except Exception as e:
            logger.error(f"Failed to generate security report: {e}")
            return {}


class SecurityEventLogger:
    """Security event logger for suspicious activities."""

    def __init__(self):
        self.suspicious_events: List[Dict[str, Any]] = []

    def log_suspicious_activity(
        self,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log suspicious security activity."""
        event = {
            "event_type": event_type,
            "description": description,
            "user_id": user_id,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow(),
            "additional_data": additional_data or {},
        }

        self.suspicious_events.append(event)
        logger.warning(f"Suspicious activity detected: {event_type} - {description}")

    def get_suspicious_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent suspicious events."""
        return self.suspicious_events[-limit:]

    def clear_suspicious_events(self) -> None:
        """Clear suspicious events."""
        self.suspicious_events.clear()


# Global security audit logger
security_audit_logger = SecurityAuditLogger()
security_event_logger = SecurityEventLogger()
